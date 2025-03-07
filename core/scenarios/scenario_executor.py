import threading, time
from .globals import stop_scenario_execution, check_scenario_status, reset_scenario_status
from .services import load_scenario_from_db, load_action
from .action_executor import execute_action
from channels.layers import get_channel_layer
from .services import replace_placeholders, send_to_websocket
import asyncio
from core.network.traffic_monitor import start_realtime_analysis, stop_realtime_analysis
from core.models import NetworkInfo
from core.context.observable_context import ObservableContext
from core.context.callbacks import ip_blocked_callback

from channels.layers import get_channel_layer



async def execute_scenario(scenario_id, selected_network, group_name):
    """
    Spustí scénář a posílá průběžné zprávy přes WebSocket do skupiny.
    Nyní zpracovává také větvení (branches) podle aktuálního kontextu.
    """
    reset_scenario_status()
    channel_layer = get_channel_layer()

    # Načtení scénáře z DB
    scenario = load_scenario_from_db(scenario_id)
    if not scenario:
        await send_to_websocket(group_name, f"Scénář s ID '{scenario_id}' nebyl nalezen.")
        return

    interface = NetworkInfo.objects(network=selected_network).first().interface

    # Inicializace kontextu
    context = ObservableContext({"selected_network": selected_network})
    network_info = NetworkInfo.objects(network=selected_network).first()
    if network_info:
        context["attacker_ip"] = network_info.ip_address
    else:
        print("IP adresa pro útočníka nebyla nalezena.")
    
    context.register_callback("ip_blocked", lambda key, value: ip_blocked_callback(key, value, group_name, context))

    print(f"Context: {context}")

    # Převod seznamu kroků do slovníku pro snadný přístup podle step_id
    steps = {step["step_id"]: step for step in scenario["steps"]}
    # Předpokládáme, že první krok má nejnižší step_id nebo je explicitně definován jako první
    current_step_id = scenario["steps"][0]["step_id"] if scenario["steps"] else None
    

    try:
        while current_step_id is not None and current_step_id != "end":
            step = steps.get(current_step_id)
            if not step:
                await send_to_websocket(group_name, f"Krok s id '{current_step_id}' nebyl nalezen. Ukončuji scénář.")
                return

            # Odešleme zprávu o spuštění kroku
            description = replace_placeholders(step["description"], context)
            # await send_to_websocket(group_name, f"Provádím krok {step['step_id']}: {description}")
            await send_to_websocket(group_name, f"Provádím krok: {description}")

            # Pokud je definováno pole "conditions" pro tento krok, zkontrolujeme je
            if "conditions" in step and not evaluate_conditions(step["conditions"], context):
                await send_to_websocket(group_name, step.get("failure_message", "Podmínky pro tento krok nejsou splněny. Ukončuji scénář."))
                stop_scenario_execution()
                return

            # Načtení akce pro tento krok
            action = load_action(step["action"])
            if not action:
                await send_to_websocket(group_name, f"Akce '{step['action']}' nebyla nalezena. Ukončuji scénář.")
                return

            # Nahrazení placeholderů v parametrech
            parameters = {key: replace_placeholders(value, context) for key, value in step.get("parameters", {}).items()}

            valid, error_message = validate_required_params(action, parameters)
            if not valid:
                await send_to_websocket(group_name, error_message)
                await send_to_websocket(group_name, f"Scénář ukončen.")
                return

            success, output = await execute_action(action, parameters, context, group_name)
            if not success and not context.get("force_end_current_step"): # Pokud byla akce neúspěšná a nebylo vynuceno ukončení kroku pomocí callbacku
                await send_to_websocket(group_name, step.get("failure_message", "Akce selhala. Ukončuji scénář."))
                await send_to_websocket(group_name, f"Scénář ukončen.")
                return

            # Aktualizace kontextu na základě výsledku akce
            update_context(context, step, output, success)
            # await send_to_websocket(group_name, f"Krok {step['step_id']} byl úspěšně dokončen. {step.get('success_message', '')}")
            await send_to_websocket(group_name, f"Krok byl úspěšně dokončen. {replace_placeholders(step.get('success_message', ''), context)}")

            # Zkusíme spustit monitoring, pokud máme target_ip a sniffer ještě neběží
            if "target_ip" in context and not context.get("realtime_analysis_running"):
                context["realtime_analysis_running"] = True
                await start_realtime_analysis(interface, context["target_ip"], context["attacker_ip"], group_name, context)
                # Můžeš si to uložit i do contextu, ale stačí do lokálních proměnných

            # Zpracování větvení: pokud je definováno pole "branches", vyhodnotíme podmínky
            if "branches" in step:
                branch_taken = False
                for branch in step["branches"]:
                    if evaluate_conditions(branch["condition"], context):
                        current_step_id = branch["next_step"]
                        branch_taken = True

                        # Pokud definované, vypíšeme branch_message
                        if "branch_message" in branch:
                            await send_to_websocket(group_name, replace_placeholders(branch["branch_message"],context))
                        break
                if not branch_taken:
                    # Pokud žádná větev neodpovídá, použijeme standardní next_step
                    current_step_id = step.get("next_step", None)
            else:
                current_step_id = step.get("next_step", None)

            if check_scenario_status():
                await send_to_websocket(group_name, "Scénář byl zastaven uživatelem.")
                return

        await send_to_websocket(group_name, "Scénář byl úspěšně dokončen.")
        
    finally:
        # Až skončí scénář (normálně nebo chybou), vypneme sniffer
        if context.get("realtime_analysis_running"):
            await stop_realtime_analysis()
            context["realtime_analysis_running"] = False
            
def validate_required_params(action, parameters):
    required = action.get("required_parameters", [])
    for param in required:
        if param not in parameters or parameters[param] is None:
            return False, f"Chybí požadovaný parametr: {param} !"
    return True, None
    

def evaluate_conditions(conditions, context):
    """
    Kontroluje, zda jsou splněny všechny podmínky na základě aktuálního kontextu.
    Tento zjednodušený příklad předpokládá, že podmínky jsou slovníkové páry, kde se
    kontroluje, zda hodnota v kontextu odpovídá očekávané hodnotě.
    
    Například:
      {"target_ip": {"$exists": true}}  či {"target_ip": null}
    """
    # Pro tento příklad budeme předpokládat, že podmínky mohou mít speciální operátor "$exists"
    for key, expected in conditions.items():
        actual = context.get(key)
        if isinstance(expected, dict) and "$exists" in expected:
            exists_required = expected["$exists"]
            if exists_required and actual is None:
                return False
            if not exists_required and actual is not None:
                return False
        else:
            if actual != expected:
                return False
    return True



def update_context(context, step, output, success):
    """
    Aktualizuje kontext na základě výsledku akce a definic ve scénáři.
    Pokud je v kroku definováno "context_updates", uloží výstup akce do příslušných klíčů.
    """
    if output is None or output.strip() == "":
        context["previous_step_success"] = False
    else:
        context["previous_step_success"] = success

    if "context_updates" in step and success:
        for key, expression in step["context_updates"].items():
            if expression == "output":
                context[key] = output.strip() if output and output.strip() else None  
            else:
                context[key] = expression
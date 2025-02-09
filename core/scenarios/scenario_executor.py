import threading, time
from .globals import stop_scenario_execution, check_scenario_status, reset_scenario_status
from .services import load_scenario_from_db, load_action
from .action_executor import execute_action
from channels.layers import get_channel_layer
from .services import replace_placeholders, send_to_websocket
import asyncio

from channels.layers import get_channel_layer

async def execute_scenario(scenario_id, selected_network, group_name):
    """
    Spustí scénář a posílá průběžné zprávy přes WebSocket do skupiny.
    """
    reset_scenario_status()
    channel_layer = get_channel_layer()

    # Načtěte scénář z databáze
    scenario = load_scenario_from_db(scenario_id)
    if not scenario:
        await send_to_websocket(group_name, f"Scénář s ID '{scenario_id}' nebyl nalezen.")
        return

    context = {"selected_network": selected_network}
    
    for step in scenario["steps"]:
        print(f"Executing step {step['step_id']}")
        if check_scenario_status():
            await send_to_websocket(group_name, "Scénář byl zastaven uživatelem.")
            return
        # Popis aktuálního kroku
        description = replace_placeholders(step["description"], context)
        
        await send_to_websocket(group_name, f"Provádím krok {step['step_id']}: {description}")

        # Načtení akce pro tento krok
        action = load_action(step["action"])
        if not action:
            await send_to_websocket(group_name, f"Akce '{step['action']}' nebyla nalezena v databázi. Ukončuji scénář.")
            return

        # Zkontrolujeme, zda jsou splněny podmínky pro tento krok
        if "conditions" in step and not evaluate_conditions(step["conditions"], context):
            await send_to_websocket(group_name, step.get("failure_message", "Podmínky pro tento krok nejsou splněny. Ukončuji scénář."))
            stop_scenario_execution()
            return

        # Zpracování akce
           # Nahrazení placeholderů v parametrech akce
        parameters = {key: replace_placeholders(value, context) for key, value in step["parameters"].items()}
        success, output = await execute_action(action, parameters, context, group_name)

        if not success:
            await send_to_websocket(group_name, step.get("failure_message", "Akce selhala. Ukončuji scénář."))
            return

        # Aktualizace kontextu
        #context.update(step.get("context_updates", {}))
        update_context(context, step, output, success)
        
        await send_to_websocket(group_name, f"Krok {step['step_id']} byl úspěšně dokončen.")

    await send_to_websocket(group_name, "Scénář byl úspěšně dokončen.")
    
def evaluate_conditions(conditions, context):
    """
    Kontroluje, zda jsou splněny všechny podmínky na základě aktuálního kontextu.
    """
    print(f"Kontroluji podmínky: {conditions}")
    for key, expected_value in conditions.items():
        actual_value = context.get(key)

        # Pokud podmínka odkazuje na hodnotu v kontextu (např. {{target_ip}})
        if isinstance(expected_value, str) and expected_value.startswith("{{") and expected_value.endswith("}}"):
            required_key = expected_value.strip("{{}}")
            actual_required_value = context.get(required_key)

            # Zkontrolujeme, zda je klíč přítomen a není None
            if actual_required_value is None:
                print(f"Podmínka pro '{key}' není splněna: očekávaný klíč '{required_key}' chybí nebo je prázdný v kontextu.")
                stop_scenario_execution()
                return False
        elif actual_value is None:
            print(f"Podmínka pro '{key}' není splněna: hodnota je None.")
            stop_scenario_execution()
            return False
        elif actual_value != expected_value:
            print(f"Podmínka pro '{key}' není splněna: {actual_value} != {expected_value}.")
            stop_scenario_execution()
            return False

    # Pokud jsou všechny podmínky splněny
    print("Všechny podmínky jsou splněny.")
    return True

def update_context(context, step, output, success):
    """
    Aktualizuje kontext na základě výsledku akce a definic ve scénáři.
    """
    if output is None or output.strip() == "":
        context["previous_step_success"] = False
    else:
        context["previous_step_success"] = success

    
    # Pokud existují nějaké specifické aktualizace v `context_updates`
    if "context_updates" in step and success:
        for key, expression in step["context_updates"].items():
            if expression == "output":
                # Uložíme výstup akce do kontextu
                context[key] = output.strip() if output and output.strip() else None  
            else:
                # Uložíme jinou hodnotu definovanou ve scénáři
                context[key] = expression
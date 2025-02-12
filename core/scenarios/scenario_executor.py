import threading, time
from .globals import stop_scenario_execution, check_scenario_status, reset_scenario_status
from .services import load_scenario_from_db, load_action
from .action_executor import execute_action
from channels.layers import get_channel_layer
from .services import replace_placeholders, send_to_websocket
import asyncio

from channels.layers import get_channel_layer

# async def execute_scenario(scenario_id, selected_network, group_name):
#     """
#     Spustí scénář a posílá průběžné zprávy přes WebSocket do skupiny.
#     """
#     reset_scenario_status()
#     channel_layer = get_channel_layer()

#     # Načtěte scénář z databáze
#     scenario = load_scenario_from_db(scenario_id)
#     if not scenario:
#         await send_to_websocket(group_name, f"Scénář s ID '{scenario_id}' nebyl nalezen.")
#         return

#     context = {"selected_network": selected_network}
    
#     for step in scenario["steps"]:
#         print(f"Executing step {step['step_id']}")
#         if check_scenario_status():
#             await send_to_websocket(group_name, "Scénář byl zastaven uživatelem.")
#             return
#         # Popis aktuálního kroku
#         description = replace_placeholders(step["description"], context)
        
#         await send_to_websocket(group_name, f"Provádím krok {step['step_id']}: {description}")

#         # Načtení akce pro tento krok
#         action = load_action(step["action"])
#         if not action:
#             await send_to_websocket(group_name, f"Akce '{step['action']}' nebyla nalezena v databázi. Ukončuji scénář.")
#             return

#         # Zkontrolujeme, zda jsou splněny podmínky pro tento krok
#         if "conditions" in step and not evaluate_conditions(step["conditions"], context):
#             await send_to_websocket(group_name, step.get("failure_message", "Podmínky pro tento krok nejsou splněny. Ukončuji scénář."))
#             stop_scenario_execution()
#             return

#         # Zpracování akce
#            # Nahrazení placeholderů v parametrech akce
#         parameters = {key: replace_placeholders(value, context) for key, value in step["parameters"].items()}
#         success, output = await execute_action(action, parameters, context, group_name)

#         if not success:
#             await send_to_websocket(group_name, step.get("failure_message", "Akce selhala. Ukončuji scénář."))
#             return

#         # Aktualizace kontextu
#         #context.update(step.get("context_updates", {}))
#         update_context(context, step, output, success)
        
#         await send_to_websocket(group_name, f"Krok {step['step_id']} byl úspěšně dokončen.")

#     await send_to_websocket(group_name, "Scénář byl úspěšně dokončen.")

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

    # Inicializace kontextu
    context = {"selected_network": selected_network}

    # Převod seznamu kroků do slovníku pro snadný přístup podle step_id
    steps = {step["step_id"]: step for step in scenario["steps"]}
    # Předpokládáme, že první krok má nejnižší step_id nebo je explicitně definován jako první
    current_step_id = scenario["steps"][0]["step_id"] if scenario["steps"] else None

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
        if not success:
            await send_to_websocket(group_name, step.get("failure_message", "Akce selhala. Ukončuji scénář."))
            await send_to_websocket(group_name, f"Scénář ukončen.")
            return

        # Aktualizace kontextu na základě výsledku akce
        update_context(context, step, output, success)
        # await send_to_websocket(group_name, f"Krok {step['step_id']} byl úspěšně dokončen. {step.get('success_message', '')}")
        await send_to_websocket(group_name, f"Krok byl úspěšně dokončen. {replace_placeholders(step.get('success_message', ''), context)}")

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


def validate_required_params(action, parameters):
    required = action.get("required_parameters", [])
    for param in required:
        if param not in parameters or parameters[param] is None:
            return False, f"Chybí požadovaný parametr: {param} !"
    return True, None
    
# def evaluate_conditions(conditions, context):
#     """
#     Kontroluje, zda jsou splněny všechny podmínky na základě aktuálního kontextu.
#     """
#     print(f"Kontroluji podmínky: {conditions}")
#     for key, expected_value in conditions.items():
#         actual_value = context.get(key)

#         # Pokud podmínka odkazuje na hodnotu v kontextu (např. {{target_ip}})
#         if isinstance(expected_value, str) and expected_value.startswith("{{") and expected_value.endswith("}}"):
#             required_key = expected_value.strip("{{}}")
#             actual_required_value = context.get(required_key)

#             # Zkontrolujeme, zda je klíč přítomen a není None
#             if actual_required_value is None:
#                 print(f"Podmínka pro '{key}' není splněna: očekávaný klíč '{required_key}' chybí nebo je prázdný v kontextu.")
#                 stop_scenario_execution()
#                 return False
#         elif actual_value is None:
#             print(f"Podmínka pro '{key}' není splněna: hodnota je None.")
#             stop_scenario_execution()
#             return False
#         elif actual_value != expected_value:
#             print(f"Podmínka pro '{key}' není splněna: {actual_value} != {expected_value}.")
#             stop_scenario_execution()
#             return False

#     # Pokud jsou všechny podmínky splněny
#     print("Všechny podmínky jsou splněny.")
#     return True

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


# def update_context(context, step, output, success):
#     """
#     Aktualizuje kontext na základě výsledku akce a definic ve scénáři.
#     """
#     if output is None or output.strip() == "":
#         context["previous_step_success"] = False
#     else:
#         context["previous_step_success"] = success

    
#     # Pokud existují nějaké specifické aktualizace v `context_updates`
#     if "context_updates" in step and success:
#         for key, expression in step["context_updates"].items():
#             if expression == "output":
#                 # Uložíme výstup akce do kontextu
#                 context[key] = output.strip() if output and output.strip() else None  
#             else:
#                 # Uložíme jinou hodnotu definovanou ve scénáři
#                 context[key] = expression


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
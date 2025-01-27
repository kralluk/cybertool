import threading, time
from .globals import stop_scenario_execution, check_scenario_status, reset_scenario_status
from .services import load_scenario_from_db, load_action
from .action_executor import execute_action
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .services import replace_placeholders

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
        await channel_layer.group_send(
            group_name,
            {"type": "send_message", "message": f"Scénář s ID '{scenario_id}' nebyl nalezen."}
        )
        return

    context = {"selected_network": selected_network}

    for step in scenario["steps"]:
        if check_scenario_status():
            await channel_layer.group_send(
                group_name,
                {"type": "send_message", "message": "Scénář byl zastaven uživatelem."}
            )
            break

        # Popis aktuálního kroku
        description = replace_placeholders(step["description"], context)
        await channel_layer.group_send(
            group_name,
            {"type": "send_message", "message": f"Provádím krok {step['step_id']}: {description}"}
        )

        # Načtení akce pro tento krok
        action = load_action(step["action"])
        if not action:
            await channel_layer.group_send(
                group_name,
                {"type": "send_message", "message": f"Akce '{step['action']}' nebyla nalezena v databázi. Ukončuji scénář."}
            )
            break

        # Zkontrolujeme, zda jsou splněny podmínky pro tento krok
        if "conditions" in step and not evaluate_conditions(step["conditions"], context):
            await channel_layer.group_send(
                group_name,
                {"type": "send_message", "message": step.get("failure_message", "Podmínky pro tento krok nejsou splněny. Ukončuji scénář.")}
            )
            break

        # Zpracování akce
           # Nahrazení placeholderů v parametrech akce
        parameters = {key: replace_placeholders(value, context) for key, value in step["parameters"].items()}
        success, output = execute_action(action, parameters, context)

        if not success:
            await channel_layer.group_send(
                group_name,
                {"type": "send_message", "message": step.get("failure_message", "Akce selhala. Ukončuji scénář.")}
            )
            break

        # Aktualizace kontextu
        context.update(step.get("context_updates", {}))

        await channel_layer.group_send(
            group_name,
            {"type": "send_message", "message": step.get("success_message", "Krok byl úspěšný.")}
        )

    await channel_layer.group_send(
        group_name,
        {"type": "send_message", "message": "Scénář byl úspěšně dokončen."}
    )
def evaluate_conditions(conditions, context):
    """
    Kontroluje, zda jsou splněny všechny podmínky na základě aktuálního kontextu.
    """
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


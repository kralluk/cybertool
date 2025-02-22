from core.scenarios.services import send_to_websocket
from core.scenarios.globals import stop_scenario_execution

async def ip_blocked_callback(key, value, group_name, context):
    if key == "ip_blocked" and value is True:
        await send_to_websocket(group_name, f"IP adresa {context['attacker_ip']} byla zablokována.")
        stop_scenario_execution()


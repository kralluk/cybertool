from core.scenarios.services import send_to_websocket
from core.scenarios.globals import stop_attack_processes

# async def ip_blocked_callback(key, value, group_name, context):
#     if key == "ip_blocked" and value is True:
#         await send_to_websocket(group_name, f"IP adresa {context['attacker_ip']} byla zablokována.")
#         stop_scenario_execution()

async def ip_blocked_callback(key, value, group_name, context):
    """
    Callback, který se spustí při změně hodnoty 'ip_blocked'.
    Odešle zprávu, zastaví běžící útokové procesy a nastaví flag pro okamžité vyhodnocení větví.
    """
    if key == "ip_blocked" and value is True:
        await send_to_websocket(group_name, "Detekována pravděpodobná blokace cílové IP. Přerušuji aktuální krok.")
        
        # Ukončíme útokové procesy pomocí nové funkce
        stop_attack_processes()
        
        # Nastavíme flag, který způsobí, že aktuální krok se ukončí a scénář přejde na vyhodnocení branchí
        context["force_end_current_step"] = True

from core.scenarios.services import send_to_websocket
from core.scenarios.globals import stop_attack_processes

async def ip_blocked_callback(key, value, group_name, context):
    """
    Callback, který se spustí při změně hodnoty 'ip_blocked'.
    Odešle zprávu, zastaví běžící útokové procesy a nastaví flag pro okamžité vyhodnocení větví.
    """
    if key == "ip_blocked" and value is True:
        await send_to_websocket(group_name, "Detekována pravděpodobná blokace cílové IP. Přerušuji aktuální krok.")
        
        stop_attack_processes()
        
        # Nastavíme flag, který způsobí, že aktuální krok se ukončí a scénář přejde na vyhodnocení branchí
        context["force_end_current_step"] = True

async def msf_session_closed_callback(key, value, group_name, context):
    if key == "msf_session_closed" and value is True and not context.get("msf_session_closed_reported", False):
        await send_to_websocket(group_name, "Detekována pravděpodobné ukončení Metasploit session ze strany oběti.")
        stop_attack_processes(include_metasploit=True, context=context)
        context["force_end_current_step"] = True
        context["msf_session_closed_reported"] = True
        print(f"[msf_session_closed_callback] Detekováno uzavření session: {context['msf_session_closed_reported']}")



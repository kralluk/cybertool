import asyncio, re
from core.scenarios.services import send_to_websocket

# Registr pro Python akce
PYTHON_ACTION_REGISTRY = {}

def register_python_action(name):
    """
    Dekorátor pro registraci Python akcí.
    Použij ho, když definuješ novou akci, aby se automaticky přidala do registru.
    """
    def decorator(func):
        PYTHON_ACTION_REGISTRY[name] = func
        return func
    return decorator

async def execute_python_action(action, parameters, context, group_name):
    """
    Spustí Python funkci definovanou v akci typu 'python'.
    Očekává se, že v konfiguraci akce bude uveden klíč 'python_function',
    který obsahuje název funkce registrované v PYTHON_ACTION_REGISTRY.
    
    Funkce se volá s předanými parametry a aktuálním kontextem.
    """
    python_function_name = action.get("python_function")
    if not python_function_name:
        await send_to_websocket(group_name, "Chybí specifikace python_function v akci.")
        return False, "Missing python_function specification."

    func = PYTHON_ACTION_REGISTRY.get(python_function_name)
    if not func:
        await send_to_websocket(group_name, f"Python funkce '{python_function_name}' nebyla nalezena.")
        return False, f"Python function '{python_function_name}' not found."

    try:
        # Podpora asynchroních i synchroních funkcí
        if asyncio.iscoroutinefunction(func):
            result = await func(parameters, context)
        else:
            result = func(parameters, context)
            
        await send_to_websocket(group_name, f"Výstup python funkce: {result}")
        return True, result
    except Exception as e:
        await send_to_websocket(group_name, f"Chyba při spuštění python funkce '{python_function_name}': {str(e)}")
        return False, str(e)
    

@register_python_action("parse_nmap_ping_output")
def parse_nmap_ping_output(parameters, context):
    """
    Přečte surový výstup nmapu (ping scan) z kontextu
    a vyparsuje řádky typu 'Nmap scan report for 192.168.50.10'.
    Výsledné IP uloží do context["host_list"] (mezerou oddělené).

    Parametry (parameters):
      - output_key: (volitelný) klíč v kontextu, kde je uložen surový výstup. Default: 'ping_scan_output'.

    Návratová hodnota:
      - Seznam nalezených IP adres (např. ["192.168.50.10", "192.168.50.12"]).
    """
    # 1) Zjistíme, kde je uložen surový výstup v kontextu
    output_key = parameters.get("output_key", "ping_scan_output")
    raw_output = context.get(output_key, "")
    if not raw_output:
        return "Nebyl nalezen žádný surový výstup nmapu v kontextu."

    # 2) Parsování řádků
    found_ips = []
    for line in raw_output.splitlines():
        line = line.strip()
        # Hledáme řádky typu "Nmap scan report for 192.168.50.10"
        m = re.match(r"Nmap scan report for (\S+)", line)
        if m:
            ip_addr = m.group(1)
            found_ips.append(ip_addr)

    # 3) Uložíme do kontextu např. jako "host_list"
    #    Můžeš si vybrat formát – buď list, nebo mezerou oddělený řetězec
    context["host_list"] = " ".join(found_ips)

    # 4) Vrátíme seznam IP
    return found_ips
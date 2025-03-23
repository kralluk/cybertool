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
    Pokud vrátí obyčejnou hodnotu (např. řetězec/list/int), 
    bereme to jako (True, ta_hodnota).
    Pokud vrátí dvojici (bool, cokoliv), bereme bool jako success, cokoliv jako output.
    """
    python_function_name = action.get("python_function")
    if not python_function_name:
        await send_to_websocket(group_name, "Chybí specifikace 'python_function' v akci.")
        return False, "Missing python_function specification."

    func = PYTHON_ACTION_REGISTRY.get(python_function_name)
    if not func:
        msg = f"Python funkce '{python_function_name}' nebyla nalezena."
        await send_to_websocket(group_name, msg)
        return False, msg

    try:
        # Rozlišíme, zda funkce je async nebo sync
        if asyncio.iscoroutinefunction(func):
            result = await func(parameters, context)
        else:
            result = func(parameters, context)
        
        # Teď zjistíme, zda result je tuple (bool, cokoliv)
        if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], bool):
            success, output = result
        else:
            # Bereme to jako (True, result)
            success, output = True, result
        
        await send_to_websocket(group_name, f"Výstup: {output}")
        return success, output

    except Exception as e:
        err_msg = f"Chyba při spuštění python funkce '{python_function_name}': {str(e)}"
        await send_to_websocket(group_name, err_msg)
        return False, err_msg

@register_python_action("parse_nmap_output_for_IPs")
def parse_nmap_output_for_IPs(parameters, context):
    """
    Přečte surový výstup nmapu (ping scan) z kontextu
    a vyparsuje řádky typu 'Nmap scan report for 192.168.50.10'.
    Výsledné IP uloží do context["host_list"] jako mezerou oddělený řetězec.

    Parametry (parameters):
      - output_key: (volitelný) klíč v kontextu, kde je uložen surový výstup. 
        Default: 'ping_scan_output'.

    Návratová hodnota:
      - Řetězec všech nalezených IP adres, oddělených mezerou.
    """
    import re

    output_key = parameters.get("nmap_output", "output") # vystup z nmapu, v připadě že není definován, hledá se "output"
    raw_output = context.get(output_key, "")
    if not raw_output:
        return "Nebyl nalezen žádný surový výstup nmapu v kontextu."

    found_ips = []
    for line in raw_output.splitlines():
        line = line.strip()
        # Hledáme řádky typu "Nmap scan report for 192.168.50.10"
        m = re.match(r"Nmap scan report for (\S+)", line)
        if m:
            ip_addr = m.group(1)
            found_ips.append(ip_addr)

    # Převést seznam IP na jediný řetězec oddělený mezerou
    ip_string = " ".join(found_ips)

    # Uložíme do contextu
    # context["host_list"] = ip_string

    # print(f"context = {context}")

    # Vrátíme stejný řetězec
    return ip_string


@register_python_action("parse_nmap_services_for_vulns")
def parse_nmap_services_for_vulns(parameters, context):
    """
    Projde nmap service scan (uložený v context[scan_output_key]) a hledá definované 
    signatury, např. "UnrealIRCd" na portu 6667. Pokud najde, uloží do context["target_ip"] 
    IP té služby, a vrátí "192.168.50.8" (příklad).
    
    Parametry:
      - scan_output_key (str) = klíč, kde je uložen syrový text z nmap -sV
      - patterns (dict) = slovník { "unreal_ircd": "UnrealIRCd", "vsftpd": "vsftpd 2.3.4", ... }
         Můžeš definovat víc signatur, podle kterých hledáš potenciální cíl.

    Příklad usage:
      parameters = {
        "scan_output_key": "service_scan_output",
        "patterns": {
          "unreal_ircd": "UnrealIRCd",
          "vsftpd": "vsftpd 2.3.4"
        }
      }
    Návrat: IP adresa (string) nebo None/prazdny text, 
            plus uloží do context["target_ip"].
    """
    scan_key = parameters.get("scan_output_key", "service_scan_output")
    raw_output = context.get(scan_key, "")
    if not raw_output:
        return "Chybí nmap service scan output"

    # Předpokládaná struktura 'patterns' je dict 
    # (např. { "unreal_ircd": "UnrealIRCd", "vsftpd": "vsftpd 2.3.4" })
    patterns = parameters.get("patterns", {})

    # Regulárně procházíme řádky typu:
    # "Nmap scan report for 192.168.50.8
    # 6667/tcp open  irc     UnrealIRCd 3.2.8.1"
    # Typicky to vypadá: "PORT   STATE SERVICE VERSION"

    # Budeme si pamatovat ip => text o službách
    ip_services = {}
    current_ip = None

    for line in raw_output.splitlines():
        line = line.strip()
        # Hledáme řádek "Nmap scan report for <IP>"
        m = re.match(r"Nmap scan report for (\S+)", line)
        if m:
            current_ip = m.group(1)
            ip_services[current_ip] = []
        else:
            # Pokud je to řádek s portem / službou, přidáme do ip_services[current_ip]
            if current_ip:
                ip_services[current_ip].append(line)

    # Nyní máme ip_services = { "192.168.50.8": ["21/tcp open ftp vsftpd 2.3.4", "6667/tcp open irc UnrealIRCd 3.2.8.1", ...], ... }

    # Budeme hledat, jestli některý z definovaných 'patterns' se vyskytuje v textu
    # a pokud ano, vybereme tu IP jako target
    found_ip = None
    for ip, lines in ip_services.items():
        joined = " ".join(lines)  # seřadíme řádky dohromady
        for label, pattern in patterns.items():
            if pattern.lower() in joined.lower():
                # Našli jsme hledaný string => považujeme to za zranitelné
                found_ip = ip
                break
        if found_ip:    
            break

    if found_ip:
        return found_ip
    else:
         return (False, "Nebyly nalezeny definované signatury z patterns")
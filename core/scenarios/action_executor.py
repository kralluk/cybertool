import asyncio
import subprocess, paramiko
import os
import signal
import json
import time
from .globals import check_scenario_status, running_processes, ssh_manager
from .services import replace_placeholders, send_to_websocket
from .ssh_manager import SSHManager
from pymetasploit3.msfrpc import MsfRpcClient
import traceback
from core.scenarios.globals import set_msf_session



async def execute_action(action, parameters, context, group_name):
    """
    Spustí akci a zavolá správného handlera podle typu akce.
    """

    action_type = action.get("type", "local")  # Defaultně předpokládáme `local`
    command = action.get("command", None)
    if command:
        command = replace_placeholders(command, parameters)

    if action_type == "local" and parameters.get("run_in_msf_session", False):
        # Pokud je akce typu "local" a má být spuštěna v  metasploit session, zavoláme funkci pro Metasploit session
        return await execute_metasploit_session_command(command, context, group_name)
    elif action_type == "local":
        return await execute_local_command(command, group_name)
    elif action_type == "ssh":
        return await execute_ssh_command(action, parameters, group_name)
    elif action_type == "python":
        from core.scenarios.python_actions import execute_python_action
        return await execute_python_action(action, parameters, context, group_name)
    elif action_type == "metasploit":
        return await execute_metasploit_action(action, parameters, context, group_name)
    else:
        await send_to_websocket(group_name, f"Neznámý typ akce: {action_type}")
        return False, f"Neznámý typ akce: {action_type}"



async def execute_local_command(command, group_name):
    """
    Spustí lokální příkaz asynchronně a posílá průběžné zprávy přes WebSocket.
    """
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setsid
        )

        # Přidání procesu do seznamu běžících procesů
        running_processes.append(process)

        while process.returncode is None:  # Pokud stále běží
            if check_scenario_status():  # Pokud byl scénář zastaven
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
               # await send_to_websocket(group_name, "Akce byla zastavena uživatelem.")
                return False #, "Akce byla zastavena uživatelem."

            await asyncio.sleep(0.5)

        stdout, stderr = await process.communicate()
        output = stdout.decode().strip() + "\n" + stderr.decode().strip()
        output = output.strip()  # odstraní prázdné řádky na začátku a konci

        # if not output and not check_scenario_status():
        #     await send_to_websocket(group_name, "Výstup je prázdný – akce selhala.")
        #     return False, "Výstup příkazu byl prázdný."
    
        

        if process.returncode != 0 and not check_scenario_status():
            await send_to_websocket(group_name, f"Chyba při lokálním příkazu: {output}")
            return False, output
        
        await send_to_websocket(group_name, f"Výstup spuštěného příkazu: {output}")

        # if not check_scenario_status():
        #     await send_to_websocket(group_name, f"Výstup lokálního příkazu: {output}")
        return True, output

    finally:
        if process in running_processes:
            running_processes.remove(process)



async def execute_ssh_command(action, parameters, group_name):
    """
    Spustí příkaz přes SSH a případně nahraje a spustí .py skript, pokud jde o akci ssh_run_python_script.
    Posílá průběžné zprávy přes WebSocket.
    """
    global ssh_manager
    try:
        ssh_user = parameters.get("ssh_user")
        ssh_password = parameters.get("ssh_password")
        target_ip = parameters.get("target_ip")

        if not ssh_user or not ssh_password or not target_ip:
            await send_to_websocket(group_name, "Chybí potřebné SSH parametry (ssh_user, ssh_password, target_ip).")
            return False, "Chybí SSH parametry."

        ssh_manager = SSHManager(target_ip, ssh_user, ssh_password, group_name)

        # Připojení k SSH
        if not await ssh_manager.connect():
            await send_to_websocket(group_name, "Nepodařilo se připojit k SSH. Ukončuji krok jako neúspěšný.")
            return False, "Nepodařilo se připojit k SSH."

        use_sudo = True  # výchozí hodnota

        # Pokud se jedná o spuštění Python skriptu
        if action["_id"] == "ssh_run_python_script":
            script_name = parameters.get("script_name")

            if not script_name:
                await send_to_websocket(group_name, "Chybí parametr 'script_name'.")
                return False, "Chybí parametr 'script_name'."

            if ".." in script_name or "/" in script_name:
                return False, "Neplatný název skriptu."

            local_path = os.path.join("scripts", script_name)
            remote_path = f"/tmp/{script_name}"

            if not os.path.isfile(local_path):
                await send_to_websocket(group_name, f"Skript '{script_name}' neexistuje.")
                return False, f"Skript '{script_name}' neexistuje."

            loop = asyncio.get_event_loop()
            success, msg = await loop.run_in_executor(None, lambda: ssh_manager.upload_file(local_path, remote_path))

            if not success:
                await send_to_websocket(group_name, f"Nahrávání skriptu selhalo: {msg}")
                return False, msg

            await send_to_websocket(group_name, f"Skript '{script_name}' byl úspěšně nahrán.")
            command = f"python3 {remote_path}"
            use_sudo = False  # ⬅️ NEpoužívat sudo pro spouštění Python skriptu
        
        elif action["_id"] == "ssh_upload_file":
            file_name = parameters.get("file_name")

            if not file_name:
                await send_to_websocket(group_name, "Chybí parametr 'file_name'.")
                return False, "Chybí parametr 'file_name'."

            if ".." in file_name or "/" in file_name:
                return False, "Neplatný název souboru."

            local_path = os.path.join("files", file_name)  
            remote_path = f"{file_name}"
            

            if not os.path.isfile(local_path):
                await send_to_websocket(group_name, f"Soubor '{file_name}' neexistuje.")
                return False, f"Soubor '{file_name}' neexistuje."

            loop = asyncio.get_event_loop()
            success, msg = await loop.run_in_executor(None, lambda: ssh_manager.upload_file(local_path, remote_path))

            if not success:
                await send_to_websocket(group_name, f"Nahrávání souboru selhalo: {msg}")
                return False, msg

            await send_to_websocket(group_name, f"Soubor '{file_name}' byl úspěšně nahrán.")
            await ssh_manager.close()
            return True, f"Soubor '{file_name}' úspěšně nahrán na cílové zařízení."

        else:
            command = replace_placeholders(action["command"], parameters)

        # Spuštění příkazu
        success, output = await ssh_manager.execute_command(command, use_sudo=use_sudo)

        # Odpojení
        await ssh_manager.close()

        return success, output

    except Exception as e:
        await send_to_websocket(group_name, f"Chyba při SSH příkazu: {str(e)}")
        return False, str(e)

async def execute_metasploit_action(action, parameters, context, group_name):
    await send_to_websocket(group_name, f"Spouštím exploit {action['_id']}...")
    # Nahrazení placeholderů dle contextu
    options = replace_placeholders(action.get("options", {}), context)
    await send_to_websocket(group_name, f"Nastavení pro exploit: {options}")
    loop = asyncio.get_event_loop()

    def run_exploit_with_console():
        try:
            # Připojení k Metasploit serveru
            client = MsfRpcClient("mysecret", server="127.0.0.1", port=55553)
            # Uložíme si seznam session před spuštěním exploitu
            old_sessions = client.sessions.list.copy()

            # Vytvoříme novou konzoli
            console = client.consoles.console()
            
            # Použijeme modul specifikovaný v options (např. "exploit/unix/irc/unreal_ircd_3281_backdoor")
            module_str = options.get("module")
            if not module_str:
                return {"error": "Chybí nastavený modul"}
            console.write(f"use {module_str}")
            
            # Nastavení dalších voleb kromě modulu a payloadu
            for key, value in options.items():
                if key in ("module", "PAYLOAD"):
                    continue
                # Příkaz typu "set <key> <value>"
                console.write(f"set {key} {value}")
            
            # Nastavení payloadu
            chosen_payload = options.get("PAYLOAD")
            if chosen_payload:
                console.write(f"set PAYLOAD {chosen_payload}")
            # else:
            #     return {"error": "Chybí nastavený payload"}
            
            # Spuštění exploitu
            console.write("run")
            
            # Polling – čekáme na výstup konzole až do timeoutu (60 sekund)
            output = ""
            session_opened = False
            start = time.time()
            while time.time() - start < 60:
                out = console.read()
                if out:
                    # Pokud je výstup dict, převedeme ho na řetězec
                    if isinstance(out, dict):
                        out_str = json.dumps(out, ensure_ascii=False)
                    else:
                        out_str = out
                    output += out_str
                    if "Command shell session" in out_str:
                        session_opened = True
                        break
                time.sleep(2)
            
            # Pokud se session otevřela, načteme aktuální session a získáme ID nové session
            session_id = None
            if session_opened:
                new_sessions = client.sessions.list
                created_sessions = set(new_sessions.keys()) - set(old_sessions.keys())
                if created_sessions:
                    session_id = list(created_sessions)[0]
            
            # (Volitelně) Můžeš odstranit část, která testuje příkaz whoami
            whoami_output = ""
            if session_opened:
                console.write("whoami")
                start2 = time.time()
                while time.time() - start2 < 30:
                    out = console.read()
                    if out:
                        if isinstance(out, dict):
                            data = out.get("data", "")
                            whoami_output += data
                        else:
                            whoami_output += out
                        if whoami_output.strip():
                            break
                    time.sleep(2)
            
            return {
                "console_output": output,
                "session_opened": session_opened,
                "whoami": whoami_output,
                "session_id": session_id
            }
        except Exception as ex:
            return {"error": str(ex)}
    
    await send_to_websocket(group_name, "Připojuji se k Metasploit serveru pomocí konzole a spouštím exploit...")
    result = await loop.run_in_executor(None, run_exploit_with_console)
    
    if "error" in result:
        error_message = f"Chyba při spuštění exploitu: {result['error']}"
        await send_to_websocket(group_name, error_message)
        return (False, error_message)
    
    if not result.get("session_opened"):
        msg = "Exploit byl zadán, ale nebyla otevřena žádná interaktivní session."
        await send_to_websocket(group_name, msg)
        return (False, json.dumps({"exploit": result}, ensure_ascii=False))
    
    # Uložíme session_id do contextu, aby další kroky mohly s ní pracovat
    context["session_id"] = result.get("session_id")
    msf_client = MsfRpcClient("mysecret", server="127.0.0.1", port=55553)
    set_msf_session(msf_client, result["session_id"])



    # Spuštíme detektor pro sledování stavu session
    from core.network.detectors import MetasploitSessionDetector
    asyncio.create_task(
        MetasploitSessionDetector(
            session_id=result.get("session_id"),
            group_name=group_name,
            context=context,
            poll_interval=5.0
        ).start()
    )
    
    await send_to_websocket(group_name, "Exploit dokončen.")
    await send_to_websocket(group_name, f"Active session otevřena, session_id: {result.get('session_id')}, uložena do kontextu a whoami výstup: {result['whoami']}")
    
    combined_result = {"exploit": result}
    return (True, json.dumps(combined_result, ensure_ascii=False))

async def execute_metasploit_session_command(command, context, group_name=None):
    """
    Spustí cmd ve stávající Metasploit session a průběžně čte výstup,
    dokud uživatel nestiskne stop, nebo nenastane force_end_current_step,
    nebo msf_session_closed.
    """
    from pymetasploit3.msfrpc import MsfRpcClient

    session_id = context.get("session_id")
    if not session_id:
        return False, "Session ID není dostupné."

    client = MsfRpcClient("mysecret", server="127.0.0.1", port=55553)
    session = client.sessions.session(session_id)
    session.write(command)

    loop = asyncio.get_event_loop()
    while True:
        # 1) Priorita: ukončení scénáře
        if check_scenario_status():
            return True, "Zastaveno uživatelem."

        # 2) Callbacky pro force_end_current_step nebo msf_session_closed
        if context.get("force_end_current_step") or context.get("msf_session_closed"):
            return True, "Ukončeno callbackem."

        # 3) Pokusíme se přečíst výstup; pokud chybí pole 'data', považujeme session za uzavřenou
        try:
            out = await loop.run_in_executor(None, session.read)
        except KeyError:
            # označíme v contextu, že session zmizela
            context["msf_session_closed"] = True
            # await send_to_websocket(group_name, f"[msf:{session_id}] Session byla uzavřena obětí.")
            return True, "Session ukončena obětí."
        except Exception as e:
            # jiné chyby jen zalogujeme a ukončíme
            await send_to_websocket(group_name, f"[msf:{session_id}] Chyba čtení session: {e}")
            return False, str(e)

        # 4) Když máme nějaký výstup, pošleme ho na frontend
        if out:
            await send_to_websocket(group_name, f"[msf:{session_id}] {out}")

        # 5) Krátká pauza před dalším čtením
        await asyncio.sleep(0.2)
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
    Spustí příkaz přes SSH a posílá průběžné zprávy přes WebSocket.
    """
    global ssh_manager
    try:
        # Načtení parametrů
        ssh_user = parameters.get("ssh_user")
        ssh_password = parameters.get("ssh_password")
        target_ip = parameters.get("target_ip")
        command = replace_placeholders(action["command"], parameters)

        if not ssh_user or not ssh_password or not target_ip:
            await send_to_websocket(group_name, "Chybí potřebné SSH parametry (ssh_user, ssh_password, target_ip).")
            return False, "Chybí SSH parametry."

        ssh_manager = SSHManager(target_ip, ssh_user, ssh_password, group_name)

        # Připojení k SSH
        if not await ssh_manager.connect():
            return False, "Nepodařilo se připojit k SSH."

        # Spuštění příkazu
        success, output = await ssh_manager.execute_command(command, use_sudo=True)

        # Odpojení od SSH
        await ssh_manager.close()

        return success, output

    except Exception as e:
        await send_to_websocket(group_name, f"Chyba při SSH příkazu: {str(e)}")
        return False, str(e)
    

from pymetasploit3.msfrpc import MsfRpcClient


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
            else:
                return {"error": "Chybí nastavený payload"}
            
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
    from pymetasploit3.msfrpc import MsfRpcClient
    loop = asyncio.get_event_loop()
    
    def run_command():
        session_id = context.get("session_id")
        if not session_id:
            return (False, "Session ID není dostupné.")

        try:
            client = MsfRpcClient("mysecret", server="127.0.0.1", port=55553)
            session = client.sessions.session(session_id)
            session.write(command)
            output = session.read()
            return (True, output)
        

        except Exception as e:
            traceback.print_exc()
            return False, f"Chyba v run_cmd: {e}"
    
    # 1) Spustíme v executor vlákně
    success, output = await loop.run_in_executor(None, run_command)

        # 2) Pošleme na frontend
    if group_name:
        await send_to_websocket(group_name, f" Výstup: {output}")

    return success, output

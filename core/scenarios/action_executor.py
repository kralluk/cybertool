import asyncio
import subprocess, paramiko
import os
import signal
from .globals import check_scenario_status, running_processes, ssh_manager
from .services import replace_placeholders, send_to_websocket
from .ssh_manager import SSHManager
from pymetasploit3.msfrpc import MsfRpcClient


async def execute_action(action, parameters, context, group_name):
    """
    Spustí akci a zavolá správného handlera podle typu akce.
    """

    action_type = action.get("type", "local")  # Defaultně předpokládáme `local`
    command = action.get("command", None)
    if command:
        command = replace_placeholders(command, parameters)


    if action_type == "local":
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
    
async def execute_metasploit_action(action, parameters, context, group_name):
    """
    Spustí Metasploit exploit (nebo libovolný 'exploit' modul) 
    s ohledem na placeholdery definované v akci (options).
    """
    # 1) Načteme options z akce
    final_options = action.get("options", {})

    # 2) Vytvoříme placeholder_context z context + parameters
    placeholder_context = {**context, **parameters}

    # 3) Nahradíme placeholdery
    replaced_options = {}
    for key, val in final_options.items():
        replaced_options[key] = replace_placeholders(val, placeholder_context)

    # 4) Získáme module_name z replaced_options
    module_name = replaced_options.pop("module", None)
    if not module_name:
        return False, "Chybí 'module' v options."

    # 5) Připojení k Metasploit RPC
    client = MsfRpcClient('mysecret', server='127.0.0.1', port=55553)

    # 6) Vytvoření exploitu
    exploit = client.modules.use('exploit', module_name)

    # 7) Nastavení voleb (kromě PAYLOAD)
    for key, value in replaced_options.items():
        if key.upper() == "PAYLOAD":
            continue
        exploit[key] = value

    # 8) Pokud je definován PAYLOAD
    payload_name = replaced_options.get("PAYLOAD")
    if payload_name:
        payload = client.modules.use('payload', payload_name)
    else:
        payload = None

    # 9) Spuštění exploitu
    job_result = exploit.execute(payload=payload)
    if not job_result:
        return False, "Nebyl vytvořen job pro exploit."

    # Může vrátit buď int job_id, nebo dict { 'job_id': int, 'uuid': ... }
    if isinstance(job_result, dict):
        actual_job_id = job_result.get("job_id")
    else:
        actual_job_id = job_result

    if not actual_job_id:
        return False, "Nepodařilo se získat job_id."

    # 10) Polling na dokončení jobu (max 30s)
    for _ in range(30):
        if actual_job_id not in client.jobs.list:
            break
        await asyncio.sleep(1)

    if actual_job_id in client.jobs.list:
        return False, "Exploit stále běží, vypršel timeout."

    # 11) Případně analyzuj session, logs atd.
    return True, "Exploit skončil úspěšně."
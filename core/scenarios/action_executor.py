import asyncio
import subprocess
import os
import signal
from .globals import check_scenario_status, running_processes
from .services import replace_placeholders, send_to_websocket


async def execute_action(action, parameters, context, group_name):
    """
    Spustí akci a zavolá správného handlera podle typu akce.
    """
    action_type = action.get("type", "local")  # Defaultně předpokládáme `local`
    command = replace_placeholders(action["command"], parameters)

    if action_type == "local":
        return await execute_local_command(command, group_name)
    elif action_type == "ssh":
        return await execute_ssh_command(action, parameters, group_name)
    # elif action_type == "metasploit":
    #     return await execute_metasploit_action(action, parameters, group_name)
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
                await send_to_websocket(group_name, "Akce byla zastavena uživatelem.")
                return False, "Akce byla zastavena uživatelem."

            await asyncio.sleep(0.5)

        stdout, stderr = await process.communicate()
        output = stdout.decode().strip() + "\n" + stderr.decode().strip()

        if process.returncode != 0:
            await send_to_websocket(group_name, f"Chyba při lokálním příkazu: {output}")
            return False, output

        await send_to_websocket(group_name, f"Výstup lokálního příkazu: {output}")
        return True, output

    finally:
        if process in running_processes:
            running_processes.remove(process)



async def execute_ssh_command(action, parameters, group_name):
    """
    Spustí příkaz přes SSH a vrátí výsledek.
    """
    try:
        ssh_user = parameters["ssh_user"]
        ssh_password = parameters["ssh_password"]
        target_ip = parameters["target_ip"]
        command = replace_placeholders(action["command"], parameters)

        # Příklad implementace SSH pomocí paramiko (nutno přidat jako závislost)
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(target_ip, username=ssh_user, password=ssh_password)

        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode().strip() + "\n" + stderr.read().decode().strip()
        client.close()

        if stderr.channel.recv_exit_status() != 0:
            await send_to_websocket(group_name, f"Chyba při SSH příkazu: {output}")
            return False, output

        await send_to_websocket(group_name, f"Výstup SSH příkazu: {output}")
        return True, output

    except Exception as e:
        await send_to_websocket(group_name, f"Chyba při SSH příkazu: {str(e)}")
        return False, str(e)

# PRIPRAVA NA METASPLOIT INTEGRACI

# async def execute_metasploit_action(action, parameters, group_name):
#     """
#     Spustí příkaz nebo modul Metasploitu (rozšiřitelné).
#     """
#     try:
#         # Příklad použití Metasploit RPC API (musíte nastavit MSF API na serveru)
#         import msfrpc
#         client = msfrpc.Msfrpc({})
#         client.login('msf', 'password')  # Nastavte přihlašovací údaje

#         module = action["module"]  # Např. `auxiliary/scanner/ssh/ssh_login`
#         options = {key: replace_placeholders(value, parameters) for key, value in action["options"].items()}

#         response = client.call('module.execute', [module, options])

#         await send_to_websocket(group_name, f"Metasploit akce spuštěna: {response}")
#         return True, response

#     except Exception as e:
#         await send_to_websocket(group_name, f"Chyba při Metasploit akci: {str(e)}")
#         return False, str(e)


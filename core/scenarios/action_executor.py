import subprocess, os, signal, threading, time
from .globals import check_scenario_status
from .services import replace_placeholders

def execute_action(action, parameters, context):
    """Spustí akci a vrátí výsledek."""
    command = action["command"]
    command = replace_placeholders(command, parameters)
    print(f"Spouštím příkaz: {command}")

    output = []

    def process_task():
        """Zpracuje příkaz lokálně nebo vzdáleně."""
        if command.startswith("ssh"):
            success, cmd_output = interact_with_ssh(parameters, command)  # Implementujte `interact_with_ssh`
        else:
            success, cmd_output = execute_local_command(command)
        output.append((success, cmd_output))

    # Spuštění ve vlákně
    process_thread = threading.Thread(target=process_task, daemon=True)
    process_thread.start()

    while process_thread.is_alive():
        if check_scenario_status():
            print("Scénář byl zastaven uživatelem.")
            break
        time.sleep(0.5)

    process_thread.join()

    if output:
        success, cmd_output = output[0]
        return success, cmd_output
    return False, "Akce selhala."

def execute_local_command(command):
    """Spustí příkaz lokálně."""
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid
        )

        stdout, stderr = process.communicate()
        output = stdout.strip() + "\n" + stderr.strip()
        if process.returncode != 0:
            return False, output
        return True, output
    except Exception as e:
        return False, str(e)


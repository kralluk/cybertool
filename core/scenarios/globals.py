from threading import Lock
import os
import signal
import asyncio
from pymetasploit3.msfrpc import MsfRpcClient

# Globální proměnná pro zastavení scénáře
stop_scenario = False

# Zámek pro synchronizaci přístupu k proměnné
scenario_lock = Lock()

# Seznam běžících procesů
running_processes = []

ssh_manager = None  # Uchovává SSH připojení

def stop_scenario_execution():
    """Nastaví stop_scenario na True a zastaví všechny běžící procesy."""
    global stop_scenario, ssh_manager
    with scenario_lock:
        stop_scenario = True

    # Ukončení všech běžících procesů
    for process in running_processes:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            print(f"Proces {process.pid} byl úspěšně ukončen.")
        except ProcessLookupError:
            print(f"Proces {process.pid} už neběží.")
        except Exception as e:
            print(f"Chyba při ukončení procesu {process.pid}: {e}")

    # Vyčištění seznamu běžících procesů
    running_processes.clear()

    if ssh_manager:
        asyncio.create_task(ssh_manager.stop_process())  # Zavoláme zastavení běžících SSH procesů
        print("Všechny SSH procesy ukončeny.")

def check_scenario_status():
    """Vrátí aktuální stav stop_scenario, synchronizovaně."""
    global stop_scenario
    with scenario_lock:
        return stop_scenario

def reset_scenario_status():
    """Resetuje stop_scenario na False a zajistí synchronizaci při zápisu."""
    global stop_scenario
    with scenario_lock:
        stop_scenario = False
        print("Stav scénáře resetován.")

def set_ssh_manager(manager):
    """Nastaví globální SSH manager."""
    global ssh_manager
    ssh_manager = manager
    print(f"SSH Manager byl úspěšně nastaven: {ssh_manager}")

# def stop_attack_processes():
#     """
#     Zastaví všechny aktuálně běžící útokové procesy, aniž by zastavila celý scénář.
#     (Tedy neovlivní globální flag stop_scenario.)
#     """
#     for process in running_processes:
#         try:
#             os.killpg(os.getpgid(process.pid), signal.SIGTERM)
#             print(f"Proces {process.pid} byl úspěšně ukončen.")
#         except ProcessLookupError:
#             print(f"Proces {process.pid} už neběží.")
#         except Exception as e:
#             print(f"Chyba při ukončení procesu {process.pid}: {e}")
#     running_processes.clear()

def stop_attack_processes(include_metasploit=False, context=None):
    # 1) lokální procesy
    print("Zastavuji všechny běžící procesy.")
    for proc in list(running_processes):
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except:
            pass
    running_processes.clear()

    # 2) metasploit cleanup
    if include_metasploit and context:
        try:
            client = MsfRpcClient("mysecret", server="127.0.0.1", port=55553)
        except:
            return
        # pokud máme session
        session_id = context.get("session_id")
        if session_id is not None:
            try: client.sessions.stop(session_id)
            except: pass
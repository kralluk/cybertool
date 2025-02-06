from threading import Lock
import os
import signal

# Globální proměnná pro zastavení scénáře
stop_scenario = False

# Zámek pro synchronizaci přístupu k proměnné
scenario_lock = Lock()

# Seznam běžících procesů
running_processes = []

def stop_scenario_execution():
    """Nastaví stop_scenario na True a zastaví všechny běžící procesy."""
    global stop_scenario
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
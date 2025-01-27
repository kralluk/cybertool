from threading import Lock

# Globální proměnná pro zastavení scénáře
stop_scenario = False

# Zámek pro synchronizaci přístupu k proměnné
scenario_lock = Lock()

def stop_scenario_execution():
    """Nastaví stop_scenario na True a zajistí synchronizaci při zápisu."""
    global stop_scenario
    with scenario_lock:
        stop_scenario = True

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
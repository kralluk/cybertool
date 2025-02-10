from django.shortcuts import render
from django.http import JsonResponse
from .network.services import save_and_set_default_network
from .network.scanner import scan_network
from .scenarios.services import get_all_scenarios, get_scenario_detail
from .scenarios.scenario_executor import execute_scenario
from .models import NetworkInfo
import asyncio

from django.shortcuts import render
from core.models import NetworkInfo

def home_view(request):
    networks = NetworkInfo.objects.all()

    # Pokud není v session žádná aktuální síť nebo není žádná síť v DB, nastavíme výchozí
    if 'current_network' not in request.session or not networks:
        current_network = save_and_set_default_network()
        request.session['current_network'] = str(current_network)
    else:
        current_network = request.session['current_network']

    message = None  # Výchozí hodnota pro hlášení

    # Zpracování změny sítě, pokud byl odeslán formulář
    if request.method == "POST":
        selected_network = request.POST.get("network")
        if selected_network and NetworkInfo.objects.filter(network=selected_network).count() > 0:
            request.session['current_network'] = selected_network
            message = f"Aktuální síť byla změněna na: {selected_network}"
        else:
            message = "Chyba při změně sítě. Zkontrolujte, zda je síť dostupná."

    return render(request, "core/home.html", {
        "current_network": current_network,
        "networks": networks,
        "message": message
    })
    
def scan_network_view(request):
    # Načtení aktuální sítě ze session
    current_network = request.session.get('current_network')

    if not current_network:
        return JsonResponse({"error": "Aktuální síť není nastavena."}, status=400)

    # Skenování sítě
    scan_results = scan_network(current_network)

    return JsonResponse({
        "message": f"Skenování sítě {current_network} bylo úspěšné.",
        "scan_results": scan_results
    })

def change_network_view(request):
    networks = NetworkInfo.objects.all()

    if request.method == "POST":
        selected_network = request.POST.get("network")
        if selected_network:
            # Uložíme aktuální síť do session
            request.session['current_network'] = selected_network
            return render(request, "core/change_network.html", {
                "networks": networks,
                "message": f"Aktuální síť byla změněna na: {selected_network}"
            })

    return render(request, "core/change_network.html", {"networks": networks})

def list_scenarios_view(request):
    # Načteme všechny scénáře
    scenarios = get_all_scenarios()
    return render(request, "core/list_scenarios.html", {"scenarios": scenarios})

def scenario_detail_view(request, scenario_id):
    # Načteme detail konkrétního scénáře
    scenario = get_scenario_detail(scenario_id)
    return render(request, "core/scenario_detail.html", {"scenario": scenario})


async def run_scenario_view(request, scenario_id):
    """
    Spustí scénář a pošle zprávy přes WebSocket.
    """
    if request.method == "POST":
        selected_network = request.POST.get("selected_network")
        if not selected_network:
            return JsonResponse({"error": "Vyberte síť pro spuštění scénáře."}, status=400)

        group_name = f"scenario_{scenario_id}"

        # Spuštění scénáře pomocí asynchronního tasku
        from core.scenarios.scenario_executor import execute_scenario
        asyncio.create_task(execute_scenario(scenario_id, selected_network, group_name))

        return JsonResponse({"message": f"Scénář '{scenario_id}' byl spuštěn."})

    return JsonResponse({"error": "Použijte POST metodu."}, status=405)
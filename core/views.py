from django.shortcuts import render
from django.http import JsonResponse
from .network.services import save_and_set_default_network
from .network.scanner import scan_network
from .scenarios.services import get_all_scenarios, get_scenario_detail
from .scenarios.scenario_executor import execute_scenario
from .models import NetworkInfo
import asyncio

def home_view(request):
    # Pokud není v session žádná aktuální síť nebo je prazne NetworkInfo, automaticky uložíme a nastavíme výchozí
    if 'current_network' not in request.session or not NetworkInfo.objects.all():
        print("Nastavuji výchozí síť.")
        current_network = save_and_set_default_network()
        request.session['current_network'] = str(current_network)
    else:
        # Načteme aktuální síť ze session
        print("Načítám aktuální síť ze session.")
        current_network = request.session['current_network']

    # Data pro zobrazení
    context = {
        "current_network": current_network,
    }
    return render(request, "core/home.html", context)

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
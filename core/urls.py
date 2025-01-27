from django.urls import path
from .views import home_view, scan_network_view, change_network_view, list_scenarios_view, scenario_detail_view

urlpatterns = [
    # path('active-interfaces/', list_active_interfaces, name='active_interfaces'),
    path('', home_view, name='home'),  # Hlavní stránka
    path('scan-network/', scan_network_view, name='scan_network'),  # Skenování sítě
    path('change-network/', change_network_view, name='change_network'),  # Změna výchozí sítě
    path('scenarios/', list_scenarios_view, name='list_scenarios'),  # Seznam scénářů
    path('scenarios/<str:scenario_id>/', scenario_detail_view, name='scenario_detail'),  # Detail scénáře
]
from core.models import NetworkInfo
from core.network.services import save_and_set_default_network

_data_initialized = False

class EnsureNetworkInfoMiddleware:
    """
    Middleware, který při každém HTTP requestu ověří, zda v databázi existují záznamy
    v modelu NetworkInfo. Pokud ne, načte a uloží výchozí sítě.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        global _data_initialized
        networks = NetworkInfo.objects.all()
        # for network in networks:
        #     print(f"Síť: {network.network}, IP: {network.ip_address}, Interface: {network.interface}")
        
        if not _data_initialized:
            #if NetworkInfo.objects.count() == 0: nefunguje
            if len(list(NetworkInfo.objects.all())) == 0:
                save_and_set_default_network()
                print("NetworkInfo nebyla nalezena – načetl jsem a uložil výchozí data.")
            _data_initialized = True
        response = self.get_response(request)
        return response
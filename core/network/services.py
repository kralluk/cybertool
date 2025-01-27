# Soubor pro vytvoření služeb pro síťové operace

import psutil
import socket
import ipaddress
from core.models import NetworkInfo 

def get_active_interfaces():
    interfaces = psutil.net_if_addrs()
    active_interfaces = []

    for interface, addresses in interfaces.items():
        for addr in addresses:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                network = ipaddress.IPv4Network(f"{addr.address}/24", strict=False)
                active_interfaces.append((interface, addr.address, network))

    return active_interfaces


def save_network_info_to_db(interfaces):
    # Smazání starých dat
    NetworkInfo.objects.delete()

    # Uložení nových dat
    for iface, ip, net in interfaces:
        NetworkInfo(interface=iface, ip_address=ip, network=str(net)).save()


def save_and_set_default_network():
    # Získáme aktivní rozhraní
    interfaces = get_active_interfaces()

    # Smažeme stará data
    NetworkInfo.objects.delete()

    # Uložíme nová data a nastavíme výchozí síť
    default_network = None
    for iface, ip, net in interfaces:
        NetworkInfo(interface=iface, ip_address=ip, network=str(net)).save()
        if iface == "eth0":
            default_network = net

    # Pokud není eth0, použijeme první dostupnou síť
    if not default_network and interfaces:
        default_network = interfaces[0][2]

    return default_network  # Vrací výchozí síť


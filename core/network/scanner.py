import nmap

def scan_network(network):
    """
    Skenuje zadanou síť pomocí Nmapu.
    """
    nm = nmap.PortScanner()
    scan_results = []

    try:
        nm.scan(hosts=str(network), arguments='-sn')  # Skenování bez portů (ping scan)
        for host in nm.all_hosts():
            scan_results.append({
                "ip": host,
                "state": nm[host].state(),
                "hostname": nm[host].hostname()
            })
    except Exception as e:
        print(f"Chyba při skenování sítě: {e}")

    return scan_results
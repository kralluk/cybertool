import asyncio
import shlex
from core.scenarios.globals import check_scenario_status

async def start_sniffer(interface, target_ip, group_name):
    """
    Spustí tshark a vrátí handle (např. process) nebo tasks pro čtení a analýzu.
    Můžeš parametry přizpůsobit – filtr, výstup do PCAP atd.
    """
    pcap_file = f"/capture_{target_ip}.pcap"

    cmd = f"tshark -i {interface} -f 'host {target_ip}' -w {pcap_file}"


    # cmd = f"tshark -i {interface} -f 'host {target_ip}' -l -T fields -e frame.time -e ip.src -e ip.dst"
    # -l zaručí "line-buffered" výstup; -T fields a -e ip.src atd. jsou příklad textového výstupu
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Tady spustíš analyzátor v jiné asynchronní úloze
    task = asyncio.create_task(monitor_output(process, group_name))

    return process, task

async def monitor_output(process, group_name):
    """
    Čte řádky z process.stdout, analyzuje je (např. kdo je src/dst),
    a vyhodnocuje, jestli došlo k blokaci, atd.
    """
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        
        decoded = line.decode().strip()
        # Tady se můžou parsovat sloupce – např. time, ip.src, ip.dst
        # Můžeš klidně zavolat send_to_websocket, logovat si, cokoliv
        # Nebo sledovat, jestli se tam objevuje traffic z cíl -> útočník

        # Případný check scénáře (pokud budeš chtít zastavit)
        if check_scenario_status():
            process.kill()
            break

    # Až skončí loop, tshark se pravděpodobně ukončil
    # Můžeš tady do kontextu scénáře zapsat, co jsi zjistil atd.

async def stop_sniffer(process):
    """ 
    Jednoduše killne tshark
    """
    if process:
        process.terminate()
        await process.wait()
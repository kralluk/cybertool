import asyncio
import os
from core.scenarios.globals import check_scenario_status
from core.scenarios.services import send_to_websocket
from core.network.detectors import BlockageDetector


# -------------------------
#  REALTIME ANALYSIS
# -------------------------

_realtime_process = None
_realtime_task = None

async def start_realtime_analysis(interface, target_ip, attacker_ip, group_name, context):
    cmd = [
        "tshark",
        "-i", interface,
        "-l", # Line buffered
        "-f", f"host {target_ip}",
        "-T", "fields",
        "-e", "ip.src",
        "-e", "ip.dst",
        "-e", "tcp.flags.reset",
        "-e", "icmp.type",
        "-e", "icmp.code"
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Tady vytvoříme list (nebo dict) detektorů PRO TSHARK
    detectors = [
        BlockageDetector(target_ip, attacker_ip, block_timeout=20.0),
        # V Budoucnu může být víc detektorů, např.: DNS, HTTP, ...
    ]

    task = asyncio.create_task(_realtime_analysis_loop(process, group_name, context, detectors))

    return process, task 

async def _realtime_analysis_loop(process, group_name, context, detectors, poll_interval=0.2):
    """
    Čte řádky z tshark stdout a předává je detektorům, které mohou 
    reagovat na pakety a aktualizovat např. context (blokace atd.).
    
    Argumenty:
      - process: Subprocess (tshark) s otevřeným stdout.
      - group_name: WebSocket group, kam posíláme logy.
      - context: sdílený slovník (např. scenario context), kde lze nastavovat ip_blocked atp.
      - detectors: seznam nebo dict detektorů, které umí zpracovat každý řádek (paket).
      - poll_interval: čas (s), po kterém každou iteraci spánku 
        dáváme šanci detektorům zkontrolovat timeouty atd.
    """
    print("[RealtimeAnalysis] Start dekódovaného výstupu.")
    while True:
        # 1) Check jestli scénář není zastaven
        if check_scenario_status():
            process.terminate()
            break
        # 2) Přečti řádku z tsharku
        line = await process.stdout.readline()
        if not line:
            # tshark skončil?
            break
        decoded = line.decode().strip()
        if decoded:
            # Každé slovo může být odděleno tabulátory, např.:
            # ip.src, ip.dst, tcp.flags.reset, icmp.type, icmp.code, ...
            splitted = decoded.split("\t")

            # 3) Pošli řádku všem detektorům
            for det in detectors:
                det.handle_packet_line(splitted, context)
        # 4) Po krátké pauze dáme detektorům možnost provést kontrolu (timeouty atd.)
        await asyncio.sleep(poll_interval)
        for det in detectors:
            det.periodic_check(context)

    print("[RealtimeAnalysis] Smyčka ukončena, tshark skončil.")

async def stop_realtime_analysis():
    """
    Ukončí realtime analýzu, pokud běží.
    """
    global _realtime_process, _realtime_task

    # Zrušíme task (pokud existuje)
    if _realtime_task and not _realtime_task.done():
        _realtime_task.cancel()
        try:
            await _realtime_task
        except asyncio.CancelledError:
            pass
        _realtime_task = None

    # Pošleme terminate tsharku
    if _realtime_process:
        _realtime_process.terminate()
        try:
            await _realtime_process.wait()
        except ProcessLookupError:
            pass
        _realtime_process = None

    print("[RealtimeAnalysis] Ukončena realtime analýza.")
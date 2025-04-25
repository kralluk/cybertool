import time, asyncio
from pymetasploit3.msfrpc import MsfRpcClient
from core.scenarios.services import send_to_websocket
from core.scenarios.globals import stop_scenario_execution



# Detekor blokace pro realtime monitoring TSHARKu
class BlockageDetector:
    """
    Detektor blokace na základě RST, ICMP administratively prohibited
    a časové heuristiky (pokud cíl X sekund neposlal packet útočníkovi).
    """
    def __init__(self, target_ip, attacker_ip, block_timeout=20.0): # Defaultn9 je 20 sekund
        self.target_ip = target_ip
        self.attacker_ip = attacker_ip
        self.block_timeout = block_timeout
        self.last_response_time = time.time()  # Kdy naposled cíl něco poslal
        self.blockage_reported = False

    def handle_packet_line(self, splitted, context):
        """
        splitted je list z decode.split("\t"), např.:
          [ip.src, ip.dst, tcp.flags.reset, icmp.type, icmp.code, ...]
        Můžeme být flexibilní, pokud je tam víc sloupců.
        """
        src = splitted[0] if len(splitted) > 0 else ""
        dst = splitted[1] if len(splitted) > 1 else ""
        rst_flag = splitted[2] if len(splitted) > 2 else ""
        icmp_type = splitted[3] if len(splitted) > 3 else ""
        icmp_code = splitted[4] if len(splitted) > 4 else ""

        # 1) Pokud cíl poslal RST -> ip_blocked = True
        if src == self.target_ip and rst_flag == "1":
            context["ip_blocked"] = True

        # 2) ICMP administratively prohibited (typ=3, code=13)
        if src == self.target_ip and icmp_type == "3" and icmp_code == "13":
            context["ip_blocked"] = True

        # 3) Pokud cíl poslal *cokoliv* útočníkovi, resetujeme last_response_time
        if src == self.target_ip and dst == self.attacker_ip:
            self.last_response_time = time.time()

    def periodic_check(self, context):
        """
        Každá 'iterace' smyčky dostane šanci na extra kontrolu,
        např. zda neuplynulo moc času od posledního packetu od cíle.
        """
        if self.blockage_reported:
            return # Už jsme to reportovali, nemá cenu znovu
        if (time.time() - self.last_response_time) > self.block_timeout:
            # Timeout => cíl se odmlčel => považujeme za blok
            print(f"[BlockageDetector] cíl {self.target_ip} se odmlčel na více než {self.block_timeout} s.")
            context["ip_blocked"] = True
            self.blockage_reported = True

class MetasploitSessionDetector:
    """
    Detektor, který hlídá, jestli prostřelená Metasploit session stále běží.
    Jakmile session zanikne, zapíše do context['msf_session_closed'] = True.
    """
    def __init__(self, session_id: str, group_name: str, context: dict, poll_interval: float = 5.0):
        self.session_id = str(session_id)
        self.group = group_name
        self.context = context
        self.interval = poll_interval
        self.client = MsfRpcClient("mysecret", server="127.0.0.1", port=55553)
        self._running = True

    async def start(self):
        while self._running: # and not stop_scenario_execution():
            try:
                # 1) Zkontrolujeme, zda je session stále v seznamu
                session_ids = list(map(str, self.client.sessions.list.keys()))
                if self.session_id not in session_ids:
                    # await send_to_websocket(self.group, "[MetasploitSessionDetector] Detekována pravděpodobné ukončení session.")
                    self.context["msf_session_closed"] = True
                    break

                # 2) Zkusíme lehkou interakci – echo
                sess = self.client.sessions.session(self.session_id)
                try:
                    sess.write(" ")  # pokud to vyhodí, session je pryč
                except Exception:
                    # await send_to_websocket(self.group, "[MetasploitSessionDetector] Detekována pravděpodobné ukončení session")
                    self.context["msf_session_closed"] = True
                    break

            except Exception as e:
                print(f"[MetasploitSessionDetector] Chyba detektoru: {e}")
                # v případě chyby rozhodneme o ukončení detektoru
                break

            await asyncio.sleep(self.interval)

        # await send_to_websocket(self.group, "[MetasploitSessionDetector] Detektor ukončen.")

    def stop(self):
        self._running = False
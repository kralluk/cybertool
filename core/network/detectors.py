import time

class BlockageDetector:
    """
    Detektor blokace na základě RST, ICMP administratively prohibited
    a časové heuristiky (pokud cíl X sekund neposlal packet útočníkovi).
    """
    def __init__(self, target_ip, attacker_ip, block_timeout=5.0):
        self.target_ip = target_ip
        self.attacker_ip = attacker_ip
        self.block_timeout = block_timeout
        self.last_response_time = time.time()  # Kdy naposled cíl něco poslal

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
        if (time.time() - self.last_response_time) > self.block_timeout:
            # Timeout => cíl se odmlčel => považujeme za blok
            print(f"[BlockageDetector] cíl {self.target_ip} se odmlčel na více než {self.block_timeout} s.")
            context["ip_blocked"] = True
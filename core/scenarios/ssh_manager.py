import paramiko
import time
import asyncio
from channels.layers import get_channel_layer
from .globals import check_scenario_status

class SSHManager:
    def __init__(self, target_ip, ssh_user, ssh_password, group_name):
        self.target_ip = target_ip
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password
        self.group_name = group_name
        self.client = None

    async def connect(self):
        """Připojí se k SSH serveru."""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.client.connect(
                hostname=self.target_ip,
                username=self.ssh_user,
                password=self.ssh_password,
                look_for_keys=False,
                allow_agent=False
            )
            await self.send_to_websocket(f"Připojení k {self.target_ip} jako {self.ssh_user} úspěšné.")
            return True
        except Exception as e:
            await self.send_to_websocket(f"Chyba při připojení k {self.target_ip}: {str(e)}")
            return False


    async def execute_command(self, command, use_sudo=False):
        """Asynchronně spustí SSH příkaz. Pokud `use_sudo=True`, spustí se jako sudo."""
        if not self.client:
            await self.send_to_websocket("Není navázáno SSH připojení.")
            return False, "SSH připojení není aktivní."

        try:
            if use_sudo:
                command = f"sudo -S {command}"

            # Použití Pseudo-terminalu (PTY), aby bylo možné zadat heslo
            await self.send_to_websocket(f"Spouštím SSH příkaz: `{command}`")
            loop = asyncio.get_event_loop()
            stdin, stdout, stderr = await loop.run_in_executor(None, lambda: self.client.exec_command(command, get_pty=True))

            if use_sudo:
                await asyncio.sleep(0.5)  # Počkáme na výzvu k zadání hesla
                stdin.write(self.ssh_password + "\n")  # Pošleme heslo
                stdin.flush()

                        # Čtení výstupu po řádcích a posílání na WebSocket
            async for line in self._stream_output(stdout, stderr):
                await self.send_to_websocket(line)


            output = await loop.run_in_executor(None, stdout.read)
            error = await loop.run_in_executor(None, stderr.read)

            output = output.decode().strip()
            error = error.decode().strip()

            if error:
                await self.send_to_websocket(f"Chyba při spuštění příkazu: {error}")
                return False, error

            await self.send_to_websocket(f"Výstup příkazu: {output}")
            return True, output
        except Exception as e:
            await self.send_to_websocket(f"Chyba při spuštění příkazu: {str(e)}")
            return False, str(e)


    async def close(self):
        """Ukončí SSH připojení."""
        if self.client:
            self.client.close()
            await self.send_to_websocket(f"Odpojení od {self.target_ip}.")

    async def send_to_websocket(self, message):
        """Pošle zprávu do WebSocketu."""
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            self.group_name,
            {"type": "send_message", "message": message}
        )


    async def _stream_output(self, stdout, stderr):
        """Postupně čte výstup z SSH spojení a odesílá jej po řádcích."""
        loop = asyncio.get_event_loop()

        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                line = await loop.run_in_executor(None, stdout.readline)
                if line:
                    yield line.strip()

            if stderr.channel.recv_stderr_ready():
                line = await loop.run_in_executor(None, stderr.readline)
                if line:
                    yield f"ERROR: {line.strip()}"

            await asyncio.sleep(0.1)  # Malá prodleva, aby se zabránilo blokování

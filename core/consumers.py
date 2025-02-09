from channels.generic.websocket import AsyncWebsocketConsumer
import json
from core.scenarios.globals import stop_scenario_execution
import  asyncio

class ScenarioConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.scenario_id = self.scope['url_route']['kwargs']['scenario_id']
        self.group_name = f"scenario_{self.scenario_id}"

        # Připojení ke skupině
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

        # # Debug: Zpráva po připojení
        # await self.send(text_data=json.dumps({
        #     "message": f"WebSocket připojen ke scénáři {self.scenario_id}."
        # }))

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get("action") == "start_scenario":
            current_network = self.scope["session"].get("current_network", None)

            if not current_network:
                await self.send(text_data=json.dumps({
                    "message": "Chybí aktuální síť (current_network) v session."
                }))
                return

            # Spustí scénář na pozadí
            from core.scenarios.scenario_executor import execute_scenario
            asyncio.create_task(execute_scenario(self.scenario_id, current_network, self.group_name))

            # Odeslání zprávy zpět klientovi
            await self.send(text_data=json.dumps({
                "message": f"Scénář byl spuštěn na síti {current_network}."
              #  "message": f"Scénář {self.scenario_id} byl spuštěn na síti {current_network}."
            }))
        
        
        elif data.get("action") == "stop_scenario":
            # Zavolá funkci na zastavení scénáře
            stop_scenario_execution()
            
            # Pošle zprávu všem klientům, že scénář byl zastaven
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "send_message", "message": "Scénář byl zastaven uživatelem."}
            )

            
    async def send_message(self, event):
        """
        Zpracuje zprávu typu `send_message` a pošle ji zpět klientovi.
        """
        message = event["message"]
        print(f"ODESÍLÁM NA FRONTEND: {message}")  
        await self.send(text_data=json.dumps({"message": message}))
        
    async def disconnect(self, close_code):
        # Odpojení od skupiny
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    
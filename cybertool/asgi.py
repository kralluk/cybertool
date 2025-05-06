"""
ASGI config for cybertool project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import subprocess

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from core.routing import websocket_urlpatterns
import core.routing

from channels.sessions import SessionMiddlewareStack 

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cybertool.settings')

# print("[GlobalAnalysis] Spouštím global capture na eth1.")
# os.makedirs("pcaps", exist_ok=True)

# capture_process = subprocess.Popen([
#     "tshark",
#     "-i", "eth1",
#     "-w", "pcaps/eth1_capture.pcap",
#     "-b", "filesize:50000",
#     "-b", "files:5",
# ])


application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),


# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": SessionMiddlewareStack(  # ⬅️ To je klíčové!
#         AuthMiddlewareStack(
#             URLRouter(
#                 core.routing.websocket_urlpatterns
#             )
#         )
#     ),

})


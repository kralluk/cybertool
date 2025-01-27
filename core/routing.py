from django.urls import path
from .consumers import ScenarioConsumer

websocket_urlpatterns = [
    path('ws/scenario/<str:scenario_id>/', ScenarioConsumer.as_asgi()),
]
# Mapa de rotas WebSocket (ASGI) do app display -- equivalente ao
# core/urls.py, mas para conexoes ws:// em vez de HTTP.
from django.urls import re_path

from apps.display.consumers.painel_consumer import PainelChamadaConsumer
from apps.display.consumers.paciente_notificacao import PacienteNotificacaoConsumer

websocket_urlpatterns = [
    re_path(r"ws/painel-chamada/$", PainelChamadaConsumer.as_asgi()),
    re_path(r"ws/paciente/(?P<cpf>[^/]+)/$", PacienteNotificacaoConsumer.as_asgi()),
]

# Rotas do app system, montadas sob /sistema/ em config/urls.py -- as
# duas acoes de recepcao sobre a fila (chamar e marcar ausente).
from django.urls import path

from apps.system import views

urlpatterns = [
    path("chamar/", views.chamar_paciente_view, name="chamar-paciente"),
    path("marcar-ausente/", views.marcar_ausente_view, name="marcar-ausente"),
]

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.mobile.api.views import EncaixeViewSet, FilaViewSet, PacienteAuthViewSet, PesquisaSatisfacaoViewSet

router = DefaultRouter()
router.register("encaixes", EncaixeViewSet, basename="api-encaixe")
router.register("fila", FilaViewSet, basename="api-fila")
router.register("pacientes", PacienteAuthViewSet, basename="api-pacientes")
router.register("pesquisa-satisfacao", PesquisaSatisfacaoViewSet, basename="api-pesquisa-satisfacao")

urlpatterns = router.urls

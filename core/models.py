# Caminho de import historico: o codigo (views, services, testes) importa
# os modelos como core.models.X. Os modelos de verdade vivem em
# apps/core_domain/models/ -- este arquivo so os reexporta pra nao quebrar
# quem ainda referencia o caminho antigo.
from apps.core_domain.models import *

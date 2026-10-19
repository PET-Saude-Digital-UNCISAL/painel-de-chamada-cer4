"""Ator atual: o UsuarioSistema responsavel pela operacao em andamento.

Guardado num ContextVar (e nao em thread-local) porque o projeto roda sob
ASGI/Daphne: o contexto acompanha a requisicao tanto no caminho async
quanto nas views sync que o Django executa em thread via sync_to_async.

So o id e guardado -- os mixins de auditoria gravam direto em
`criado_por_id`/`atualizado_por_id`/`excluido_por_id`, sem precisar
buscar o UsuarioSistema no banco.

Quem define o ator:
- nas requisicoes HTTP, o AtorAtualMiddleware, a partir de
  `staff_usuario_id` na sessao;
- fora de requisicao (integrador, importer, comandos de manage.py), o
  codigo chamador, com `usando_ator(...)`.

Paciente nunca e ator: sem staff logado o ator fica None e os campos
"por" ficam vazios.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

_ator_atual_id: ContextVar[int | None] = ContextVar("ator_atual_id", default=None)


def _para_id(ator) -> int | None:
    """Aceita um UsuarioSistema, um id ou None."""
    if ator is None:
        return None
    return getattr(ator, "pk", ator)


def get_ator_atual_id() -> int | None:
    """Id do UsuarioSistema da operacao atual, ou None se nao ha staff."""
    return _ator_atual_id.get()


def definir_ator(ator):
    """Define o ator atual e devolve o token pra `restaurar_ator`.

    Prefira `usando_ator`; esta funcao existe pro middleware, que precisa
    abrir e fechar o contexto em pontos diferentes."""
    return _ator_atual_id.set(_para_id(ator))


def restaurar_ator(token) -> None:
    _ator_atual_id.reset(token)


@contextmanager
def usando_ator(ator):
    """Executa o bloco com `ator` (UsuarioSistema, id ou None) como ator
    atual, restaurando o anterior no fim -- inclusive em caso de erro."""
    token = definir_ator(ator)
    try:
        yield
    finally:
        restaurar_ator(token)


def sem_ator(func):
    """Decorator pras acoes do paciente: grava os campos "por" vazios
    mesmo que haja staff logado na mesma sessao (ex.: tablet da recepcao
    usado pelo paciente pro proprio check-in). Serve pra views e pra
    metodos de ViewSet."""

    @wraps(func)
    def _wrapped(*args, **kwargs):
        with usando_ator(None):
            return func(*args, **kwargs)

    return _wrapped

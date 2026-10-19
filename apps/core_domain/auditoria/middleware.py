"""Middleware que define o ator atual a partir da sessao do staff.

Le so `staff_usuario_id` da sessao, sem consultar UsuarioSistema -- quem
valida se o usuario existe e esta ativo continuam sendo os decorators de
core/auth_decorators.py. A sessao do paciente (`paciente_id`) e ignorada
de proposito: paciente nunca e registrado como autor.

Precisa vir depois do SessionMiddleware em settings.MIDDLEWARE.
"""

from asgiref.sync import iscoroutinefunction, markcoroutinefunction

from apps.core_domain.auditoria.contexto import definir_ator, restaurar_ator

CHAVE_SESSAO_STAFF = "staff_usuario_id"


class AtorAtualMiddleware:
    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    def __call__(self, request):
        if iscoroutinefunction(self):
            return self.__acall__(request)
        token = definir_ator(_staff_da_sessao(request.session.get(CHAVE_SESSAO_STAFF)))
        try:
            return self.get_response(request)
        finally:
            restaurar_ator(token)

    async def __acall__(self, request):
        # Sob ASGI o acesso sync a sessao levantaria SynchronousOnlyOperation
        # (a sessao e carregada do banco na primeira leitura).
        uid = await request.session.aget(CHAVE_SESSAO_STAFF)
        token = definir_ator(_staff_da_sessao(uid))
        try:
            return await self.get_response(request)
        finally:
            restaurar_ator(token)


def _staff_da_sessao(uid) -> int | None:
    """A sessao guarda o pk como int, mas um valor corrompido nao pode
    derrubar a requisicao -- nesse caso a operacao segue sem ator."""
    try:
        return int(uid) if uid is not None else None
    except (TypeError, ValueError):
        return None

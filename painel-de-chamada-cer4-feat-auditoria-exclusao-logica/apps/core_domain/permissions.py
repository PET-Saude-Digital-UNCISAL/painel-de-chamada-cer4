"""Enforcement real da hierarquia de níveis de acesso.

Substitui a simulação client-side que existia em configuracoes.html: as
permissões de cada nível (recepcionista / coordenação / super admin) agora
são lidas do banco (`NivelAcessoPermissao`) e checadas no servidor.
"""

from apps.core_domain.models import NivelAcessoPermissao


def usuario_tem_permissao(usuario, permissao: str) -> bool:
    """Retorna True se `usuario` (UsuarioSistema) tiver a permissão ativa
    para o seu nível de acesso."""
    if not usuario or not getattr(usuario, "usuario_ativo", True):
        return False
    return NivelAcessoPermissao.objects.filter(
        nivel_acesso=usuario.nivel_acesso,
        permissao=permissao,
        ativo=True,
    ).exists()


def permissoes_do_nivel(nivel_acesso: str) -> set[str]:
    """Retorna o conjunto de chaves de permissão ativas para um nível."""
    return set(
        NivelAcessoPermissao.objects.filter(
            nivel_acesso=nivel_acesso, ativo=True
        ).values_list("permissao", flat=True)
    )


def mapa_permissoes_por_nivel() -> dict:
    """Retorna {nivel_acesso: {permissao: bool}} para todos os níveis —
    usado para montar a tela de Controle de Níveis de Acesso."""
    from apps.core_domain.models import UsuarioSistema

    mapa = {nivel: {} for nivel, _ in UsuarioSistema.NivelAcesso.choices}
    for registro in NivelAcessoPermissao.objects.all():
        mapa.setdefault(registro.nivel_acesso, {})[registro.permissao] = registro.ativo
    return mapa

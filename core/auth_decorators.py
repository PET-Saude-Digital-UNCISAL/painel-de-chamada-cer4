"""Decorators de autenticacao/autorizacao para as views da area interna
(sistema institucional). Nao usa o sistema de auth padrao do Django --
o login de UsuarioSistema e proprio, guardado na sessao como
`staff_usuario_id`.
"""

from functools import wraps

from django.http import JsonResponse
from django.shortcuts import redirect, render

from core.models import UsuarioSistema


def _requisicao_ajax(request):
    """Distingue uma chamada AJAX/fetch de uma navegacao normal de pagina,
    pra decidir se a resposta de erro deve ser JSON (pro JS tratar) ou um
    redirect/render de pagina inteira."""
    return request.headers.get("x-requested-with") == "XMLHttpRequest" or request.content_type == "application/json"


def staff_required(view_func):
    """Exige apenas que exista um UsuarioSistema ativo logado na sessao,
    sem checar permissao especifica nenhuma. Views que precisam de uma
    permissao pontual devem usar `permissao_requerida` em vez deste."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        uid = request.session.get("staff_usuario_id")
        usuario = UsuarioSistema.objects.filter(pk=uid, usuario_ativo=True).first() if uid else None
        if not usuario:
            if _requisicao_ajax(request):
                return JsonResponse({"ok": False, "erro": "Autenticação necessária."}, status=401)
            return redirect("login")
        request.staff_usuario = usuario
        return view_func(request, *args, **kwargs)
    return _wrapped


def permissao_requerida(permissao):
    """Exige que o usuário staff logado tenha a permissão informada,
    de acordo com o nível de acesso dele (ver NivelAcessoPermissao).

    Deve ser aplicado a views já cobertas por login (implica staff_required
    caso a view ainda não tenha essa checagem)."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            from apps.core_domain.permissions import usuario_tem_permissao

            uid = request.session.get("staff_usuario_id")
            usuario = UsuarioSistema.objects.filter(pk=uid, usuario_ativo=True).first() if uid else None
            if not usuario:
                if _requisicao_ajax(request):
                    return JsonResponse({"ok": False, "erro": "Autenticação necessária."}, status=401)
                return redirect("login")
            if not usuario_tem_permissao(usuario, permissao):
                if _requisicao_ajax(request):
                    return JsonResponse(
                        {"ok": False, "erro": "Seu nível de acesso não tem permissão para esta ação."},
                        status=403,
                    )
                return render(request, "core/acesso_negado.html", {"usuario": usuario}, status=403)
            request.staff_usuario = usuario
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator

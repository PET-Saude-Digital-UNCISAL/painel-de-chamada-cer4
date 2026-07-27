from functools import wraps

from django.http import JsonResponse
from django.shortcuts import redirect

from core.models import UsuarioSistema


def staff_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        uid = request.session.get("staff_usuario_id")
        usuario = UsuarioSistema.objects.filter(pk=uid, usuario_ativo=True).first() if uid else None
        if not usuario:
            if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.content_type == "application/json":
                return JsonResponse({"ok": False, "erro": "Autenticação necessária."}, status=401)
            return redirect("login")
        request.staff_usuario = usuario
        return view_func(request, *args, **kwargs)
    return _wrapped

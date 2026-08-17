import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.test_settings")
django.setup()

from django.test.utils import setup_test_environment, teardown_test_environment
from django.test.runner import DiscoverRunner
from django.test import Client

runner = DiscoverRunner()
old_config = runner.setup_databases()
setup_test_environment()

try:
    from core.models import UsuarioSistema, NivelAcessoPermissao

    recep = UsuarioSistema(nome_completo="Recep Teste", email_institucional="recep@t.com", cpf="11111111111", nivel_acesso="recepcionista")
    recep.set_senha("123456")
    recep.save()

    coord = UsuarioSistema(nome_completo="Coord Teste", email_institucional="coord@t.com", cpf="22222222222", nivel_acesso="coordenacao")
    coord.set_senha("123456")
    coord.save()

    admin = UsuarioSistema(nome_completo="Admin Teste", email_institucional="admin@t.com", cpf="33333333333", nivel_acesso="super_admin")
    admin.set_senha("123456")
    admin.save()

    print("Seed inicial de permissões:", list(NivelAcessoPermissao.objects.values_list("nivel_acesso", "permissao", "ativo")))

    c = Client()

    # 1) Recepcionista NÃO deve acessar auditoria (view real, staff_required trocado por permissao_requerida)
    session = c.session
    session["staff_usuario_id"] = recep.pk
    session.save()
    r = c.get("/telas/auditoria-percurso-seguranca/")
    print("Recepcionista GET auditoria ->", r.status_code, "(esperado 403)")

    # 2) Coordenação DEVE acessar auditoria
    session["staff_usuario_id"] = coord.pk
    session.save()
    r = c.get("/telas/auditoria-percurso-seguranca/")
    print("Coordenação GET auditoria ->", r.status_code, "(esperado 200)")

    # 3) Recepcionista consegue acessar /configuracoes/ mas sem poder gerenciar usuários (is_admin False)
    session["staff_usuario_id"] = recep.pk
    session.save()
    r = c.get("/configuracoes/")
    print("Recepcionista GET configuracoes ->", r.status_code)
    print("  is_admin no contexto:", r.context["is_admin"] if r.context else None)
    print("  pode_editar_permissoes:", r.context["pode_editar_permissoes"] if r.context else None)

    # 4) Coordenação consegue gerenciar usuários (is_admin True) mas NAO editar permissoes
    session["staff_usuario_id"] = coord.pk
    session.save()
    r = c.get("/configuracoes/")
    print("Coordenação is_admin:", r.context["is_admin"], "| pode_editar_permissoes:", r.context["pode_editar_permissoes"])

    # 5) Coordenação tenta salvar permissões via endpoint -> deve ser 403 (só super_admin)
    import json
    r = c.post(
        "/configuracoes/permissoes/salvar/",
        data=json.dumps({"nivel_acesso": "recepcionista", "permissoes": {"auditoria": True}}),
        content_type="application/json",
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    print("Coordenação POST salvar-permissoes ->", r.status_code, "(esperado 403)", r.json())

    # 6) Super Admin consegue salvar permissões, dando 'auditoria' para recepcionista
    session["staff_usuario_id"] = admin.pk
    session.save()
    r = c.post(
        "/configuracoes/permissoes/salvar/",
        data=json.dumps({"nivel_acesso": "recepcionista", "permissoes": {"auditoria": True, "checkin": True}}),
        content_type="application/json",
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    print("Super Admin POST salvar-permissoes ->", r.status_code, "(esperado 200)", r.json())

    # 7) Confirma que agora recepcionista TEM acesso a auditoria (permissão persistida de verdade)
    session["staff_usuario_id"] = recep.pk
    session.save()
    r = c.get("/telas/auditoria-percurso-seguranca/")
    print("Recepcionista GET auditoria APÓS conceder permissão ->", r.status_code, "(esperado 200)")

    # 8) chamar_paciente_view (apps/system) continua exigindo permissao 'checkin' (todos tem por padrao)
    r = c.post("/sistema/chamar/", {"senha": "X999", "sala": "Sala 1"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    print("Recepcionista POST chamar (sem paciente cadastrado) ->", r.status_code, "(esperado 404, nao 403 - prova que passou pela checagem de permissao)")

finally:
    teardown_test_environment()
    runner.teardown_databases(old_config)
    print("OK - suite finalizada")

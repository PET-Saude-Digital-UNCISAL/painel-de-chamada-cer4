import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.test_settings")
django.setup()

from django.test.runner import DiscoverRunner
from django.test.utils import setup_test_environment, teardown_test_environment
from django.test import Client

runner = DiscoverRunner()
old_config = runner.setup_databases()
setup_test_environment()

try:
    from datetime import date
    from core.models import UsuarioSistema, Paciente, Agendamento, EncaixePaciente
    from core.services import registrar_checkin, get_painel_chamada_context

    staff = UsuarioSistema(nome_completo="Admin Teste", email_institucional="a@t.com", cpf="11122233396", nivel_acesso="super_admin")
    staff.set_senha("123456")
    staff.save()

    paciente = Paciente.objects.create(
        nome_completo="Paciente Sessao Mista",
        cpf="39053344705",
        data_nascimento=date(1990, 5, 10),
        nome_mae="Mae Teste",
        paciente_ativo=True,
    )
    Agendamento.objects.create(paciente=paciente, data_agendamento=date.today(), status=Agendamento.Status.AGENDADO)

    # 1) Simula sessao ja contaminada (staff logado + paciente_id presente),
    #    como aconteceria ANTES do flush existir, para garantir que a
    #    blindagem em meu_perfil_view tambem funciona (defesa em profundidade).
    c = Client()
    session = c.session
    session["staff_logged_in"] = True
    session["staff_usuario_id"] = staff.pk
    session["paciente_id"] = paciente.pk
    session.save()

    r_perfil = c.get("/meu-perfil/?interno=1")
    body = r_perfil.content.decode()
    print("1) GET /meu-perfil/ com sessao contaminada ->", r_perfil.status_code)
    print("   contem nome do paciente?", "Paciente Sessao Mista" in body)
    print("   contem 'Super Admin' (papel do staff)?", "Super Admin" in body)
    print("   contem 'Paciente' (papel correto p/ instancia=paciente)?", ">Paciente<" in body or "Paciente</" in body)

    # 2) Verifica que o checkin via view real agora faz flush (sem sessao mista)
    c2 = Client()
    session2 = c2.session
    session2["staff_logged_in"] = True
    session2["staff_usuario_id"] = staff.pk
    session2.save()

    r_checkin = c2.post("/identificacao-paciente/", {
        "cpf": paciente.cpf,
        "data_nascimento": "10/05/1990",
        "nome_mae": "Mae Teste",
    })
    print("2) POST /identificacao-paciente/ ->", r_checkin.status_code, r_checkin.get("Location"))
    print("   sessao apos checkin ainda tem staff_logged_in?", c2.session.get("staff_logged_in"))
    print("   sessao apos checkin tem paciente_id?", c2.session.get("paciente_id") is not None)

    # 3) get_painel_chamada_context com dados reais nao deve quebrar (timezone fix)
    ctx = get_painel_chamada_context(use_real_data=True)
    print("3) get_painel_chamada_context(use_real_data=True) ->", ctx["current_date"], ctx["current_time"])

finally:
    teardown_test_environment()
    runner.teardown_databases(old_config)
    print("\nOK - suite finalizada")

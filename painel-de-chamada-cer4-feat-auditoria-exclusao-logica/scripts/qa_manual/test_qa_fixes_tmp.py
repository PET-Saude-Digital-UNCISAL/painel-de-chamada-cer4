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
    from core.services import registrar_checkin

    staff = UsuarioSistema(nome_completo="Recep", email_institucional="r@t.com", cpf="11122233396", nivel_acesso="super_admin")
    staff.set_senha("123456")
    staff.save()

    paciente = Paciente.objects.create(
        nome_completo="Teste Idempotente",
        cpf="390.533.447-05",
        data_nascimento=date(1990, 5, 10),
        nome_mae="Mae Teste",
        paciente_ativo=True,
    )
    Agendamento.objects.create(
        paciente=paciente,
        data_agendamento=date.today(),
        status=Agendamento.Status.AGENDADO,
    )

    # 1) Primeiro check-in cria um encaixe novo
    e1 = registrar_checkin(paciente, paciente.data_nascimento, paciente.nome_mae)
    print("1) primeiro checkin -> senha:", e1.senha, "| total encaixes hoje:", EncaixePaciente.objects.filter(data_atendimento=date.today()).count())

    # 2) Segundo check-in (mesmo paciente, mesmo dia) NAO deve criar outro
    e2 = registrar_checkin(paciente, paciente.data_nascimento, paciente.nome_mae)
    print("2) segundo checkin -> mesma senha?", e1.pk == e2.pk, "| senha:", e2.senha, "| total encaixes hoje:", EncaixePaciente.objects.filter(data_atendimento=date.today()).count())

    # 3) Fluxo completo chamar -> iniciar -> concluir via views (senha/id based)
    c = Client()
    session = c.session
    session["staff_logged_in"] = True
    session["staff_usuario_id"] = staff.pk
    session.save()

    r_chamar = c.post("/sistema/chamar/", {"senha": e1.senha, "sala": "Sala 1"})
    print("3) POST /sistema/chamar/ ->", r_chamar.status_code, r_chamar.json())

    e1.refresh_from_db()
    print("   status apos chamar:", e1.status)

    r_iniciar = c.post(f"/encaixe/{e1.pk}/iniciar-atendimento/")
    print("4) POST /encaixe/<id>/iniciar-atendimento/ ->", r_iniciar.status_code, r_iniciar.json())
    e1.refresh_from_db()
    print("   status apos iniciar:", e1.status)

    r_concluir = c.post(f"/encaixe/{e1.pk}/concluir-atendimento/")
    print("5) POST /encaixe/<id>/concluir-atendimento/ ->", r_concluir.status_code, r_concluir.json())
    e1.refresh_from_db()
    print("   status apos concluir:", e1.status, "| concluido_em preenchido?", e1.concluido_em is not None)

    # 4) Testa marcar_ausente em outro encaixe (para nao interferir no concluido)
    paciente2 = Paciente.objects.create(
        nome_completo="Teste Ausente",
        cpf="529.982.247-25",
        data_nascimento=date(1985, 1, 1),
        nome_mae="Mae Ausente",
        paciente_ativo=True,
    )
    Agendamento.objects.create(paciente=paciente2, data_agendamento=date.today(), status=Agendamento.Status.AGENDADO)
    e3 = registrar_checkin(paciente2, paciente2.data_nascimento, paciente2.nome_mae)
    c.post("/sistema/chamar/", {"senha": e3.senha, "sala": "Sala 2"})
    r_ausente = c.post("/sistema/marcar-ausente/", {"senha": e3.senha})
    print("6) POST /sistema/marcar-ausente/ ->", r_ausente.status_code, r_ausente.json())
    e3.refresh_from_db()
    print("   status apos ausente:", e3.status)

    # 5) Renderiza a tela "Atendimentos do Dia" pra garantir que o template nao quebrou
    r_tela = c.get("/telas/auditoria-percurso-seguranca/?interno=1")
    print("7) GET /telas/auditoria-percurso-seguranca/?interno=1 ->", r_tela.status_code)
    body = r_tela.content.decode()
    print("   contem 'Iniciar Atendimento'?", "Iniciar Atendimento" in body)
    print("   contem 'Concluir Atendimento'?", "Concluir Atendimento" in body)
    print("   contem 'ausente-action'?", "ausente-action" in body)
    print("   contem WS de sincronizacao?", "ws/painel-chamada/" in body)

    # 6) Tela mobile "Paciente Chamado" sem simular chamada
    r_pc = c.get(f"/paciente-chamado/")
    print("8) GET /paciente-chamado/ ->", r_pc.status_code)
    print("   ainda tem 'Simular chamada'?", "Simular chamada" in r_pc.content.decode())

finally:
    teardown_test_environment()
    runner.teardown_databases(old_config)
    print("\nOK - suite finalizada")

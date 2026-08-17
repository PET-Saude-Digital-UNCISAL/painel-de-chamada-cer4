import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.test_settings")
django.setup()

from django.test.runner import DiscoverRunner
from django.test.utils import setup_test_environment, teardown_test_environment
from django.test import Client
import json

runner = DiscoverRunner()
old_config = runner.setup_databases()
setup_test_environment()

try:
    from datetime import date
    from core.models import EncaixePaciente, UsuarioSistema
    from apps.core_domain.models import PesquisaSatisfacao

    staff = UsuarioSistema(nome_completo="Recep", email_institucional="r@t.com", cpf="11122233396", nivel_acesso="recepcionista")
    staff.set_senha("123456")
    staff.save()

    encaixe = EncaixePaciente.objects.create(
        nome_completo="Paciente Teste",
        cpf="390.533.447-05",
        senha="A001",
        data_atendimento=date.today(),
        status=EncaixePaciente.Status.CONCLUIDO,
        posicao_fila=1,
    )

    c = Client()

    # Registro ANTIGO (formato legado, só nota geral) - simula dado pré-existente
    PesquisaSatisfacao.objects.create(paciente_cpf="00000000000", nota=3, paciente_nome="Legado")

    # Envio via API nova (por categoria)
    r = c.post(
        "/api/v1/pesquisa-satisfacao/",
        data=json.dumps({
            "cpf": "390.533.447-05",
            "nota_atendimento": 5,
            "nota_espera": 3,
            "nota_instalacao": 4,
            "nota_profissional": 5,
            "nota_clareza": 4,
            "comentario": "Muito bom",
        }),
        content_type="application/json",
    )
    print("POST pesquisa ->", r.status_code, r.json())

    p = PesquisaSatisfacao.objects.get(paciente_cpf="390.533.447-05")
    print("nota geral calculada:", p.nota, "(esperado 4, media de 5+3+4+5+4=21/5=4.2 arredondado)")
    print("categorias salvas:", p.nota_atendimento, p.nota_espera, p.nota_instalacao, p.nota_profissional, p.nota_clareza)

    # Tenta enviar de novo pro mesmo encaixe -> deve bloquear duplicidade
    r2 = c.post(
        "/api/v1/pesquisa-satisfacao/",
        data=json.dumps({
            "cpf": "390.533.447-05", "nota_atendimento": 1, "nota_espera": 1,
            "nota_instalacao": 1, "nota_profissional": 1, "nota_clareza": 1,
        }),
        content_type="application/json",
    )
    print("\nPOST duplicado ->", r2.status_code, r2.json())

    # Checa a API de métricas (staff logado)
    session = c.session
    session["staff_usuario_id"] = staff.pk
    session.save()
    r3 = c.get("/api/dashboard/qualidade-metrics/?days=30")
    data = r3.json()
    print("\nGET metrics -> status", r3.status_code)
    for attr in data["atributos"]:
        print(" ", attr)
    print("total:", data["total"], "| media:", data["media"])

finally:
    teardown_test_environment()
    runner.teardown_databases(old_config)
    print("\nOK - suite finalizada")

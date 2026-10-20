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
    from core.models import UsuarioSistema

    recep = UsuarioSistema(nome_completo="Recep Teste", email_institucional="recep@t.com", cpf="11122233396", nivel_acesso="recepcionista")
    recep.set_senha("123456")
    recep.save()

    admin = UsuarioSistema(nome_completo="Admin Teste", email_institucional="admin@t.com", cpf="99988877714", nivel_acesso="super_admin")
    admin.set_senha("123456")
    admin.save()

    c = Client()

    # login as recepcionista first
    r = c.post("/login/", {"cpf": "111.222.333-96", "senha": "123456"})
    print("Login recepcionista ->", r.status_code, r.get("Location"))

    r = c.get("/meu-perfil/?interno=1")
    body = r.content.decode()
    print("Perfil apos login recep contem 'Recep Teste':", "Recep Teste" in body)

    # Now, WITHOUT logging out, try to log in as admin (this is the reported bug scenario)
    r = c.post("/login/", {"cpf": "999.888.777-14", "senha": "123456"})
    print("\nLogin admin SEM logout explicito ->", r.status_code, r.get("Location"), "(esperado 302 para sistema-interno)")

    r = c.get("/meu-perfil/?interno=1")
    body = r.content.decode()
    print("Perfil apos 2o login contem 'Admin Teste':", "Admin Teste" in body, "| ainda contem 'Recep Teste':", "Recep Teste" in body)

    # Now test wrong credentials -> should show error message
    c2 = Client()
    r = c2.post("/login/", {"cpf": "999.888.777-14", "senha": "senhaerrada"})
    print("\nLogin com senha errada -> status", r.status_code)
    body = r.content.decode()
    print("Contem 'CPF ou senha inválidos':", "CPF ou senha inválidos" in body)
    print("Contem classe mensagem-erro:", "mensagem-erro" in body)

finally:
    teardown_test_environment()
    runner.teardown_databases(old_config)
    print("\nOK - suite finalizada")

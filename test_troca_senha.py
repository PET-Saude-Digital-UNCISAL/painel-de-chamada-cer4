import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.test_settings")
django.setup()

from django.test.utils import setup_test_environment, teardown_test_environment
from django.test.runner import DiscoverRunner

runner = DiscoverRunner()
old_config = runner.setup_databases()

from django.test import Client
from core.models import UsuarioSistema

client = Client()

usuario = UsuarioSistema.objects.create(
    nome_completo="Recepcionista Teste",
    email_institucional="recepcionista.teste@cer4.local",
    cpf="11122233396",
    nivel_acesso=UsuarioSistema.NivelAcesso.RECEPCIONISTA,
    cargo="Recepcionista",
    departamento="Recepção",
)
usuario.set_senha("123456")
usuario.save()

session = client.session
session["staff_logged_in"] = True
session["staff_usuario_id"] = usuario.pk
session.save()

# 1) senha atual errada -> deve falhar e manter senha antiga
resp = client.post("/meu-perfil/?interno=1", {
    "action": "trocar_senha",
    "senha_atual": "senha-errada",
    "nova_senha": "novaSenha123",
    "confirmar_nova_senha": "novaSenha123",
})
usuario.refresh_from_db()
assert resp.status_code == 200, f"status inesperado: {resp.status_code}"
assert usuario.checar_senha("123456"), "senha não deveria ter mudado com senha atual errada"
assert b"incorreta" in resp.content.lower() or "incorreta".encode("latin-1") in resp.content, "mensagem de erro nao encontrada"
print("OK 1: senha atual incorreta é rejeitada e senha não muda")

# 2) confirmacao nao bate -> deve falhar
resp = client.post("/meu-perfil/?interno=1", {
    "action": "trocar_senha",
    "senha_atual": "123456",
    "nova_senha": "novaSenha123",
    "confirmar_nova_senha": "outraSenha456",
})
usuario.refresh_from_db()
assert usuario.checar_senha("123456"), "senha não deveria ter mudado com confirmação divergente"
print("OK 2: confirmação divergente é rejeitada")

# 3) nova senha igual a atual -> deve falhar
resp = client.post("/meu-perfil/?interno=1", {
    "action": "trocar_senha",
    "senha_atual": "123456",
    "nova_senha": "123456",
    "confirmar_nova_senha": "123456",
})
usuario.refresh_from_db()
assert usuario.checar_senha("123456")
print("OK 3: nova senha igual à atual é rejeitada")

# 4) fluxo correto -> deve mudar a senha
resp = client.post("/meu-perfil/?interno=1", {
    "action": "trocar_senha",
    "senha_atual": "123456",
    "nova_senha": "novaSenha123",
    "confirmar_nova_senha": "novaSenha123",
})
usuario.refresh_from_db()
assert resp.status_code == 200
assert usuario.checar_senha("novaSenha123"), "senha deveria ter sido alterada"
assert not usuario.checar_senha("123456"), "senha antiga não deveria mais funcionar"
print("OK 4: troca de senha bem-sucedida com dados válidos")

# 5) o resto do perfil (nome/email) continua funcionando como antes
resp = client.post("/meu-perfil/?interno=1", {
    "nome_completo": "Recepcionista Teste Editado",
    "email_institucional": "novo.email@cer4.local",
})
usuario.refresh_from_db()
assert usuario.nome_completo == "Recepcionista Teste Editado", usuario.nome_completo
print("OK 5: atualização normal de perfil (nome/email) continua funcionando")

runner.teardown_databases(old_config)
print("\nTODOS OS TESTES PASSARAM")

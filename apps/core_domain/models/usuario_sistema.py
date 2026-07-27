from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class UsuarioSistema(models.Model):
    class NivelAcesso(models.TextChoices):
        RECEPCIONISTA = "recepcionista", "Recepcionista"
        COORDENACAO = "coordenacao", "Coordenação"
        SUPER_ADMIN = "super_admin", "Super Admin"

    nome_completo = models.CharField(max_length=150)
    email_institucional = models.EmailField(unique=True)
    cpf = models.CharField(max_length=11, unique=True)
    senha_hash = models.CharField(max_length=128, default="")
    nivel_acesso = models.CharField(max_length=20, choices=NivelAcesso.choices)
    cargo = models.CharField(max_length=100, default="")
    departamento = models.CharField(max_length=100, default="")
    foto_perfil = models.ImageField(upload_to='perfis/', null=True, blank=True)
    usuario_ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        ordering = ("nome_completo",)
        verbose_name = "usuário do sistema"
        verbose_name_plural = "usuários do sistema"

    @property
    def iniciais(self):
        partes = self.nome_completo.split()
        return "".join(parte[0] for parte in partes[:2]).upper()

    def set_senha(self, senha_plana: str) -> None:
        self.senha_hash = make_password(senha_plana)

    def checar_senha(self, senha_plana: str) -> bool:
        return check_password(senha_plana, self.senha_hash)

    def __str__(self):
        return self.nome_completo

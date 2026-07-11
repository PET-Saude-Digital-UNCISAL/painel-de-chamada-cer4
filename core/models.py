from django.db import models


class UsuarioSistema(models.Model):
    class NivelAcesso(models.TextChoices):
        RECEPCIONISTA = "recepcionista", "Recepcionista"
        COORDENACAO = "coordenacao", "Coordenação"
        SUPER_ADMIN = "super_admin", "Super Admin"

    nome_completo = models.CharField(max_length=150)
    email_institucional = models.EmailField(unique=True)
    cpf = models.CharField(max_length=14, unique=True)
    nivel_acesso = models.CharField(max_length=20, choices=NivelAcesso.choices)
    usuario_ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nome_completo",)
        verbose_name = "usuário do sistema"
        verbose_name_plural = "usuários do sistema"

    @property
    def iniciais(self):
        partes = self.nome_completo.split()
        return "".join(parte[0] for parte in partes[:2]).upper()

    def __str__(self):
        return self.nome_completo

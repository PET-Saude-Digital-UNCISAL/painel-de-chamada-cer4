from django.db import models

from apps.core_domain.models.usuario_sistema import UsuarioSistema


class NivelAcessoPermissao(models.Model):
    """Persiste quais permissões cada nível de acesso possui.

    Substitui a simulação client-side que existia em configuracoes.html
    (objeto `profiles` hardcoded em JS, sem persistência real).
    """

    class Permissao(models.TextChoices):
        CHECKIN = "checkin", "Check-in e Atendimento"
        PRONTUARIO = "prontuario", "Edição de Prontuário"
        USUARIOS = "usuarios", "Gestão de Usuários"
        AUDITORIA = "auditoria", "Auditoria de Logs"
        DELETAR = "deletar", "Deletar Registros"

    nivel_acesso = models.CharField(max_length=20, choices=UsuarioSistema.NivelAcesso.choices)
    permissao = models.CharField(max_length=20, choices=Permissao.choices)
    ativo = models.BooleanField(default=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        unique_together = ("nivel_acesso", "permissao")
        verbose_name = "permissão de nível de acesso"
        verbose_name_plural = "permissões de nível de acesso"
        ordering = ("nivel_acesso", "permissao")

    def __str__(self):
        return f"{self.get_nivel_acesso_display()} — {self.get_permissao_display()}"

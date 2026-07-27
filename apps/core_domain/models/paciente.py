from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class Paciente(models.Model):
    nome_completo = models.CharField(max_length=150)
    nome_mae = models.CharField(max_length=150, blank=True, default="")
    cpf = models.CharField(max_length=14, unique=True)
    data_nascimento = models.DateField(null=True, blank=True)
    email = models.EmailField(blank=True)
    senha_hash = models.CharField(max_length=128)
    paciente_ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        ordering = ("nome_completo",)
        verbose_name = "paciente"
        verbose_name_plural = "pacientes"

    def set_senha(self, senha_plana: str) -> None:
        self.senha_hash = make_password(senha_plana)

    def checar_senha(self, senha_plana: str) -> bool:
        return check_password(senha_plana, self.senha_hash)

    def __str__(self):
        return self.nome_completo

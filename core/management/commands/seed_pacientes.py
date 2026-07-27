from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Agendamento, Paciente


PACIENTES = [
    {
        "nome_completo": "Ana Clara Silva",
        "cpf": "12345678901",
        "data_nascimento": "1988-03-15",
        "nome_mae": "Maria das Graças Silva",
        "atendimento": "consulta",
    },
    {
        "nome_completo": "Bruno Henrique Oliveira",
        "cpf": "23456789012",
        "data_nascimento": "1995-07-22",
        "nome_mae": "Luciana Oliveira",
        "atendimento": "exame_auditivo",
    },
    {
        "nome_completo": "Carla Beatriz Souza",
        "cpf": "34567890123",
        "data_nascimento": "1982-11-05",
        "nome_mae": "Teresa Cristina Souza",
        "atendimento": "terapia",
    },
    {
        "nome_completo": "Diego Ramos Santos",
        "cpf": "45678901234",
        "data_nascimento": "2001-01-30",
        "nome_mae": "Patricia Santos Ramos",
        "atendimento": "exame_auditivo",
    },
    {
        "nome_completo": "Eduarda Lima Ferreira",
        "cpf": "56789012345",
        "data_nascimento": "1975-09-12",
        "nome_mae": "Francisca Lima",
        "atendimento": "consulta",
    },
    {
        "nome_completo": "Felipe Augusto Rocha",
        "cpf": "67890123456",
        "data_nascimento": "1990-04-18",
        "nome_mae": "Helena Rocha",
        "atendimento": "terapia",
    },
    {
        "nome_completo": "Gabriela Martins Costa",
        "cpf": "78901234567",
        "data_nascimento": "1998-12-25",
        "nome_mae": "Regina Célia Martins",
        "atendimento": "exame_auditivo",
    },
    {
        "nome_completo": "Heitor Alves Pereira",
        "cpf": "89012345678",
        "data_nascimento": "1963-06-08",
        "nome_mae": "Raimunda Alves Pereira",
        "atendimento": "consulta",
    },
    {
        "nome_completo": "Isabela Fernandes Melo",
        "cpf": "90123456789",
        "data_nascimento": "2005-02-03",
        "nome_mae": "Claudia Fernandes",
        "atendimento": "terapia",
    },
    {
        "nome_completo": "João Pedro Barbosa",
        "cpf": "01234567890",
        "data_nascimento": "1989-10-14",
        "nome_mae": "Sônia Maria Barbosa",
        "atendimento": "exame_auditivo",
    },
]


class Command(BaseCommand):
    help = "Popula o banco com 10 pacientes fictícios e agendamentos para testes."

    def handle(self, *args, **options):
        hoje = timezone.localdate()
        criados = 0
        ignorados = 0
        agendamentos_criados = 0
        agendamentos_ignorados = 0

        for data in PACIENTES:
            cpf = data["cpf"]
            nome = data["nome_completo"]

            paciente, foi_criado = Paciente.objects.get_or_create(
                cpf=cpf,
                defaults={
                    "nome_completo": nome,
                    "data_nascimento": data["data_nascimento"],
                },
            )
            if foi_criado:
                paciente.set_senha("123456")
                paciente.save(update_fields=["senha_hash"])
                criados += 1
                self.stdout.write(f"  Criado Paciente: {nome} ({cpf})")
            else:
                ignorados += 1
                self.stdout.write(f"  Paciente já existe: {nome} ({cpf}) — pulando")

            if Agendamento.objects.filter(
                paciente=paciente, data_agendamento=hoje
            ).exists():
                agendamentos_ignorados += 1
                self.stdout.write(
                    f"  Agendamento já existe hoje para {nome} — pulando"
                )
                continue

            Agendamento.objects.create(
                paciente=paciente,
                data_agendamento=hoje,
                hora_agendamento=None,
                tipo_atendimento=data["atendimento"],
            )
            agendamentos_criados += 1
            self.stdout.write(f"  Agendamento criado: {nome} -> {data['atendimento']}")

        self.stdout.write(self.style.SUCCESS(
            f"Resumo: {criados} pacientes criados, {ignorados} já existiam; "
            f"{agendamentos_criados} agendamentos criados, {agendamentos_ignorados} já existiam hoje."
        ))

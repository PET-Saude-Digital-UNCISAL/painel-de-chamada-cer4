from django.core.management.base import BaseCommand

from core.models import UsuarioSistema


USUARIOS = [
    {
        "nome_completo": "Recepcionista Teste",
        "email_institucional": "recepcionista.teste@sistema.com",
        "cpf": "11122233396",
        "nivel_acesso": UsuarioSistema.NivelAcesso.RECEPCIONISTA,
        "cargo": "Recepcionista",
        "departamento": "Atendimento",
        "senha": "123456",
    },
    {
        "nome_completo": "Gerente Teste",
        "email_institucional": "gerente.teste@sistema.com",
        "cpf": "55566677720",
        "nivel_acesso": UsuarioSistema.NivelAcesso.COORDENACAO,
        "cargo": "Gerente",
        "departamento": "Gestão",
        "senha": "123456",
    },
    {
        "nome_completo": "Admin Teste",
        "email_institucional": "admin.teste@sistema.com",
        "cpf": "99988877714",
        "nivel_acesso": UsuarioSistema.NivelAcesso.SUPER_ADMIN,
        "cargo": "Super Administrador",
        "departamento": "Tecnologia",
        "senha": "123456",
    },
]


class Command(BaseCommand):
    help = "Popula o banco com 3 usuários do sistema para testes."

    def handle(self, *args, **options):
        criados = 0
        ignorados = 0

        for data in USUARIOS:
            usuario, criado = UsuarioSistema.objects.get_or_create(
                cpf=data["cpf"],
                defaults={
                    "nome_completo": data["nome_completo"],
                    "email_institucional": data["email_institucional"],
                    "nivel_acesso": data["nivel_acesso"],
                    "cargo": data["cargo"],
                    "departamento": data["departamento"],
                },
            )
            usuario.set_senha(data["senha"])
            usuario.save(update_fields=["senha_hash"])
            if criado:
                criados += 1
                self.stdout.write(
                    f"  Criado: {data['nome_completo']} ({data['nivel_acesso']})"
                )
            else:
                ignorados += 1
                self.stdout.write(
                    f"  Já existe: {data['nome_completo']} — pulando"
                )

        self.stdout.write(self.style.SUCCESS(
            f"\nResumo: {criados} usuários criados, {ignorados} já existiam."
        ))

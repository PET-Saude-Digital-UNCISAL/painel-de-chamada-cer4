"""Comando de linha de comando pra rodar a sincronizacao de
agendamentos manualmente (uso tipico: agendado via cron/tarefa
programada no servidor). Equivalente ao clique em
sincronizar_agendamentos_view, mas sem depender de alguem estar logado
na tela."""

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.core_domain.auditoria import usando_ator
from core.integrador import IntegradorHttp, sincronizar_agendamentos
from core.models import UsuarioSistema


class Command(BaseCommand):
    help = "Sincroniza agendamentos do sistema externo (Dias Conectado)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--data",
            type=str,
            help="Data alvo no formato YYYY-MM-DD (padrão: hoje)",
        )
        parser.add_argument(
            "--base-url",
            type=str,
            help="URL base da API externa (sobrescreve settings.INTEGRADOR_BASE_URL)",
        )
        parser.add_argument(
            "--token",
            type=str,
            help="Token de autenticação (sobrescreve settings.INTEGRADOR_TOKEN)",
        )
        parser.add_argument(
            "--ator",
            type=str,
            help=(
                "E-mail institucional do UsuarioSistema registrado como autor "
                "dos agendamentos (padrão: nenhum, campos de auditoria vazios)"
            ),
        )

    def handle(self, *args, **options):
        from django.conf import settings

        data_alvo = date.fromisoformat(options["data"]) if options["data"] else None
        base_url = options.get("base_url") or getattr(settings, "INTEGRADOR_BASE_URL", "")
        token = options.get("token") or getattr(settings, "INTEGRADOR_TOKEN", "")

        if not base_url:
            self.stderr.write(self.style.ERROR(
                "INTEGRADOR_BASE_URL não configurado. Defina em settings.py ou use --base-url."
            ))
            return

        ator = None
        if options.get("ator"):
            ator = UsuarioSistema.objects.filter(
                email_institucional=options["ator"], usuario_ativo=True
            ).first()
            if not ator:
                raise CommandError(
                    f"Nenhum UsuarioSistema ativo com o e-mail {options['ator']}."
                )

        integrador = IntegradorHttp(base_url=base_url, token=token)
        # Rodando por cron nao ha sessao: sem --ator, os campos "por" dos
        # pacientes/agendamentos criados ou atualizados ficam vazios.
        with usando_ator(ator):
            resultado = sincronizar_agendamentos(data_alvo=data_alvo, integrador=integrador)

        if resultado.get("ok"):
            self.stdout.write(self.style.SUCCESS(
                f"Sincronização concluída para {resultado['data']}: "
                f"{resultado['criados']} criados, "
                f"{resultado['atualizados']} atualizados, "
                f"{resultado['total_recebidos']} recebidos"
            ))
        else:
            self.stderr.write(self.style.ERROR(f"Erro: {resultado.get('erro', 'desconhecido')}"))

        if resultado.get("erros"):
            self.stderr.write(self.style.WARNING("Erros individuais:"))
            for e in resultado["erros"]:
                self.stderr.write(f"  - {e}")

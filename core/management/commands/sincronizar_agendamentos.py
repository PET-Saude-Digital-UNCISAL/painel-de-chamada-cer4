from datetime import date

from django.core.management.base import BaseCommand

from core.integrador import IntegradorHttp, sincronizar_agendamentos


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

        integrador = IntegradorHttp(base_url=base_url, token=token)
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

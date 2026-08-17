from datetime import datetime

from django.utils import timezone


class SystemClock:
    @staticmethod
    def now() -> datetime:
        # timezone.now() sempre retorna UTC quando USE_TZ=True — precisa
        # converter para o fuso configurado (America/Maceio) antes de usar
        # em exibição (relógio, data por extenso) ou em regras de negócio
        # que dependem do dia local (ex.: "hoje").
        return timezone.localtime(timezone.now())

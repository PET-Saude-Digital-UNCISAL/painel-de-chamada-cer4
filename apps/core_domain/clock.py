from datetime import datetime

from django.utils import timezone


class SystemClock:
    @staticmethod
    def now() -> datetime:
        return timezone.now()

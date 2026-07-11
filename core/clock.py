from datetime import datetime

from django.utils import timezone


class SystemClock:
    """Clock wrapper used by business rules and services.

    Centralizing time access makes tests deterministic and avoids direct
    calls to datetime.now()/timezone.now() across the codebase.
    """

    @staticmethod
    def now() -> datetime:
        """Return current timezone-aware datetime."""
        return timezone.now()

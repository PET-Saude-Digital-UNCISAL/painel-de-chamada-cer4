from datetime import datetime

from core.clock import SystemClock


def is_deadline_expired(deadline_at: datetime, clock=SystemClock) -> bool:
    """Example business rule: returns True when deadline has passed."""
    return clock.now() > deadline_at


def can_run_reception_workflow(clock=SystemClock) -> bool:
    """Example business rule: workflow runs only on weekdays.

    weekday(): Monday=0 ... Sunday=6
    """
    current_weekday = clock.now().weekday()
    return current_weekday < 5

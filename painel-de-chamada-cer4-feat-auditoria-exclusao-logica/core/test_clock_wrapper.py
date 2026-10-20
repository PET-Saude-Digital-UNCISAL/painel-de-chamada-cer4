from datetime import datetime
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from core.business_rules import can_run_reception_workflow, is_deadline_expired
from core.services import get_auditoria_percurso_context


class ClockWrapperTests(SimpleTestCase):
    @patch("core.business_rules.SystemClock.now")
    def test_reception_workflow_blocked_on_weekend(self, mock_now):
        # Saturday (weekend) should block the workflow.
        mock_now.return_value = timezone.make_aware(datetime(2026, 7, 11, 9, 0, 0))

        self.assertFalse(can_run_reception_workflow())

    @patch("core.business_rules.SystemClock.now")
    def test_deadline_expired_uses_clock_wrapper(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime(2026, 7, 7, 10, 0, 0))
        deadline = timezone.make_aware(datetime(2026, 7, 7, 9, 0, 0))

        self.assertTrue(is_deadline_expired(deadline))

    @patch("core.services.SystemClock.now")
    def test_audit_context_uses_clock_wrapper(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime(2026, 7, 11, 18, 48, 0))

        context = get_auditoria_percurso_context()

        self.assertEqual(context["current_time"], "18:48")
        self.assertEqual(context["current_date"], "11 de julho de 2026")

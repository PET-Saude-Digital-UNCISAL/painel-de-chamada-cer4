from django.test import SimpleTestCase, override_settings

from core.dev_builders import build_fake_screen_list, build_mocked_screen_payload
from core.services import get_screen_context, list_team_screens


class IsolatedScreenSetupTests(SimpleTestCase):
	def test_direct_screen_route_works(self):
		response = self.client.get("/telas/pacientes-listagem/")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Tela de Pacientes")

	@override_settings(DEBUG=True)
	def test_debug_hidden_route_enabled(self):
		response = self.client.get("/__dev__/mocks/")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Preview de mocks")

	@override_settings(DEBUG=False)
	def test_debug_hidden_route_disabled(self):
		response = self.client.get("/__dev__/mocks/")
		self.assertEqual(response.status_code, 404)

	def test_service_returns_none_for_unknown_screen(self):
		context = get_screen_context("nao-existe")
		self.assertIsNone(context)

	def test_builder_generates_payload_without_db(self):
		payload = build_mocked_screen_payload("dev2")
		self.assertEqual(payload["screen_slug"], "dev2")
		self.assertEqual(payload["status"], "mock-data")

	def test_list_team_screens_has_expected_size(self):
		screens = list_team_screens()
		self.assertEqual(len(screens), 6) # 1 grupo + 5 telas individuais

	def test_fake_screen_list_builder(self):
		cards = build_fake_screen_list(quantity=3)
		self.assertEqual(len(cards), 3)
		self.assertEqual(cards[0]["slug"], "dev1")

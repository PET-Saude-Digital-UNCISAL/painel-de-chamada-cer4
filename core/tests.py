from django.test import SimpleTestCase, override_settings

from core.dev_builders import build_fake_screen_list, build_mocked_screen_payload
from core.services import get_screen_context, list_team_screens


class IsolatedScreenSetupTests(SimpleTestCase):
	def test_direct_screen_route_works(self):
		response = self.client.get("/telas/pacientes-listagem/")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Listagem de Pacientes")

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
		self.assertEqual(len(screens), 8) # 1 grupo + 7 telas individuais
		self.assertIn(
			{
				"slug": "dashboard-monitoramento",
				"title": "Dashboard de Monitoramento do Fluxo",
				"owner": "Remany",
				"status": "em desenvolvimento",
				"path": "/dashboard-monitoramento/",
			},
			screens,
		)

	def test_patient_group_uses_completed_monaliza_screens(self):
		patient_group = list_team_screens()[0]
		self.assertEqual(
			patient_group["screens"],
			[
				{
					"slug": "agendamento-nao-encontrado",
					"title": "Tela de Agendamento Não Encontrado",
					"owner": "Monaliza",
					"status": "Concluído",
					"path": "/agendamento-nao-encontrado/",
				},
				{
					"slug": "perdeu-chamada",
					"title": "Tela de Senha Perdida",
					"owner": "Monaliza",
					"status": "Concluído",
					"path": "/perdeu-chamada/",
				},
			],
		)

	def test_development_panel_links_to_requested_screens(self):
		response = self.client.get("/")
		self.assertContains(response, 'href="/agendamento-nao-encontrado/"')
		self.assertContains(response, 'href="/perdeu-chamada/"')
		self.assertContains(response, 'href="/dashboard-monitoramento/"')

		for path in (
			"/agendamento-nao-encontrado/",
			"/perdeu-chamada/",
			"/dashboard-monitoramento/",
		):
			with self.subTest(path=path):
				self.assertEqual(self.client.get(path).status_code, 200)

	def test_auditoria_route_works(self):
		response = self.client.get("/telas/auditoria-percurso-seguranca/")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Auditoria de Percurso e Segurança")

	def test_auditoria_search_filter(self):
		response = self.client.get("/telas/auditoria-percurso-seguranca/?q=ricardo")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Ricardo Mendes Junior")
		self.assertNotContains(response, "Benedito Silveira Santos")

	def test_auditoria_date_filter(self):
		response = self.client.get("/telas/auditoria-percurso-seguranca/?data=2026-07-06")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Maria Clara Ferreira")
		self.assertNotContains(response, "Ricardo Mendes Junior")

	def test_auditoria_date_range_filter(self):
		response = self.client.get(
			"/telas/auditoria-percurso-seguranca/?data_inicio=2026-07-06&data_fim=2026-07-06"
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Maria Clara Ferreira")
		self.assertNotContains(response, "Ricardo Mendes Junior")

	def test_auditoria_date_range_filter_accepts_inverted_dates(self):
		response = self.client.get(
			"/telas/auditoria-percurso-seguranca/?data_inicio=2026-07-07&data_fim=2026-07-06"
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Maria Clara Ferreira")
		self.assertContains(response, "Ricardo Mendes Junior")

	def test_auditoria_date_filter_modal_is_rendered(self):
		response = self.client.get("/telas/auditoria-percurso-seguranca/")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "date-filter-modal")
		self.assertContains(response, "Aplicar Filtro")

	def test_auditoria_reorder_modal_is_rendered(self):
		response = self.client.get("/telas/auditoria-percurso-seguranca/")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Confirmar Reordenação")
		self.assertContains(response, "reorder-action")
		self.assertContains(response, "reorder-position-select")

	def test_auditoria_export_csv(self):
		response = self.client.get("/telas/auditoria-percurso-seguranca/?export=csv")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response["Content-Type"], "text/csv")
		self.assertIn("attachment; filename=\"auditoria_percurso_seguranca.csv\"", response["Content-Disposition"])
		self.assertIn("Ficha", response.content.decode("utf-8"))

	def test_fake_screen_list_builder(self):
		cards = build_fake_screen_list(quantity=3)
		self.assertEqual(len(cards), 3)
		self.assertEqual(cards[0]["slug"], "dev1")

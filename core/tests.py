from datetime import date

from django.test import TestCase, override_settings
from django.urls import resolve, reverse

from core.dev_builders import build_fake_screen_list, build_mocked_screen_payload
from core.services import (
	get_bloqueio_direcionamento_context,
	get_checkin_assistido_context,
	get_dashboard_monitoramento_context,
	get_painel_chamada_context,
	get_paciente_chamado_context,
	get_screen_context,
	list_patient_screens,
	list_team_screens,
)
from core.models import Paciente, UsuarioSistema, Agendamento, EncaixePaciente


class IsolatedScreenSetupTests(TestCase):
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

	def test_patient_navigation_has_required_screens_in_expected_order(self):
		screens = list_patient_screens()
		expected = [
			("identificacao-paciente", "Identificação do Paciente", "Remany", "identificacao-paciente"),
			("checkin-concluido", "Check-in Concluído", "Remany", "checkin-concluido"),
			("acompanhamento-atendimento", "Acompanhamento de Atendimento", "Remany", "acompanhamento-atendimento"),
			("paciente-chamado", "Paciente Chamado", "Remany", "paciente-chamado"),
			("checkin-assistido", "Check-in Assistido", "Remany", "checkin-assistido"),
			("bloqueio-direcionamento", "Bloqueio e Direcionamento", "Remany", "bloqueio-direcionamento"),
			("pesquisa-satisfacao", "Pesquisa de satisfação", "Monaliza", "pesquisa_satisfacao"),
			("agendamento-nao-encontrado", "Agendamento não encontrado", "Monaliza", "agendamento_nao_encontrado"),
			("perdeu-chamada", "Perdeu a chamada", "Monaliza", "perdeu_chamada"),
		]
		screens_by_slug = {screen["slug"]: screen for screen in screens}
		positions = {screen["slug"]: index for index, screen in enumerate(screens)}

		for slug, title, owner, route_name in expected:
			with self.subTest(slug=slug):
				self.assertIn(slug, screens_by_slug)
				screen = screens_by_slug[slug]
				self.assertEqual(screen["title"], title)
				self.assertEqual(screen["owner"], owner)
				self.assertEqual(screen["path"], reverse(route_name))
				self.assertEqual(resolve(screen["path"]).url_name, route_name)

		for current, following in zip(expected, expected[1:]):
			self.assertLess(positions[current[0]], positions[following[0]])

		self.assertNotIn("dashboard-monitoramento", screens_by_slug)
		self.assertNotIn("painel-chamada", screens_by_slug)

	def test_patient_navigation_route_renders_canonical_cards(self):
		response = self.client.get(reverse("painel-pacientes"))

		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, "mobile/painel_pacientes.html")
		self.assertEqual(response.context["screens"], list_patient_screens())
		for screen in list_patient_screens():
			with self.subTest(slug=screen["slug"]):
				self.assertContains(response, screen["title"])
				self.assertContains(response, f'href="{screen["path"]}"')

	def test_dashboard_monitoramento_context_has_expected_mock_data(self):
		context = get_dashboard_monitoramento_context()
		self.assertEqual(context["current_time"], "09:48")
		self.assertEqual(len(context["kpis"]), 6)
		self.assertEqual(len(context["chart"]["bars"]), 7)
		self.assertEqual(len(context["encaixes"]["requests"]), 7)
		self.assertEqual(context["encaixes"]["pending_chip"], "+4 solicitações")
		self.assertTrue(all(request["mother"] for request in context["encaixes"]["requests"]))
		self.assertEqual(len(context["kanban_columns"]), 4)
		self.assertTrue(all(len(column["patients"]) == 3 for column in context["kanban_columns"]))

	def test_dashboard_monitoramento_route_renders_context_data(self):
		response = self.client.get("/dashboard-monitoramento/")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Monitoramento do Fluxo")
		self.assertContains(response, "Roberto Almeida")
		self.assertContains(response, "Mãe: Helena Almeida")
		self.assertContains(response, "Lucas Gabriel Rocha")
		self.assertContains(response, 'id="encaixes-toggle"')
		self.assertContains(response, 'aria-expanded="false"')
		self.assertContains(response, "Concluído às 08:55")

	def test_painel_chamada_context_has_expected_mock_data(self):
		context = get_painel_chamada_context()
		self.assertEqual(context["reception_name"], "RECEPÇÃO 3")
		self.assertEqual(context["current_call"]["ticket"], "A011")
		self.assertEqual(len(context["recent_calls"]), 5)
		self.assertTrue(context["qr_code_url"].startswith("data:image/png;base64,"))
		self.assertTrue(context["chamada_audio_url"].startswith("data:audio/mpeg;base64,"))

	def test_painel_chamada_route_renders_context_data(self):
		response = self.client.get("/painel-chamada/")
		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, "display/painel_chamada.html")
		self.assertContains(response, "FELIPE DA SILVA")
		self.assertContains(response, "ÚLTIMOS CHAMADOS")
		self.assertContains(response, "data:audio/mpeg;base64,")
		self.assertNotContains(response, "/static/core/painel_chamada/")

	def test_paciente_chamado_context_has_expected_mock_data(self):
		context = get_paciente_chamado_context()
		self.assertEqual(context["senha"], "A012")
		self.assertEqual(context["paciente"], "Ricardo Augusto Oliveira")
		self.assertEqual(context["sala"], "10")
		self.assertEqual(context["tipo_atendimento"], "Ambulatorial")
		self.assertEqual(context["mensagem"], "Se precisar de ajuda, procure a recepção.")
		self.assertTrue(context["public_sans_font_url"].startswith("data:font/ttf;base64,"))
		self.assertTrue(context["inter_font_url"].startswith("data:font/ttf;base64,"))

	def test_paciente_chamado_route_renders_context_data(self):
		response = self.client.get("/paciente-chamado/")
		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, "mobile/paciente_chamado.html")
		self.assertContains(response, "A012")
		self.assertContains(response, "RICARDO AUGUSTO OLIVEIRA")
		self.assertContains(response, "data:font/ttf;base64,")
		self.assertNotContains(response, "fonts.googleapis.com")
		self.assertNotContains(response, "styles.css")
		self.assertContains(response, "Simular chamada")
		self.assertContains(response, "642.857ms")
		self.assertContains(response, "9000")
		self.assertNotContains(response, "Entendi, estou a caminho")
		self.assertContains(response, "navigator.vibrate")
		self.assertContains(response, "[220, 120, 220, 120, 120]")
		self.assertContains(response, "!reduceMotion.matches")
		self.assertContains(response, "data:audio/mpeg;base64,")
		self.assertContains(response, 'role="alert"')
		self.assertContains(response, "prefers-reduced-motion")

	def test_checkin_assistido_context_has_expected_mock_data(self):
		context = get_checkin_assistido_context()
		self.assertEqual(context["title"], "Siga para a Recepção")
		self.assertIn("documento com foto", context["message"])
		self.assertEqual(len(context["footer_indicators"]), 2)
		self.assertTrue(context["inter_font_url"].startswith("data:font/ttf;base64,"))

	def test_checkin_assistido_route_and_identification_link_work(self):
		response = self.client.get("/checkin-assistido/")
		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, "mobile/checkin_assistido.html")
		self.assertContains(response, "Siga para a Recepção")
		self.assertContains(response, "Nossa equipe no balcão principal")
		self.assertContains(response, "documento com foto em mãos.")
		self.assertNotContains(response, "documentocom")
		self.assertContains(response, "data:font/ttf;base64,")
		self.assertContains(response, 'font-family: "Inter"')
		self.assertNotContains(response, 'font-family: "Public Sans"')
		self.assertContains(response, 'href="/identificacao-paciente/"')
		self.assertContains(response, "LGPD")
		self.assertContains(response, "Conexão")
		self.assertNotContains(response, "fonts.googleapis.com")

		identification_response = self.client.get("/identificacao-paciente/")
		self.assertEqual(identification_response.status_code, 200)
		self.assertContains(identification_response, 'href="/checkin-assistido/"')

	def test_bloqueio_direcionamento_context_has_expected_mock_data(self):
		context = get_bloqueio_direcionamento_context()

		self.assertEqual(context["title"], "Confirmação presencial necessária")
		self.assertEqual(context["next_step_title"], "Dirija-se à recepção")
		self.assertEqual(context["location"], "Balcão da recepção")
		self.assertEqual(context["status"], "Confirmação na recepção")
		self.assertEqual(context["review_label"], "Revisar meus dados")
		self.assertTrue(context["inter_font_url"].startswith("data:font/ttf;base64,"))
		self.assertTrue(context["cer_logo_url"].startswith("data:image/svg+xml;base64,"))

	def test_bloqueio_direcionamento_route_renders_safe_patient_guidance(self):
		path = reverse("bloqueio-direcionamento")
		match = resolve(path)
		response = self.client.get(path)

		self.assertEqual(match.url_name, "bloqueio-direcionamento")
		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, "mobile/bloqueio_direcionamento.html")
		self.assertEqual(response.context["status"], "Confirmação na recepção")
		self.assertContains(response, "Confirmação presencial necessária")
		self.assertContains(response, "Dirija-se à recepção")
		self.assertContains(response, "Balcão da recepção")
		self.assertContains(response, 'href="/identificacao-paciente/"')
		self.assertContains(response, 'role="status"')
		self.assertNotContains(response, "Entendi")
		self.assertNotContains(response, 'href="/checkin-concluido/"')
		self.assertNotContains(response, 'href="/acompanhamento-atendimento/"')
		self.assertNotContains(response, "fonts.googleapis.com")
		self.assertNotContains(response, "cdn.")
		self.assertNotContains(response, 'rel="stylesheet"')

	def test_identification_keeps_normal_flow_and_exposes_blocking_demo_trigger(self):
		response = self.client.get(reverse("identificacao-paciente"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'href="/checkin-concluido/"')
		self.assertContains(response, 'data-blocking-url="/bloqueio-direcionamento/"')
		self.assertContains(response, 'cpfDigits === "00000000000"')
		self.assertContains(response, 'screen.classList.add("is-validating")')
		self.assertContains(response, "Preciso de ajuda")

	def test_patient_flow_uses_clear_context_driven_copy(self):
		checkin_response = self.client.get(reverse("checkin-concluido"))
		self.assertEqual(checkin_response.status_code, 200)
		self.assertContains(checkin_response, "Você já está na fila de atendimento")
		self.assertContains(checkin_response, "Acompanhar fila")

		tracking_response = self.client.get(reverse("acompanhamento-atendimento"))
		self.assertEqual(tracking_response.status_code, 200)
		self.assertContains(tracking_response, "Ambulatorial")

	def test_inactive_mobile_accessibility_icons_are_not_false_controls(self):
		for route_name in [
			"identificacao-paciente",
			"checkin-concluido",
			"checkin-assistido",
			"acompanhamento-atendimento",
			"paciente-chamado",
			"bloqueio-direcionamento",
		]:
			with self.subTest(route_name=route_name):
				response = self.client.get(reverse(route_name))
				self.assertEqual(response.status_code, 200)
				self.assertNotContains(response, 'aria-label="Aumentar contraste"')
				self.assertNotContains(response, 'aria-label="Aumentar fonte"')

	def test_remany_mobile_screens_use_inter_typography(self):
		route_names = [
			"identificacao-paciente",
			"checkin-concluido",
			"checkin-assistido",
			"acompanhamento-atendimento",
			"paciente-chamado",
			"bloqueio-direcionamento",
		]

		for route_name in route_names:
			with self.subTest(route_name=route_name):
				response = self.client.get(reverse(route_name))
				self.assertEqual(response.status_code, 200)
				self.assertContains(response, 'font-family: "Inter"')
				self.assertNotContains(response, 'font-family: "Public Sans"')
				self.assertNotContains(response, "fonts.googleapis.com")

	def test_mobile_information_notices_share_the_same_visual_language(self):
		for route_name in [
			"acompanhamento-atendimento",
			"paciente-chamado",
			"bloqueio-direcionamento",
		]:
			with self.subTest(route_name=route_name):
				response = self.client.get(reverse(route_name))
				self.assertEqual(response.status_code, 200)
				self.assertContains(response, "#f2f7fd")
				self.assertContains(response, "#cfe2f8")
				self.assertContains(response, "#3b82f6")

	def test_list_team_screens_has_expected_registered_screens(self):
		screens = list_team_screens()
		self.assertIn(
			{
				"slug": "checkin-assistido",
				"title": "Check-in Assistido",
				"owner": "Remany",
				"status": "em desenvolvimento",
				"path": "/checkin-assistido/",
			},
			screens,
		)
		self.assertIn(
			{
				"slug": "acompanhamento-atendimento",
				"title": "Acompanhamento de Atendimento",
				"owner": "Remany",
				"status": "em desenvolvimento",
				"path": "/acompanhamento-atendimento/",
			},
			screens,
		)
		self.assertIn(
			{
				"slug": "paciente-chamado",
				"title": "Paciente Chamado",
				"owner": "Remany",
				"status": "em desenvolvimento",
				"path": "/paciente-chamado/",
			},
			screens,
		)
		self.assertIn(
			{
				"slug": "painel-chamada",
				"title": "Painel de Chamada da Recepção",
				"owner": "Remany",
				"status": "em desenvolvimento",
				"path": "/painel-chamada/",
			},
			screens,
		)
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
		self.assertIn(
			{
				"slug": "login",
				"title": "Tela de Login (Acesso ao Portal)",
				"owner": "Nathalia",
				"status": "Concluído",
				"path": "/login/",
			},
			screens,
		)
		self.assertIn(
			{
				"slug": "cadastro",
				"title": "Tela de Cadastro (Criar Conta do Paciente)",
				"owner": "Nathalia",
				"status": "Concluído",
				"path": "/cadastro/",
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

	def test_development_panel_has_only_the_two_product_flows(self):
		response = self.client.get("/")
		self.assertContains(response, 'href="/agendamento-nao-encontrado/"')
		self.assertContains(response, 'href="/sistema-interno/"')
		self.assertNotContains(response, 'href="/dashboard-monitoramento/"')

	def test_sistema_interno_uses_one_shell_and_fallback(self):
		ready_response = self.client.get("/sistema-interno/?tela=configuracoes")
		self.assertEqual(ready_response.status_code, 200)
		self.assertContains(ready_response, 'src="/configuracoes/?interno=1"')

	def test_drawer_connects_existing_internal_screens(self):
		for tela, embedded_path in (
			("monitoramento", "/dashboard-monitoramento/?interno=1"),
			("auditoria", "/telas/auditoria-percurso-seguranca/?interno=1"),
			("configuracoes", "/configuracoes/?interno=1"),
		):
			with self.subTest(tela=tela):
				response = self.client.get(f"/sistema-interno/?tela={tela}")
				self.assertEqual(response.status_code, 200)
				self.assertContains(response, f'src="{embedded_path}"')

	def test_embedded_internal_screens_allow_same_origin_frames(self):
		for path in (
			"/dashboard-monitoramento/",
			"/telas/auditoria-percurso-seguranca/",
			"/configuracoes/",
		):
			with self.subTest(path=path):
				response = self.client.get(path)
				self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")

	def test_configuracoes_route_and_development_card(self):
		response = self.client.get("/configuracoes/")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Controle de Níveis de Acesso")
		self.assertContains(response, 'data-profile="super-admin"')
		self.assertContains(response, "Gestão de Usuários")
		self.assertContains(response, 'id="module-users"')
		self.assertContains(response, 'id="module-audit"')
		self.assertContains(response, "Auditoria de Acesso")
		self.assertContains(response, "Integridade do Registro Ativa")
		self.assertContains(response, 'id="activity-modal"')
		self.assertContains(response, "Detalhes da Atividade")
		self.assertContains(response, "LOG BRUTO (RAW)")
		self.assertContains(response, 'id="clock-time"')
		self.assertContains(response, 'id="clock-date"')
		self.assertContains(response, 'id="user-modal"')
		self.assertContains(response, 'name="nome_completo"')
		self.assertContains(response, 'name="email_institucional"')
		self.assertContains(response, 'name="cpf"')
		self.assertContains(response, 'name="nivel_acesso"')

		self.assertIn(
			{
				"slug": "configuracoes",
				"title": "Tela de Configurações",
				"owner": "Daniely Vasconcelos",
				"status": "Concluído",
				"path": "/configuracoes/",
			},
			list_team_screens(),
		)

	def test_new_system_user_is_persisted(self):
		response = self.client.post(
			"/configuracoes/",
			{
				"nome_completo": "Maria de Teste",
				"email_institucional": "maria.teste@uncisal.com.br",
				"cpf": "123.456.789-01",
				"nivel_acesso": "coordenacao",
				"usuario_ativo": "true",
			},
		)
		self.assertRedirects(response, "/configuracoes/?modulo=usuarios&resultado=criado")
		self.assertTrue(
			UsuarioSistema.objects.filter(
				email_institucional="maria.teste@uncisal.com.br",
				cpf="123.456.789-01",
			).exists()
		)
		list_response = self.client.get("/configuracoes/?modulo=usuarios")
		self.assertContains(list_response, "Maria de Teste")
		self.assertContains(list_response, "maria.teste@uncisal.com.br")
		self.assertContains(list_response, "123.456.789-01")

	def test_system_user_update_toggle_and_delete(self):
		usuario = UsuarioSistema.objects.create(
			nome_completo="Nome Original",
			email_institucional="original@uncisal.com.br",
			cpf="111.222.333-44",
			nivel_acesso="recepcionista",
			usuario_ativo=True,
		)
		update_response = self.client.post(
			"/configuracoes/",
			{
				"action": "update",
				"usuario_id": usuario.pk,
				"nome_completo": "Nome Atualizado",
				"email_institucional": "atualizado@uncisal.com.br",
				"cpf": "111.222.333-44",
				"nivel_acesso": "coordenacao",
				"usuario_ativo": "true",
			},
		)
		self.assertRedirects(update_response, "/configuracoes/?modulo=usuarios&resultado=atualizado")
		usuario.refresh_from_db()
		self.assertEqual(usuario.nome_completo, "Nome Atualizado")
		self.assertEqual(usuario.nivel_acesso, "coordenacao")

		toggle_response = self.client.post(
			"/configuracoes/", {"action": "toggle", "usuario_id": usuario.pk}
		)
		self.assertRedirects(toggle_response, "/configuracoes/?modulo=usuarios&resultado=status")
		usuario.refresh_from_db()
		self.assertFalse(usuario.usuario_ativo)

		delete_response = self.client.post(
			"/configuracoes/", {"action": "delete", "usuario_id": usuario.pk}
		)
		self.assertRedirects(delete_response, "/configuracoes/?modulo=usuarios&resultado=excluido")
		self.assertFalse(UsuarioSistema.objects.filter(pk=usuario.pk).exists())

	def test_duplicate_system_user_is_not_persisted(self):
		UsuarioSistema.objects.create(
			nome_completo="Usuário Existente",
			email_institucional="existente@uncisal.com.br",
			cpf="987.654.321-00",
			nivel_acesso="recepcionista",
		)
		response = self.client.post(
			"/configuracoes/",
			{
				"nome_completo": "Usuário Duplicado",
				"email_institucional": "existente@uncisal.com.br",
				"cpf": "987.654.321-00",
				"nivel_acesso": "super_admin",
			},
		)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(UsuarioSistema.objects.count(), 1)
		self.assertContains(response, "Revise os campos")

	def test_auditoria_route_works(self):
		response = self.client.get("/telas/auditoria-percurso-seguranca/")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Atendimentos do Dia")

	def test_auditoria_search_filter(self):
		response = self.client.get("/telas/auditoria-percurso-seguranca/?q=Ana")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Ana Clara")

	def test_auditoria_search_filter_cpf(self):
		response = self.client.get("/telas/auditoria-percurso-seguranca/?q=01234567890")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "João Pedro")

	def test_auditoria_status_filter(self):
		response = self.client.get("/telas/auditoria-percurso-seguranca/?status=EM+VALIDAÇÃO")
		self.assertEqual(response.status_code, 200)

	def test_auditoria_date_filter_renders(self):
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

	def test_login_route_works(self):
		response = self.client.get("/login/")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Acesso ao Portal")

	def test_cadastro_route_works(self):
		response = self.client.get("/cadastro/")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Criar sua conta")

	def test_cadastro_creates_paciente_and_redirects_to_login(self):
		response = self.client.post(
			"/cadastro/",
			{
				"nome_completo": "Joao da Silva",
				"cpf": "390.533.447-05",
				"data_nascimento": "1990-05-10",
				"email": "joao@example.com",
				"senha": "SenhaForte123!",
			},
		)
		self.assertRedirects(response, "/login/")
		self.assertTrue(Paciente.objects.filter(cpf="39053344705").exists())
		paciente = Paciente.objects.get(cpf="39053344705")
		self.assertTrue(paciente.checar_senha("SenhaForte123!"))

	def test_cadastro_rejects_duplicate_cpf(self):
		paciente = Paciente(nome_completo="Existente", cpf="39053344705", email="a@a.com")
		paciente.set_senha("SenhaForte123!")
		paciente.save()

		response = self.client.post(
			"/cadastro/",
			{
				"nome_completo": "Outro Nome",
				"cpf": "390.533.447-05",
				"data_nascimento": "1990-05-10",
				"email": "outro@example.com",
				"senha": "OutraSenha123!",
			},
		)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Paciente.objects.count(), 1)
		self.assertContains(response, "Já existe uma conta cadastrada com este CPF.")

	def test_login_with_correct_credentials_redirects_to_area_paciente(self):
		paciente = Paciente(nome_completo="Joao da Silva", cpf="39053344705", email="joao@example.com")
		paciente.set_senha("SenhaForte123!")
		paciente.save()

		response = self.client.post(
			"/login/", {"cpf": "390.533.447-05", "senha": "SenhaForte123!"}
		)
		self.assertRedirects(response, "/area-paciente/")

		area_response = self.client.get("/area-paciente/")
		self.assertEqual(area_response.status_code, 200)

	def test_login_with_wrong_password_shows_error(self):
		paciente = Paciente(nome_completo="Joao da Silva", cpf="39053344705", email="joao@example.com")
		paciente.set_senha("SenhaForte123!")
		paciente.save()

		response = self.client.post(
			"/login/", {"cpf": "390.533.447-05", "senha": "senha-errada"}
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "CPF ou senha inválidos")

	def test_area_paciente_requires_login(self):
		response = self.client.get("/area-paciente/")
		self.assertRedirects(response, "/login/")

	def test_logout_clears_session(self):
		paciente = Paciente(nome_completo="Joao da Silva", cpf="39053344705", email="joao@example.com")
		paciente.set_senha("SenhaForte123!")
		paciente.save()
		self.client.post("/login/", {"cpf": "390.533.447-05", "senha": "SenhaForte123!"})

		self.client.post("/logout/")
		response = self.client.get("/area-paciente/")
		self.assertRedirects(response, "/login/")


class FluxoAtendimentoIntegrationTests(TestCase):
	def setUp(self):
		self.paciente = Paciente.objects.create(
			nome_completo="Maria Teste",
			cpf="39053344705",
			data_nascimento="1990-05-10",
			nome_mae="Mae Teste",
		)
		self.agendamento = Agendamento.objects.create(
			paciente=self.paciente,
			data_agendamento=date.today(),
			tipo_atendimento="consulta",
			status=Agendamento.Status.AGENDADO,
		)
		self.usuario = UsuarioSistema.objects.create(
			nome_completo="Staff Teste",
			email_institucional="staff@teste.com",
			cpf="11122233344",
			nivel_acesso="recepcionista",
		)
		self.session = self.client.session
		self.session["staff_logged_in"] = True
		self.session["staff_usuario_id"] = self.usuario.pk
		self.session.save()

	def test_fluxo_completo_checkin_ate_conclusao(self):
		"""Fluxo completo: check-in → fila → chamar → iniciar → concluir."""
		from core.services import registrar_checkin
		encaixe = registrar_checkin(self.paciente, "1990-05-10", "Mae Teste")
		self.assertIsNotNone(encaixe)
		self.assertEqual(encaixe.status, EncaixePaciente.Status.AGUARDANDO)
		self.assertEqual(encaixe.origem, EncaixePaciente.Origem.CHECKIN)
		self.assertTrue(encaixe.senha.startswith("E"))
		self.assertEqual(encaixe.posicao_fila, 1)

		self.agendamento.refresh_from_db()
		self.assertEqual(self.agendamento.status, Agendamento.Status.CHECKIN_REALIZADO)

	def test_chamar_paciente_transiciona_para_chamado(self):
		from core.services import registrar_checkin
		encaixe = registrar_checkin(self.paciente, "1990-05-10", "Mae Teste")

		response = self.client.post("/sistema/chamar/", {"senha": encaixe.senha})
		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertTrue(data["ok"])

		encaixe.refresh_from_db()
		self.assertEqual(encaixe.status, EncaixePaciente.Status.CHAMADO)
		self.assertIsNotNone(encaixe.chamado_em)
		self.assertEqual(encaixe.sala, "Sala 1")

	def test_chamar_paciente_requer_autenticacao(self):
		self.session.flush()
		self.session.save()
		from core.services import registrar_checkin
		encaixe = registrar_checkin(self.paciente, "1990-05-10", "Mae Teste")

		response = self.client.post("/sistema/chamar/", {"senha": encaixe.senha})
		self.assertEqual(response.status_code, 401)

	def test_chamar_paciente_rejeita_status_invalido(self):
		from core.services import registrar_checkin
		encaixe = registrar_checkin(self.paciente, "1990-05-10", "Mae Teste")
		encaixe.status = EncaixePaciente.Status.CONCLUIDO
		encaixe.save()

		response = self.client.post("/sistema/chamar/", {"senha": encaixe.senha})
		self.assertEqual(response.status_code, 409)
		self.assertIn("não está aguardando", response.json()["erro"])

	def test_iniciar_atendimento_apos_chamar(self):
		from core.services import registrar_checkin
		encaixe = registrar_checkin(self.paciente, "1990-05-10", "Mae Teste")
		self.client.post("/sistema/chamar/", {"senha": encaixe.senha})

		response = self.client.post(f"/encaixe/{encaixe.pk}/iniciar-atendimento/")
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()["ok"])

		encaixe.refresh_from_db()
		self.assertEqual(encaixe.status, EncaixePaciente.Status.ATENDIMENTO)

	def test_concluir_atendimento_apos_iniciar(self):
		from core.services import registrar_checkin
		encaixe = registrar_checkin(self.paciente, "1990-05-10", "Mae Teste")
		self.client.post("/sistema/chamar/", {"senha": encaixe.senha})
		self.client.post(f"/encaixe/{encaixe.pk}/iniciar-atendimento/")

		response = self.client.post(f"/encaixe/{encaixe.pk}/concluir-atendimento/")
		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertTrue(data["ok"])
		self.assertIn("pesquisa-satisfacao", data["redirect_url"])

		encaixe.refresh_from_db()
		self.assertEqual(encaixe.status, EncaixePaciente.Status.CONCLUIDO)

	def test_painel_chamada_com_dados_reais(self):
		from core.services import registrar_checkin
		encaixe = registrar_checkin(self.paciente, "1990-05-10", "Mae Teste")
		self.client.post("/sistema/chamar/", {"senha": encaixe.senha})

		context = get_painel_chamada_context(use_real_data=True)
		self.assertEqual(context["current_call"]["ticket"], encaixe.senha)
		self.assertEqual(context["current_call"]["patient_name"], encaixe.nome_completo.upper())
		self.assertIn(context["current_call"]["room"], context["current_call"]["room"])
		self.assertTrue(len(context["recent_calls"]) >= 1)
		self.assertEqual(context["recent_calls"][0]["ticket"], encaixe.senha)

	def test_acompanhamento_com_dados_reais(self):
		from core.services import registrar_checkin
		encaixe = registrar_checkin(self.paciente, "1990-05-10", "Mae Teste")

		session = self.client.session
		session["encaixe_id"] = encaixe.pk
		session["paciente_id"] = self.paciente.pk
		session.save()

		response = self.client.get("/acompanhamento-atendimento/")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, encaixe.nome_completo)
		self.assertContains(response, encaixe.senha)

	def test_validar_encaixe_flow(self):
		from core.services import registrar_encaixe
		encaixe = registrar_encaixe({
			"nome_completo": "Paciente Encaixe",
			"cpf": "12345678901",
			"data_nascimento": None,
			"nome_mae": "",
			"tipos_atendimento": ["consulta"],
			"justificativa": "",
		})
		self.assertEqual(encaixe.status, EncaixePaciente.Status.VALIDACAO)
		self.assertEqual(encaixe.origem, EncaixePaciente.Origem.ENCAIXE)

		response = self.client.post(f"/encaixe/{encaixe.pk}/validar/")
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()["ok"])

		encaixe.refresh_from_db()
		self.assertEqual(encaixe.status, EncaixePaciente.Status.AGUARDANDO)

	def test_fluxo_rejeita_pular_etapas(self):
		from core.services import registrar_checkin
		encaixe = registrar_checkin(self.paciente, "1990-05-10", "Mae Teste")

		response = self.client.post(f"/encaixe/{encaixe.pk}/concluir-atendimento/")
		self.assertEqual(response.status_code, 400)
		self.assertIn("não está em andamento", response.json()["erro"])

		response = self.client.post(f"/encaixe/{encaixe.pk}/iniciar-atendimento/")
		self.assertEqual(response.status_code, 400)
		self.assertIn("não foi chamado", response.json()["erro"])

	def test_posicao_fila_incremental(self):
		from core.services import registrar_checkin
		p2 = Paciente.objects.create(nome_completo="Paciente 2", cpf="22233344455")
		Agendamento.objects.create(paciente=p2, data_agendamento=date.today(), tipo_atendimento="consulta")

		e1 = registrar_checkin(self.paciente, "1990-05-10", "Mae Teste")
		e2 = registrar_checkin(p2, "1990-05-10", "")
		self.assertEqual(e1.posicao_fila, 1)
		self.assertEqual(e2.posicao_fila, 2)


class WebSocketEventosTests(TestCase):
	@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
	def test_notificar_fila_atualizada_envia_evento(self):
		from core.websocket_utils import notificar_fila_atualizada
		from channels.layers import get_channel_layer
		from asgiref.sync import async_to_sync

		layer = get_channel_layer()
		async_to_sync(layer.group_add)("test_group", "test_channel")

		Paciente.objects.create(nome_completo="Teste", cpf="39053344705")
		notificar_fila_atualizada()

		messages = async_to_sync(layer.receive)("test_channel")
		self.assertIsNotNone(messages)
		self.assertEqual(messages.get("type"), "fila.atualizada")

	@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
	def test_notificar_painel_chamada_envia_evento(self):
		from core.websocket_utils import notificar_painel_chamada
		from channels.layers import get_channel_layer
		from asgiref.sync import async_to_sync

		layer = get_channel_layer()
		async_to_sync(layer.group_add)("painel_chamada", "test_channel")

		encaixe = EncaixePaciente.objects.create(
			nome_completo="Teste", cpf="39053344705",
			senha="E001", posicao_fila=1,
		)
		notificar_painel_chamada(encaixe, "Sala 1", "Guiche 1")

		messages = async_to_sync(layer.receive)("test_channel")
		self.assertIsNotNone(messages)
		self.assertEqual(messages.get("type"), "paciente.chamado")
		self.assertEqual(messages.get("senha"), "E001")

	@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
	def test_notificar_paciente_envia_evento(self):
		from core.websocket_utils import notificar_paciente
		from channels.layers import get_channel_layer
		from asgiref.sync import async_to_sync

		layer = get_channel_layer()
		async_to_sync(layer.group_add)("paciente_39053344705", "test_channel")

		notificar_paciente("39053344705", "paciente.chamado", senha="E001", nome="Teste", sala="Sala 1")

		messages = async_to_sync(layer.receive)("test_channel")
		self.assertIsNotNone(messages)
		self.assertEqual(messages.get("type"), "paciente.chamado")

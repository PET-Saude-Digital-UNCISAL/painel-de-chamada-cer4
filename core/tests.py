from django.test import TestCase, override_settings

from core.dev_builders import build_fake_screen_list, build_mocked_screen_payload
from core.services import (
	get_dashboard_monitoramento_context,
	get_painel_chamada_context,
	get_paciente_chamado_context,
	get_screen_context,
	list_team_screens,
)
from core.models import Paciente, UsuarioSistema


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

	def test_dashboard_monitoramento_context_has_expected_mock_data(self):
		context = get_dashboard_monitoramento_context()
		self.assertEqual(context["current_time"], "09:48")
		self.assertEqual(len(context["kpis"]), 6)
		self.assertEqual(len(context["chart"]["bars"]), 7)
		self.assertEqual(len(context["encaixes"]["requests"]), 3)
		self.assertEqual(len(context["kanban_columns"]), 4)
		self.assertTrue(all(len(column["patients"]) == 3 for column in context["kanban_columns"]))

	def test_dashboard_monitoramento_route_renders_context_data(self):
		response = self.client.get("/dashboard-monitoramento/")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Monitoramento do Fluxo")
		self.assertContains(response, "Roberto Almeida")
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
		self.assertTemplateUsed(response, "core/painel_chamada.html")
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
		self.assertTrue(context["public_sans_font_url"].startswith("data:font/ttf;base64,"))

	def test_paciente_chamado_route_renders_context_data(self):
		response = self.client.get("/paciente-chamado/")
		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, "core/paciente_chamado.html")
		self.assertContains(response, "A012")
		self.assertContains(response, "RICARDO AUGUSTO OLIVEIRA")
		self.assertContains(response, "data:font/ttf;base64,")
		self.assertNotContains(response, "fonts.googleapis.com")
		self.assertNotContains(response, "styles.css")
		self.assertContains(response, "Simular chamada")
		self.assertNotContains(response, "Entendi, estou a caminho")
		self.assertContains(response, "navigator.vibrate")
		self.assertContains(response, "4500")
		self.assertContains(response, "data:audio/mpeg;base64,")
		self.assertContains(response, 'role="alert"')
		self.assertContains(response, "prefers-reduced-motion")

	def test_list_team_screens_has_expected_registered_screens(self):
		screens = list_team_screens()
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

		pending_response = self.client.get("/sistema-interno/?tela=relatorios")
		self.assertEqual(pending_response.status_code, 200)
		self.assertContains(pending_response, "desenvolvida")

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

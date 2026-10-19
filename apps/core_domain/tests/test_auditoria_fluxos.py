"""Testes de ponta a ponta: o "quem" gravado em cada fluxo real.

Regras (Tarefa 3 do plano de auditoria):
- acoes da recepcao/staff registram o UsuarioSistema logado (middleware);
- acoes do paciente nunca registram autor, mesmo com staff logado na
  mesma sessao (tablet da recepcao);
- /encaixe/ aberto e /api/v1/encaixes/ registram o staff se houver, senao
  ficam vazios;
- integrador e comandos sem sessao ficam vazios, a menos que o ator seja
  passado explicitamente (usando_ator / --ator).
"""

from datetime import date, timedelta
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone

from apps.core_domain.auditoria import usando_ator
from core.integrador import AgendamentoExterno, IntegradorBase, sincronizar_agendamentos
from core.models import Agendamento, EncaixePaciente, Paciente, UsuarioSistema

CPF_PACIENTE = "39053344705"


class _FluxoBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = UsuarioSistema.objects.create(
            nome_completo="Recepcao Teste",
            email_institucional="recepcao@teste.com",
            cpf="11122233344",
            nivel_acesso=UsuarioSistema.NivelAcesso.RECEPCIONISTA,
        )

    def _logar_staff(self):
        session = self.client.session
        session["staff_logged_in"] = True
        session["staff_usuario_id"] = self.staff.pk
        session.save()

    def _encaixe(self, status=EncaixePaciente.Status.VALIDACAO):
        encaixe = EncaixePaciente.objects.create(
            nome_completo="Paciente Fila",
            cpf=CPF_PACIENTE,
            senha="E001",
            posicao_fila=1,
            status=status,
        )
        # atualizado_em no passado, pra comparar sem depender do relogio.
        EncaixePaciente.objects.filter(pk=encaixe.pk).update(
            atualizado_em=timezone.now() - timedelta(days=1)
        )
        encaixe.refresh_from_db()
        return encaixe


class FluxosDaRecepcaoTests(_FluxoBase):
    def setUp(self):
        self._logar_staff()

    def test_validar_encaixe_registra_o_staff(self):
        encaixe = self._encaixe()
        antes = encaixe.atualizado_em

        response = self.client.post(f"/encaixe/{encaixe.pk}/validar/")

        self.assertEqual(response.status_code, 200)
        encaixe.refresh_from_db()
        self.assertEqual(encaixe.status, EncaixePaciente.Status.AGUARDANDO)
        self.assertEqual(encaixe.atualizado_por, self.staff)
        self.assertGreater(encaixe.atualizado_em, antes)

    def test_chamar_paciente_registra_o_staff(self):
        encaixe = self._encaixe(status=EncaixePaciente.Status.AGUARDANDO)

        response = self.client.post("/sistema/chamar/", {"senha": encaixe.senha})

        self.assertEqual(response.status_code, 200)
        encaixe.refresh_from_db()
        self.assertEqual(encaixe.atualizado_por, self.staff)

    def test_encaixe_pela_recepcao_registra_o_staff(self):
        response = self.client.post(
            "/encaixe/",
            {"nome_completo": "Paciente Encaixe", "cpf": "", "tipos_atendimento": ["consulta"]},
        )

        self.assertEqual(response.status_code, 200, response.content)
        encaixe = EncaixePaciente.objects.get(nome_completo="Paciente Encaixe")
        self.assertEqual(encaixe.criado_por, self.staff)
        self.assertEqual(encaixe.atualizado_por, self.staff)


class EncaixeSemLoginTests(_FluxoBase):
    def test_encaixe_sem_staff_fica_sem_autor(self):
        response = self.client.post(
            "/encaixe/",
            {"nome_completo": "Paciente Encaixe", "cpf": "", "tipos_atendimento": ["consulta"]},
        )

        self.assertEqual(response.status_code, 200, response.content)
        encaixe = EncaixePaciente.objects.get(nome_completo="Paciente Encaixe")
        self.assertIsNone(encaixe.criado_por)


class AcoesDoPacienteTests(_FluxoBase):
    """Staff logado na mesma sessao nao pode virar autor das acoes do
    paciente."""

    def setUp(self):
        self._logar_staff()

    def test_checkin_pela_identificacao_nao_registra_o_staff(self):
        paciente = Paciente.objects.create(
            nome_completo="Maria Teste", cpf=CPF_PACIENTE, senha_hash="x"
        )
        agendamento = Agendamento.objects.create(
            paciente=paciente,
            data_agendamento=timezone.localdate(),
            tipo_atendimento="consulta",
        )

        self.client.post("/identificacao-paciente/", {"cpf": CPF_PACIENTE})

        encaixe = EncaixePaciente.objects.get(paciente=paciente)
        self.assertIsNone(encaixe.criado_por)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, Agendamento.Status.CHECKIN_REALIZADO)
        self.assertIsNone(agendamento.atualizado_por)

    def test_cadastro_pela_api_nao_registra_o_staff(self):
        response = self.client.post(
            "/api/v1/pacientes/cadastro/",
            {
                "nome_completo": "Paciente App",
                "cpf": CPF_PACIENTE,
                "senha": "senha-segura-123",
                "confirmar_senha": "senha-segura-123",
            },
        )

        self.assertEqual(response.status_code, 201, response.content)
        paciente = Paciente.objects.get(cpf=CPF_PACIENTE)
        self.assertIsNone(paciente.criado_por)


class _IntegradorFake(IntegradorBase):
    def __init__(self, observacoes="primeira carga"):
        self.observacoes = observacoes

    def buscar_agendamentos_do_dia(self, data_alvo=None):
        return [
            AgendamentoExterno(
                nome_completo="Paciente Externo",
                cpf=CPF_PACIENTE,
                data_agendamento=(data_alvo or date.today()).isoformat(),
                observacoes=self.observacoes,
            )
        ]


class IntegradorTests(_FluxoBase):
    def test_sem_ator_fica_sem_autor(self):
        sincronizar_agendamentos(integrador=_IntegradorFake())

        agendamento = Agendamento.objects.get()
        self.assertIsNone(agendamento.criado_por)
        self.assertIsNone(agendamento.paciente.criado_por)

    def test_com_ator_registra_criacao_e_atualizacao(self):
        with usando_ator(self.staff):
            sincronizar_agendamentos(integrador=_IntegradorFake())

        outro = UsuarioSistema.objects.create(
            nome_completo="Coordenacao",
            email_institucional="coord@teste.com",
            cpf="55566677788",
            nivel_acesso=UsuarioSistema.NivelAcesso.COORDENACAO,
        )
        # Segunda sincronizacao: cai no ramo de update do update_or_create.
        with usando_ator(outro):
            sincronizar_agendamentos(integrador=_IntegradorFake(observacoes="atualizado"))

        agendamento = Agendamento.objects.get()
        self.assertEqual(agendamento.observacoes, "atualizado")
        self.assertEqual(agendamento.criado_por, self.staff)
        self.assertEqual(agendamento.atualizado_por, outro)

    @mock.patch("core.management.commands.sincronizar_agendamentos.IntegradorHttp")
    def test_comando_com_ator(self, integrador_http):
        integrador_http.return_value = _IntegradorFake()

        call_command(
            "sincronizar_agendamentos",
            base_url="http://externo.invalid",
            ator=self.staff.email_institucional,
            stdout=mock.Mock(),
            stderr=mock.Mock(),
        )

        self.assertEqual(Agendamento.objects.get().criado_por, self.staff)

    def test_comando_com_ator_inexistente_falha(self):
        with self.assertRaises(CommandError):
            call_command(
                "sincronizar_agendamentos",
                base_url="http://externo.invalid",
                ator="ninguem@teste.com",
            )
        self.assertFalse(Agendamento.objects.exists())

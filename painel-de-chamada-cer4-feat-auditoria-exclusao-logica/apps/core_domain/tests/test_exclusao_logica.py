"""Testes do comportamento da exclusao logica (Tarefa 4 do plano de auditoria).

Cobre: senha da fila com encaixe excluido, CPF de paciente excluido
(reimportacao e autocadastro), cascata Paciente -> Agendamento/Encaixe e
exclusao de UsuarioSistema que ja tem registros.
"""

from datetime import date

from django.test import TestCase
from django.utils import timezone

from apps.core_domain.auditoria import usando_ator
from core.forms import CadastroPacienteForm
from core.models import Agendamento, EncaixePaciente, Paciente, UsuarioSistema
from core.services.encaixe import registrar_encaixe
from core.services.paciente import obter_ou_criar_paciente

CPF_VALIDO = "39053344705"


def _usuario(sufixo, nivel=UsuarioSistema.NivelAcesso.RECEPCIONISTA):
    return UsuarioSistema.objects.create(
        nome_completo=f"Staff {sufixo}",
        email_institucional=f"staff.{sufixo}@teste.com",
        cpf=f"{sufixo:0>11}",
        nivel_acesso=nivel,
    )


def _paciente(cpf=CPF_VALIDO):
    paciente = Paciente(nome_completo="Paciente Teste", cpf=cpf)
    paciente.set_senha("senha-teste-123")
    paciente.save()
    return paciente


def _agendamento(paciente, dia=1):
    return Agendamento.objects.create(
        paciente=paciente,
        data_agendamento=date(2026, 10, dia),
        tipo_atendimento="consulta",
    )


def _encaixe(paciente, senha="E001", posicao=1):
    return EncaixePaciente.objects.create(
        paciente=paciente,
        nome_completo=paciente.nome_completo,
        cpf=paciente.cpf,
        senha=senha,
        posicao_fila=posicao,
        data_atendimento=timezone.localdate(),
    )


class SenhaDaFilaTests(TestCase):
    def test_senha_de_encaixe_excluido_nao_e_reaproveitada(self):
        staff = _usuario("1")
        dados = {"nome_completo": "Paciente Fila", "cpf": "", "tipos_atendimento": ["consulta"]}

        with usando_ator(staff):
            primeiro = registrar_encaixe(dados)
            primeiro.delete()
            segundo = registrar_encaixe(dados)

        self.assertNotEqual(primeiro.senha, segundo.senha)
        self.assertEqual(segundo.posicao_fila, primeiro.posicao_fila + 1)


class CpfDePacienteExcluidoTests(TestCase):
    def setUp(self):
        self.staff = _usuario("1")

    def test_reimportar_cpf_de_paciente_excluido_restaura_sem_erro(self):
        paciente = _paciente()
        with usando_ator(self.staff):
            paciente.delete()

        restaurado, criado = obter_ou_criar_paciente(
            CPF_VALIDO, defaults={"nome_completo": "Outro Nome"}
        )

        self.assertFalse(criado)
        self.assertEqual(restaurado.pk, paciente.pk)
        self.assertIsNone(restaurado.excluido_em)
        self.assertTrue(Paciente.objects.filter(pk=paciente.pk).exists())

    def test_cpf_novo_cria_paciente(self):
        paciente, criado = obter_ou_criar_paciente(
            CPF_VALIDO, defaults={"nome_completo": "Paciente Novo", "senha_hash": "x"}
        )

        self.assertTrue(criado)
        self.assertEqual(paciente.nome_completo, "Paciente Novo")

    def test_autocadastro_com_cpf_de_paciente_excluido_da_erro_de_validacao(self):
        paciente = _paciente()
        with usando_ator(self.staff):
            paciente.delete()

        form = CadastroPacienteForm(
            data={
                "nome_completo": "Maria Oliveira",
                "cpf": CPF_VALIDO,
                "senha": "senha-forte-123",
                "confirmar_senha": "senha-forte-123",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("cpf", form.errors)


class CascataDoPacienteTests(TestCase):
    def setUp(self):
        self.staff = _usuario("1")
        self.paciente = _paciente()
        self.agendamento = _agendamento(self.paciente)
        self.encaixe = _encaixe(self.paciente)

    def test_excluir_paciente_exclui_agendamentos_e_encaixes(self):
        with usando_ator(self.staff):
            self.paciente.delete()

        self.assertFalse(Paciente.objects.filter(pk=self.paciente.pk).exists())
        self.assertFalse(Agendamento.objects.filter(pk=self.agendamento.pk).exists())
        self.assertFalse(EncaixePaciente.objects.filter(pk=self.encaixe.pk).exists())

        agendamento = Agendamento.all_objects.get(pk=self.agendamento.pk)
        self.assertEqual(agendamento.excluido_por, self.staff)
        self.assertEqual(agendamento.excluido_em, self.paciente.excluido_em)

    def test_restaurar_volta_so_o_que_foi_excluido_junto(self):
        # Este agendamento foi excluido antes, por outro motivo: nao pode
        # voltar quando o paciente for restaurado.
        antigo = _agendamento(self.paciente, dia=2)
        with usando_ator(self.staff):
            antigo.delete()
            self.paciente.delete()
            self.paciente.restaurar()

        self.assertTrue(Paciente.objects.filter(pk=self.paciente.pk).exists())
        self.assertTrue(Agendamento.objects.filter(pk=self.agendamento.pk).exists())
        self.assertTrue(EncaixePaciente.objects.filter(pk=self.encaixe.pk).exists())
        self.assertFalse(Agendamento.objects.filter(pk=antigo.pk).exists())

    def test_excluir_paciente_sem_ator_levanta_erro_e_nao_altera_nada(self):
        with self.assertRaises(ValueError):
            self.paciente.delete()

        self.assertTrue(Paciente.objects.filter(pk=self.paciente.pk).exists())
        self.assertTrue(Agendamento.objects.filter(pk=self.agendamento.pk).exists())


class ExcluirUsuarioSistemaTests(TestCase):
    def setUp(self):
        self.admin = _usuario("1", nivel=UsuarioSistema.NivelAcesso.SUPER_ADMIN)
        session = self.client.session
        session["staff_logged_in"] = True
        session["staff_usuario_id"] = self.admin.pk
        session.save()

    def _excluir(self, usuario):
        return self.client.post(
            "/configuracoes/", {"action": "delete", "usuario_id": usuario.pk}
        )

    def test_usuario_com_registros_e_desativado_em_vez_de_excluido(self):
        recepcao = _usuario("2")
        with usando_ator(recepcao):
            _paciente()  # grava criado_por = recepcao

        response = self._excluir(recepcao)

        self.assertEqual(response.status_code, 302)
        self.assertIn("resultado=desativado", response["Location"])
        recepcao.refresh_from_db()
        self.assertFalse(recepcao.usuario_ativo)

    def test_usuario_sem_registros_continua_sendo_excluido(self):
        sem_registros = _usuario("3")

        response = self._excluir(sem_registros)

        self.assertIn("resultado=excluido", response["Location"])
        self.assertFalse(UsuarioSistema.objects.filter(pk=sem_registros.pk).exists())
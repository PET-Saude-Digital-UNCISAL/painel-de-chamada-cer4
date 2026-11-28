"""Regressao: o horario dos "ultimos chamados" na TV deve estar no fuso local.

Antes, chamado_em (guardado em UTC) era formatado direto com strftime e a
TV mostrava o horario 3 horas adiantado, enquanto o relogio do topo da
mesma tela mostrava o horario correto.
"""

from datetime import date
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from core.models import Agendamento, EncaixePaciente, Paciente
from core.services import registrar_checkin
from core.services.paciente import get_painel_chamada_context
from core.websocket_utils import notificar_fila_atualizada


class HorarioUltimosChamadosTests(TestCase):
    def setUp(self):
        paciente = Paciente.objects.create(
            nome_completo="Maria Teste",
            cpf="39053344705",
            data_nascimento="1990-05-10",
            nome_mae="Mae Teste",
        )
        Agendamento.objects.create(
            paciente=paciente,
            data_agendamento=date.today(),
            tipo_atendimento="consulta",
            status=Agendamento.Status.AGENDADO,
        )
        self.encaixe = registrar_checkin(paciente, "1990-05-10", "Mae Teste")
        self.encaixe.status = EncaixePaciente.Status.CHAMADO
        self.encaixe.sala = "Sala 1"
        self.encaixe.chamado_em = timezone.now()
        self.encaixe.save(update_fields=["status", "sala", "chamado_em"])
        self.horario_local = timezone.localtime(self.encaixe.chamado_em).strftime("%H:%M")

    def test_pagina_inicial_da_tv_usa_horario_local(self):
        contexto = get_painel_chamada_context(use_real_data=True)
        horarios = [chamada["time"] for chamada in contexto["recent_calls"]]
        self.assertIn(self.horario_local, horarios)

    def test_atualizacao_por_websocket_usa_horario_local(self):
        with mock.patch("core.websocket_utils._group_send") as group_send:
            notificar_fila_atualizada()
        evento = next(c for c in group_send.call_args_list if c.args[1] == "fila_atualizada")
        horarios = [chamada["time"] for chamada in evento.kwargs["recent_calls"]]
        self.assertIn(self.horario_local, horarios)
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from django.db import transaction
from django.utils import timezone

from core.models import Agendamento, Paciente, EncaixePaciente


@dataclass
class AgendamentoExterno:
    nome_completo: str
    cpf: str
    data_nascimento: Optional[str] = None
    nome_mae: str = ""
    tipo_atendimento: str = "consulta"
    data_agendamento: str = ""
    hora_agendamento: Optional[str] = None
    observacoes: str = ""
    id_externo: str = ""


class IntegradorBase:
    BASE_URL = ""
    TIMEOUT = 30

    def buscar_agendamentos_do_dia(self, data_alvo: Optional[date] = None) -> list[AgendamentoExterno]:
        raise NotImplementedError

    def notificar_conclusao(self, encaixe: EncaixePaciente) -> bool:
        raise NotImplementedError


class IntegradorHttp(IntegradorBase):
    def __init__(self, base_url: str, token: str = ""):
        self.BASE_URL = base_url.rstrip("/")
        self.token = token

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def buscar_agendamentos_do_dia(self, data_alvo: Optional[date] = None) -> list[AgendamentoExterno]:
        import requests
        data = data_alvo or date.today()
        url = f"{self.BASE_URL}/api/agendamentos?data={data.isoformat()}"
        resp = requests.get(url, headers=self._headers(), timeout=self.TIMEOUT)
        resp.raise_for_status()
        dados = resp.json()
        return [
            AgendamentoExterno(
                nome_completo=item.get("nome_completo", ""),
                cpf=item.get("cpf", ""),
                data_nascimento=item.get("data_nascimento"),
                nome_mae=item.get("nome_mae", ""),
                tipo_atendimento=item.get("tipo_atendimento", "consulta"),
                data_agendamento=item.get("data_agendamento", data.isoformat()),
                hora_agendamento=item.get("hora_agendamento"),
                observacoes=item.get("observacoes", ""),
                id_externo=item.get("id", ""),
            )
            for item in dados
        ]

    def notificar_conclusao(self, encaixe: EncaixePaciente) -> bool:
        import requests
        url = f"{self.BASE_URL}/api/agendamentos/{encaixe.pk}/conclusao"
        payload = {
            "senha": encaixe.senha,
            "cpf": encaixe.cpf,
            "status": "concluido",
            "sala": encaixe.sala,
            "concluido_em": timezone.now().isoformat(),
        }
        try:
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=self.TIMEOUT)
            return resp.ok
        except requests.RequestException:
            return False


def sincronizar_agendamentos(data_alvo: Optional[date] = None, integrador: Optional[IntegradorBase] = None) -> dict:
    from django.conf import settings

    if integrador is None:
        base_url = getattr(settings, "INTEGRADOR_BASE_URL", "")
        token = getattr(settings, "INTEGRADOR_TOKEN", "")
        if not base_url:
            return {"ok": False, "erro": "INTEGRADOR_BASE_URL não configurado em settings.py"}
        integrador = IntegradorHttp(base_url=base_url, token=token)

    data = data_alvo or date.today()
    agendamentos_externos = integrador.buscar_agendamentos_do_dia(data_alvo=data)

    criados = 0
    atualizados = 0
    erros = []

    with transaction.atomic():
        for ext in agendamentos_externos:
            cpf_limpo = ext.cpf.replace(".", "").replace("-", "").strip()
            if not cpf_limpo:
                erros.append(f"Registro sem CPF: {ext.nome_completo}")
                continue

            paciente, _ = Paciente.objects.get_or_create(
                cpf=cpf_limpo,
                defaults={
                    "nome_completo": ext.nome_completo,
                    "nome_mae": ext.nome_mae,
                    "data_nascimento": (
                        date.fromisoformat(ext.data_nascimento) if ext.data_nascimento else None
                    ),
                },
            )

            data_ag = date.fromisoformat(ext.data_agendamento) if ext.data_agendamento else data
            ag, created = Agendamento.objects.update_or_create(
                paciente=paciente,
                data_agendamento=data_ag,
                defaults={
                    "hora_agendamento": (
                        datetime.strptime(ext.hora_agendamento, "%H:%M").time()
                        if ext.hora_agendamento
                        else None
                    ),
                    "tipo_atendimento": ext.tipo_atendimento,
                    "observacoes": ext.observacoes,
                    "status": Agendamento.Status.AGENDADO,
                },
            )
            if created:
                criados += 1
            else:
                atualizados += 1

    return {
        "ok": True,
        "data": data.isoformat(),
        "total_recebidos": len(agendamentos_externos),
        "criados": criados,
        "atualizados": atualizados,
        "erros": erros,
    }

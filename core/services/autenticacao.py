"""Contextos e regras de negocio do dominio de autenticacao.

Login, cadastro e a tela de "Acesso ao Portal" do paciente/staff.
"""

from datetime import date
from typing import Optional

from core.clock import SystemClock
from core.models import Paciente


def _cabecalho_recepcao_context(guiche: str = "RECEPÇÃO 3") -> dict:

    """Contexto compartilhado pelo cabeçalho das telas de Login e Cadastro."""

    now = SystemClock.now()

    return {

        "guiche": guiche,

        "data_atual_pt": formatar_data_pt(now.date()),

        "hora_atual": now.strftime("%H:%M"),

    }





def get_login_context() -> dict:

    """Contexto da tela de Login (Acesso ao Portal)."""

    return {

        "page_title": "Acesso ao Portal",

        **_cabecalho_recepcao_context(),

    }





def get_cadastro_context() -> dict:

    """Contexto da tela de Cadastro (Criar Conta do paciente)."""

    return {

        "page_title": "Criar Conta",

        **_cabecalho_recepcao_context(),

    }





_DIAS_PT = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]

_MESES_PT = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]





def formatar_data_pt(d: date) -> str:

    return f"{_DIAS_PT[d.weekday()]}, {d.day:02d} de {_MESES_PT[d.month]} de {d.year}"





def autenticar_paciente(cpf: str, senha: str) -> Optional[Paciente]:

    """Retorna o Paciente se CPF e senha conferem e a conta está ativa."""

    try:

        paciente = Paciente.objects.get(cpf=cpf, paciente_ativo=True)

    except Paciente.DoesNotExist:

        return None



    if not paciente.checar_senha(senha):

        return None



    return paciente

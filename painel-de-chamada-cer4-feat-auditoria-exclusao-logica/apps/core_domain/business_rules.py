from datetime import datetime

from apps.core_domain.clock import SystemClock


def is_deadline_expired(deadline_at: datetime, clock=SystemClock) -> bool:
    """True quando o instante atual (via clock, injetavel nos testes) ja
    passou de `deadline_at`."""
    return clock.now() > deadline_at


def can_run_reception_workflow(clock=SystemClock) -> bool:
    """True de segunda a sexta -- a recepcao nao funciona no fim de semana,
    entao fluxos que dependem de expediente (ex.: sincronizacao de
    agendamentos) checam isso antes de rodar."""
    current_weekday = clock.now().weekday()
    return current_weekday < 5


def apenas_digitos(valor: str) -> str:
    """Remove tudo que nao for digito -- usado pra normalizar CPF vindo de
    formulario (com ou sem pontuacao) antes de comparar/gravar."""
    return "".join(ch for ch in (valor or "") if ch.isdigit())


def formatar_cpf(cpf_digitos: str) -> str:
    """Formata uma string de 11 digitos como CPF (000.000.000-00). Se nao
    tiver exatamente 11 digitos, devolve o valor original sem mexer."""
    d = apenas_digitos(cpf_digitos)
    if len(d) != 11:
        return cpf_digitos
    return f"{d[0:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}"


def cpf_e_valido(cpf: str) -> bool:
    """Valida CPF pelo algoritmo oficial dos dois digitos verificadores.
    Rejeita tambem sequencias repetidas (ex.: 111.111.111-11), que passam
    no calculo mas nunca sao CPFs reais."""
    d = apenas_digitos(cpf)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(d[num]) * ((i + 1) - num) for num in range(0, i))
        digito_esperado = (soma * 10 % 11) % 10
        if digito_esperado != int(d[i]):
            return False
    return True


def nivel_forca_senha(senha: str) -> int:
    """Estima a forca de uma senha em uma escala de 0 a 3, somando pontos
    por comprimento minimo, mistura de maiusculas/minusculas, mistura de
    numero com simbolo e comprimento generoso. Usado so pra feedback visual
    no formulario, nao como unica regra de validacao."""
    if not senha:
        return 0
    pontos = 0
    if len(senha) >= 8:
        pontos += 1
    if any(c.islower() for c in senha) and any(c.isupper() for c in senha):
        pontos += 1
    if any(c.isdigit() for c in senha) and any(not c.isalnum() for c in senha):
        pontos += 1
    if len(senha) >= 12:
        pontos += 1
    return min(pontos, 3)

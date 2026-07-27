from datetime import datetime

from apps.core_domain.clock import SystemClock


def is_deadline_expired(deadline_at: datetime, clock=SystemClock) -> bool:
    return clock.now() > deadline_at


def can_run_reception_workflow(clock=SystemClock) -> bool:
    current_weekday = clock.now().weekday()
    return current_weekday < 5


def apenas_digitos(valor: str) -> str:
    return "".join(ch for ch in (valor or "") if ch.isdigit())


def formatar_cpf(cpf_digitos: str) -> str:
    d = apenas_digitos(cpf_digitos)
    if len(d) != 11:
        return cpf_digitos
    return f"{d[0:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}"


def cpf_e_valido(cpf: str) -> bool:
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

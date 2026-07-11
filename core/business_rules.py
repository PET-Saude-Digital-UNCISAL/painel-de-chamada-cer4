from datetime import datetime

from core.clock import SystemClock


def is_deadline_expired(deadline_at: datetime, clock=SystemClock) -> bool:
    """Example business rule: returns True when deadline has passed."""
    return clock.now() > deadline_at


def can_run_reception_workflow(clock=SystemClock) -> bool:
    """Example business rule: workflow runs only on weekdays.

    weekday(): Monday=0 ... Sunday=6
    """
    current_weekday = clock.now().weekday()
    return current_weekday < 5


def apenas_digitos(valor: str) -> str:
    """Remove qualquer caractere que não seja dígito."""
    return "".join(ch for ch in (valor or "") if ch.isdigit())


def formatar_cpf(cpf_digitos: str) -> str:
    """Formata uma string de 11 dígitos como CPF (000.000.000-00)."""
    d = apenas_digitos(cpf_digitos)
    if len(d) != 11:
        return cpf_digitos
    return f"{d[0:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}"


def cpf_e_valido(cpf: str) -> bool:
    """Valida CPF pelos dígitos verificadores."""
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
    """Retorna um nível de força de senha de 0 (fraca) a 3 (forte).

    Usado apenas como orientação visual (medidor de força) na tela de
    cadastro; a validação definitiva de tamanho mínimo é feita no form.
    """
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

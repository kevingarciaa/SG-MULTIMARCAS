import re

from django.core.exceptions import ValidationError


def somente_digitos(valor):
    return re.sub(r"\D", "", valor or "")


def validar_cpf(valor):
    """Valida CPF pelos dígitos verificadores. Aceita com ou sem pontuação."""
    cpf = somente_digitos(valor)

    if len(cpf) != 11 or cpf == cpf[0] * 11:
        raise ValidationError("CPF inválido.")

    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11 % 10
        if digito != int(cpf[tamanho]):
            raise ValidationError("CPF inválido.")


def validar_telefone(valor):
    digitos = somente_digitos(valor)
    if len(digitos) not in (10, 11):
        raise ValidationError("Informe o telefone com DDD, ex.: (11) 98765-4321.")

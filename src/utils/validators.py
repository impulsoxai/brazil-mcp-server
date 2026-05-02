"""Validação matemática de CPF e CNPJ — sem chamada de API."""


def sanitizar_input(valor: str, max_len: int = 500) -> str:
    """Trunca e remove caracteres de controle de uma string."""
    return valor[:max_len].strip()


def limpar_numeros(valor: str) -> str:
    """Remove tudo que não for dígito."""
    return ''.join(filter(str.isdigit, valor))


def validar_cpf(cpf: str) -> bool:
    """
    Valida CPF matematicamente.

    Aceita CPF com ou sem formatação (11 dígitos ou XXX.XXX.XXX-XX).
    Retorna False para CPFs com todos os dígitos iguais.
    """
    cpf = limpar_numeros(cpf)

    if len(cpf) != 11:
        return False

    # CPFs com todos os dígitos iguais são inválidos
    if cpf == cpf[0] * 11:
        return False

    # Validação do primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[9]):
        return False

    # Validação do segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[10]):
        return False

    return True


def validar_cnpj(cnpj: str) -> bool:
    """
    Valida CNPJ matematicamente.

    Aceita CNPJ com ou sem formatação (14 dígitos ou XX.XXX.XXX/XXXX-XX).
    Retorna False para CNPJs com todos os dígitos iguais.
    """
    cnpj = limpar_numeros(cnpj)

    if len(cnpj) != 14:
        return False

    # CNPJs com todos os dígitos iguais são inválidos
    if cnpj == cnpj[0] * 14:
        return False

    # Validação do primeiro dígito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    if digito1 != int(cnpj[12]):
        return False

    # Validação do segundo dígito verificador
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    if digito2 != int(cnpj[13]):
        return False

    return True

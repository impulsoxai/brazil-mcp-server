"""Formatação de dados brasileiros — CPF, CNPJ, CEP, telefone."""

from src.utils.validators import limpar_numeros


def formatar_cpf(cpf: str) -> str:
    """
    Formata CPF com máscara brasileira.

    Entrada: '12345678901' → Saída: '123.456.789-01'
    """
    cpf = limpar_numeros(cpf)
    if len(cpf) != 11:
        return cpf
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def formatar_cnpj(cnpj: str) -> str:
    """
    Formata CNPJ com máscara brasileira.

    Entrada: '12345678000199' → Saída: '12.345.678/0001-99'
    """
    cnpj = limpar_numeros(cnpj)
    if len(cnpj) != 14:
        return cnpj
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def formatar_cep(cep: str) -> str:
    """
    Formata CEP com máscara brasileira.

    Entrada: '01310100' → Saída: '01310-100'
    """
    cep = limpar_numeros(cep)
    if len(cep) != 8:
        return cep
    return f"{cep[:5]}-{cep[5:]}"


def formatar_telefone_br(telefone: str) -> str:
    """
    Formata telefone brasileiro com máscara.

    Celular (11 dígitos): '11999998888' → '(11) 99999-8888'
    Fixo (10 dígitos): '1133334444' → '(11) 3333-4444'
    """
    telefone = limpar_numeros(telefone)

    if len(telefone) == 11:
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
    elif len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
    else:
        return telefone


def formatar_endereco(
    logradouro: str = "",
    numero: str = "",
    complemento: str = "",
    bairro: str = "",
    cidade: str = "",
    uf: str = "",
    cep: str = "",
) -> str:
    """
    Formata endereço completo em string legível.

    Retorna endereço formatado ou string vazia se todos os campos forem vazios.
    """
    partes = []

    if logradouro:
        parte = logradouro
        if numero:
            parte += f", {numero}"
        if complemento:
            parte += f" — {complemento}"
        partes.append(parte)

    if bairro:
        partes.append(bairro)

    if cidade and uf:
        partes.append(f"{cidade}/{uf}")
    elif cidade:
        partes.append(cidade)

    if cep:
        partes.append(formatar_cep(cep))

    return " — ".join(partes) if partes else ""

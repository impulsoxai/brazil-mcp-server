"""Módulo de pagamentos — PIX, juros, financeiro."""

import re
import sys
from mcp.server.fastmcp import FastMCP

from src.utils.validators import limpar_numeros, validar_cpf, validar_cnpj


# Limites razoáveis
_VALOR_MAXIMO = 999_999_999.99
_MESES_MAXIMO = 600  # 50 anos
_DIAS_ATRASO_MAXIMO = 3650  # 10 anos


def _sanitizar_input(valor: str, max_len: int = 500) -> str:
    """Trunca e remove caracteres de controle de uma string."""
    return valor[:max_len].strip()


def _identificar_tipo_chave(chave: str) -> str | None:
    """Identifica o tipo de chave PIX. Retorna None se inválida."""
    chave = _sanitizar_input(chave, 200)

    if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', chave, re.IGNORECASE):
        return "aleatoria"

    if re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', chave):
        return "email"

    numeros = limpar_numeros(chave)

    if len(numeros) == 11 and validar_cpf(numeros):
        return "cpf"
    if len(numeros) == 14 and validar_cnpj(numeros):
        return "cnpj"

    if len(numeros) in (12, 13) and numeros.startswith("55"):
        return "telefone"
    if len(numeros) in (10, 11):
        return "telefone"

    return None


def _formatar_valor_brl(valor: float) -> str:
    """Formata valor no padrão BR: 1234.56 → 1234.56 (ponto como decimal)."""
    return f"{valor:.2f}"


def register_tools(mcp: FastMCP) -> None:
    """Registra as ferramentas de pagamentos no servidor MCP."""

    @mcp.tool()
    async def gerar_pix_copia_cola(
        chave: str,
        valor: float,
        nome: str,
        cidade: str,
        descricao: str = "",
    ) -> str:
        """
        Gera um payload PIX Copia e Cola (estático) no padrão EMV do Banco Central.

        Use quando precisar gerar um código PIX para o cliente copiar e colar no app do banco.
        A chave pode ser CPF, CNPJ, email, telefone ou aleatória.
        O valor é obrigatório para PIX estático.
        Retorna o payload EMV completo e o valor formatado.

        Parâmetros:
        - chave: chave PIX (CPF, CNPJ, email, telefone ou aleatória)
        - valor: valor em reais (máx R$ 999.999.999)
        - nome: nome do recebedor (máx 25 caracteres)
        - cidade: cidade do recebedor (máx 15 caracteres)
        - descricao: descrição opcional (máx 25 caracteres)
        """
        tipo = _identificar_tipo_chave(chave)
        if tipo is None:
            return (
                f"❌ Chave PIX inválida: '{chave}'.\n"
                "Dica: use CPF, CNPJ, email, telefone (+55XX9XXXXXXXX) ou chave aleatória (UUID)."
            )

        if valor <= 0:
            return (
                f"❌ Valor inválido: {valor}.\n"
                "Dica: o valor deve ser maior que zero."
            )

        if valor > _VALOR_MAXIMO:
            return (
                f"❌ Valor excede o limite: R$ {valor:,.2f} (máx R$ 999.999.999).\n"
                "Dica: use um valor menor."
            )

        nome = _sanitizar_input(nome, 25)
        if not nome:
            return "❌ Nome do recebedor é obrigatório."

        cidade = _sanitizar_input(cidade, 15)
        if not cidade:
            return "❌ Cidade do recebedor é obrigatória."

        descricao = _sanitizar_input(descricao, 25)

        payload = "0014br.gov.bcb.pix"
        chave_tag = f"01{len(chave):02d}{chave}"
        payload += chave_tag

        if descricao:
            desc_tag = f"02{len(descricao):02d}{descricao}"
            payload += desc_tag

        valor_str = _formatar_valor_brl(valor)
        nome_tag = f"59{len(nome.encode('utf-8')):02d}{nome}"
        cidade_tag = f"60{len(cidade.encode('utf-8')):02d}{cidade}"

        payload_format = "000201"
        merchant_account = f"26{len(payload):02d}{payload}"
        merchant_category = "52040000"
        transaction_currency = "5303986"
        tx_amount = f"54{len(valor_str):02d}{valor_str}"
        country_code = "5802BR"
        crc_placeholder = "6304"

        emv = (
            payload_format
            + merchant_account
            + merchant_category
            + transaction_currency
            + tx_amount
            + country_code
            + nome_tag
            + cidade_tag
            + crc_placeholder
        )

        crc = _calcular_crc16(emv)
        emv_final = emv + crc

        return (
            f"✅ PIX Copia e Cola gerado:\n\n"
            f"{emv_final}\n\n"
            f"Tipo da chave: {tipo}\n"
            f"Chave: {chave}\n"
            f"Valor: R$ {valor_str}\n"
            f"Recebedor: {nome}\n"
            f"Cidade: {cidade}"
            + (f"\nDescrição: {descricao}" if descricao else "")
        )

    @mcp.tool()
    async def validar_chave_pix(chave: str) -> str:
        """
        Valida o tipo e formato de uma chave PIX.

        Use para verificar se uma chave PIX é válida antes de usar.
        Aceita CPF, CNPJ, email, telefone e chave aleatória (UUID).
        Retorna o tipo identificado e se é válida.
        """
        tipo = _identificar_tipo_chave(chave)

        if tipo is None:
            return (
                f"❌ Chave PIX inválida: '{chave}'.\n"
                "Dica: use CPF (11 dígitos), CNPJ (14 dígitos), email, "
                "telefone (+55XX9XXXXXXXX) ou chave aleatória (UUID)."
            )

        tipos_desc = {
            "cpf": "CPF",
            "cnpj": "CNPJ",
            "email": "Email",
            "telefone": "Telefone",
            "aleatoria": "Chave Aleatória (EVP)",
        }

        return f"✅ Chave PIX válida.\nTipo: {tipos_desc[tipo]}\nChave: {chave}"

    @mcp.tool()
    async def calcular_juros_simples(
        principal: float,
        taxa_mensal: float,
        meses: int,
    ) -> str:
        """
        Calcula juros simples sobre um valor principal.

        Use quando precisar calcular juros de parcelamentos, empréstimos ou atrasos
        usando a fórmula: J = P × i × t.

        Parâmetros:
        - principal: valor original em reais (máx R$ 999.999.999)
        - taxa_mensal: taxa de juros mensal em % (ex: 2.5 para 2,5%)
        - meses: número de meses (máx 600)
        """
        if principal <= 0:
            return "❌ O valor principal deve ser maior que zero."
        if principal > _VALOR_MAXIMO:
            return f"❌ Valor excede o limite: R$ {principal:,.2f} (máx R$ 999.999.999)."
        if taxa_mensal < 0:
            return "❌ A taxa de juros não pode ser negativa."
        if taxa_mensal > 100:
            return f"❌ Taxa de juros muito alta: {taxa_mensal}% (máx 100%)."
        if meses < 0:
            return "❌ O número de meses não pode ser negativo."
        if meses > _MESES_MAXIMO:
            return f"❌ Limite excedido: {meses} meses (máx {_MESES_MAXIMO})."

        taxa_decimal = taxa_mensal / 100
        juros = principal * taxa_decimal * meses
        total = principal + juros

        return (
            f"✅ Juros Simples calculados:\n"
            f"Valor principal: R$ {principal:,.2f}\n"
            f"Taxa mensal: {taxa_mensal}%\n"
            f"Período: {meses} mês(es)\n"
            f"Juros: R$ {juros:,.2f}\n"
            f"Total a pagar: R$ {total:,.2f}"
        )

    @mcp.tool()
    async def calcular_juros_compostos(
        principal: float,
        taxa_mensal: float,
        meses: int,
    ) -> str:
        """
        Calcula juros compostos sobre um valor principal.

        Use quando precisar calcular juros de financiamentos, investimentos ou
        parcelamentos com juros sobre juros. Fórmula: M = P × (1 + i)^t.

        Parâmetros:
        - principal: valor original em reais (máx R$ 999.999.999)
        - taxa_mensal: taxa de juros mensal em % (ex: 2.5 para 2,5%)
        - meses: número de meses (máx 600)
        """
        if principal <= 0:
            return "❌ O valor principal deve ser maior que zero."
        if principal > _VALOR_MAXIMO:
            return f"❌ Valor excede o limite: R$ {principal:,.2f} (máx R$ 999.999.999)."
        if taxa_mensal < 0:
            return "❌ A taxa de juros não pode ser negativa."
        if taxa_mensal > 100:
            return f"❌ Taxa de juros muito alta: {taxa_mensal}% (máx 100%)."
        if meses < 0:
            return "❌ O número de meses não pode ser negativo."
        if meses > _MESES_MAXIMO:
            return f"❌ Limite excedido: {meses} meses (máx {_MESES_MAXIMO})."

        taxa_decimal = taxa_mensal / 100
        montante = principal * ((1 + taxa_decimal) ** meses)
        juros = montante - principal

        return (
            f"✅ Juros Compostos calculados:\n"
            f"Valor principal: R$ {principal:,.2f}\n"
            f"Taxa mensal: {taxa_mensal}%\n"
            f"Período: {meses} mês(es)\n"
            f"Juros: R$ {juros:,.2f}\n"
            f"Montante total: R$ {montante:,.2f}"
        )

    @mcp.tool()
    async def calcular_multa_atraso(
        valor: float,
        dias_atraso: int,
    ) -> str:
        """
        Calcula multa e juros de atraso no padrão brasileiro.

        Use quando precisar calcular o valor atualizado de uma conta ou boleto em atraso.
        Padrão: multa de 2% + juros de 1% ao mês proporcional aos dias de atraso.

        Parâmetros:
        - valor: valor original em reais (máx R$ 999.999.999)
        - dias_atraso: número de dias em atraso (máx 3650)
        """
        if valor <= 0:
            return "❌ O valor deve ser maior que zero."
        if valor > _VALOR_MAXIMO:
            return f"❌ Valor excede o limite: R$ {valor:,.2f} (máx R$ 999.999.999)."
        if dias_atraso < 0:
            return "❌ Os dias de atraso não podem ser negativos."
        if dias_atraso > _DIAS_ATRASO_MAXIMO:
            return f"❌ Limite excedido: {dias_atraso} dias (máx {_DIAS_ATRASO_MAXIMO})."

        if dias_atraso == 0:
            return (
                f"✅ Sem atraso — valor original: R$ {valor:,.2f}"
            )

        multa = valor * 0.02
        juros_mensal = 0.01
        juros = valor * juros_mensal * (dias_atraso / 30)
        total = valor + multa + juros

        return (
            f"✅ Cálculo de atraso:\n"
            f"Valor original: R$ {valor:,.2f}\n"
            f"Dias em atraso: {dias_atraso}\n"
            f"Multa (2%): R$ {multa:,.2f}\n"
            f"Juros (1%/mês pro rata): R$ {juros:,.2f}\n"
            f"Total atualizado: R$ {total:,.2f}"
        )


def _calcular_crc16(payload: str) -> str:
    """Calcula CRC16-CCITT (polinômio 0x1021) para payload PIX EMV."""
    crc = 0xFFFF
    for char in payload:
        crc ^= ord(char) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return format(crc, '04X')

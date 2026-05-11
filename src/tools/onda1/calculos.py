"""Ferramentas de cálculo — desconto, comissão, IMC, reajuste."""

from typing import Annotated
from pydantic import Field
from mcp.server.fastmcp import FastMCP


def calcular_desconto(valor: float, desconto_percentual: float) -> dict:
    """Calcula valor final após desconto.

    Use para calcular preços com desconto em promoções.
    Ex: calcular_desconto(100, 10) → valor_final=90, desconto=10
    """
    if valor <= 0:
        return {"erro": "❌ Valor deve ser maior que zero.\nDica: use um número positivo."}
    if desconto_percentual < 0:
        return {"erro": "❌ Desconto negativo não é válido.\nDica: use 0 para sem desconto."}
    if desconto_percentual > 100:
        return {"erro": "❌ Desconto maior que 100% não faz sentido.\nDica: use um valor entre 0 e 100."}

    desconto_valor = round(valor * (desconto_percentual / 100), 2)
    valor_final = round(valor - desconto_valor, 2)
    economia = f"{desconto_percentual}% de desconto = R$ {desconto_valor:,.2f}"

    return {
        "valor_original": valor,
        "desconto_valor": desconto_valor,
        "valor_final": valor_final,
        "economia": economia
    }


def calcular_comissao(valor: float, percentual: float) -> dict:
    """Calcula comissão percentual sobre valor.

    Use para calcular comissões de representantes comerciais ou prestadores.
    Percentual acima de 100% gera aviso (não é erro).
    """
    if valor <= 0:
        return {"erro": "❌ Valor deve ser maior que zero.\nDica: use um número positivo."}
    if percentual < 0:
        return {"erro": "❌ Percentual negativo não é válido.\nDica: use 0 ou mais."}

    comissao = round(valor * (percentual / 100), 2)
    total = round(valor + comissao, 2)

    result = {
        "valor_base": valor,
        "comissao": comissao,
        "total": total
    }

    if percentual > 100:
        result["aviso"] = "Percentual acima de 100% - verificar se está correto"

    return result


def calcular_imc(peso_kg: float, altura_m: float) -> dict:
    """Calcula IMC e classificação OMS em PT-BR.

    Use para avaliações de saúde em clínicas, academias, seguros.
    Classificações: abaixo do peso, peso normal, sobrepeso, obesidade grau I/II/III.
    """
    if peso_kg <= 0 or altura_m <= 0:
        return {"erro": "❌ Peso e altura devem ser maiores que zero.\nDica: peso em kg, altura em metros."}

    imc = round(peso_kg / (altura_m ** 2), 1)

    if imc < 18.5:
        classificacao = "abaixo do peso"
    elif imc < 25:
        classificacao = "peso normal"
    elif imc < 30:
        classificacao = "sobrepeso"
    elif imc < 35:
        classificacao = "obesidade grau I"
    elif imc < 40:
        classificacao = "obesidade grau II"
    else:
        classificacao = "obesidade grau III"

    return {"imc": imc, "classificacao": classificacao}


def calcular_reajuste_inflacao(valor: float, percentual_reajuste: float) -> dict:
    """Calcula valor com reajuste percentual (IPCA ou IGP-M).

    Use para atualizar valores de contratos, aluguel, mensalidades.
    Percentual pode ser negativo (deflação).
    Não busca índice — recebe percentual já calculado.
    """
    if valor <= 0:
        return {"erro": "❌ Valor deve ser maior que zero.\nDica: use um número positivo."}

    reajuste = round(valor * (percentual_reajuste / 100), 2)
    valor_final = round(valor + reajuste, 2)

    return {
        "valor_original": valor,
        "reajuste": reajuste,
        "valor_final": valor_final
    }


def register_tools(mcp: FastMCP) -> None:
    """Registra ferramentas de cálculo no servidor MCP."""

    @mcp.tool()
    async def calcular_desconto_tool(
        valor: Annotated[float, Field(description="Valor original (R$)")],
        desconto_percentual: Annotated[float, Field(description="Percentual de desconto (0-100)")],
    ) -> str:
        """Calcula valor final após desconto.

        Use para calcular preços com desconto em promoções.
        """
        result = calcular_desconto(valor, desconto_percentual)

        if "erro" in result:
            return result["erro"]

        return (
            f"✅ Desconto calculado:\n"
            f"Valor original: R$ {result['valor_original']:,.2f}\n"
            f"Desconto ({desconto_percentual}%): R$ {result['desconto_valor']:,.2f}\n"
            f"Valor final: R$ {result['valor_final']:,.2f}\n"
            f"{result['economia']}"
        )

    @mcp.tool()
    async def calcular_comissao_tool(
        valor: Annotated[float, Field(description="Valor base (R$)")],
        percentual: Annotated[float, Field(description="Percentual da comissão (0-100+)")],
    ) -> str:
        """Calcula comissão percentual sobre valor.

        Use para calcular comissões de representantes comerciais.
        """
        result = calcular_comissao(valor, percentual)

        if "erro" in result:
            return result["erro"]

        msg = (
            f"✅ Comissão calculada:\n"
            f"Valor base: R$ {result['valor_base']:,.2f}\n"
            f"Comissão ({percentual}%): R$ {result['comissao']:,.2f}\n"
            f"Total: R$ {result['total']:,.2f}"
        )

        if "aviso" in result:
            msg += f"\n⚠️ {result['aviso']}"

        return msg

    @mcp.tool()
    async def calcular_imc_tool(
        peso_kg: Annotated[float, Field(description="Peso em kg")],
        altura_m: Annotated[float, Field(description="Altura em metros (ex: 1.75)")],
    ) -> str:
        """Calcula IMC e classificação OMS em PT-BR.

        Use para avaliações de saúde em clínicas, academias, seguros.
        """
        result = calcular_imc(peso_kg, altura_m)

        if "erro" in result:
            return result["erro"]

        return (
            f"✅ IMC calculado:\n"
            f"IMC: {result['imc']}\n"
            f"Classificação: {result['classificacao']}"
        )

    @mcp.tool()
    async def calcular_reajuste_inflacao_tool(
        valor: Annotated[float, Field(description="Valor original (R$)")],
        percentual_reajuste: Annotated[float, Field(description="Percentual de reajuste (pode ser negativo)")],
    ) -> str:
        """Calcula valor com reajuste percentual (IPCA ou IGP-M).

        Use para atualizar valores de contratos, aluguel, mensalidades.
        """
        result = calcular_reajuste_inflacao(valor, percentual_reajuste)

        if "erro" in result:
            return result["erro"]

        sinal = "+" if percentual_reajuste >= 0 else ""
        return (
            f"✅ Reajuste calculado:\n"
            f"Valor original: R$ {result['valor_original']:,.2f}\n"
            f"Reajuste ({sinal}{percentual_reajuste}%): R$ {result['reajuste']:,.2f}\n"
            f"Valor final: R$ {result['valor_final']:,.2f}"
        )
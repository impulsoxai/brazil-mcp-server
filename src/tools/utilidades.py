"""Módulo de utilidades — moeda, telefone, banco, DDD."""

import sys
from mcp.server.fastmcp import FastMCP

from src.utils.validators import limpar_numeros
from src.utils.formatters import formatar_telefone_br
from src.utils import http_client
from src.config import BRASIL_API_BASE, AWESOME_API_BASE


# Mapa completo DDD → estado
_DDD_ESTADOS = {
    "11": "São Paulo", "12": "São Paulo", "13": "São Paulo", "14": "São Paulo",
    "15": "São Paulo", "16": "São Paulo", "17": "São Paulo", "18": "São Paulo",
    "19": "São Paulo",
    "21": "Rio de Janeiro", "22": "Rio de Janeiro", "24": "Rio de Janeiro",
    "27": "Espírito Santo", "28": "Espírito Santo",
    "31": "Minas Gerais", "32": "Minas Gerais", "33": "Minas Gerais",
    "34": "Minas Gerais", "35": "Minas Gerais", "37": "Minas Gerais",
    "38": "Minas Gerais",
    "41": "Paraná", "42": "Paraná", "43": "Paraná", "44": "Paraná",
    "45": "Paraná", "46": "Paraná",
    "47": "Santa Catarina", "48": "Santa Catarina", "49": "Santa Catarina",
    "51": "Rio Grande do Sul", "53": "Rio Grande do Sul", "54": "Rio Grande do Sul",
    "55": "Rio Grande do Sul",
    "61": "Distrito Federal / Goiás",
    "62": "Goiás", "64": "Goiás",
    "63": "Tocantins",
    "65": "Mato Grosso", "66": "Mato Grosso",
    "67": "Mato Grosso do Sul",
    "68": "Acre", "69": "Rondônia",
    "71": "Bahia", "73": "Bahia", "74": "Bahia", "75": "Bahia", "77": "Bahia",
    "79": "Sergipe",
    "81": "Pernambuco", "87": "Pernambuco",
    "82": "Alagoas",
    "83": "Paraíba",
    "84": "Rio Grande do Norte",
    "85": "Ceará", "88": "Ceará",
    "86": "Piauí", "89": "Piauí",
    "91": "Pará", "93": "Pará", "94": "Pará",
    "92": "Amazonas", "97": "Amazonas",
    "95": "Roraima",
    "96": "Amapá",
    "98": "Maranhão", "99": "Maranhão",
}


def register_tools(mcp: FastMCP) -> None:
    """Registra as ferramentas de utilidades no servidor MCP."""

    @mcp.tool()
    async def converter_moeda(valor: float, de: str, para: str) -> str:
        """
        Converte um valor entre moedas usando cotação em tempo real.

        Use quando precisar converter BRL para outra moeda ou entre moedas estrangeiras.
        Consulta a AwesomeAPI em tempo real.
        Exemplos: converter_moeda(100, "BRL", "USD"), converter_moeda(50, "USD", "BRL")

        Parâmetros:
        - valor: valor a converter (ex: 100.00)
        - de: moeda de origem (ex: "BRL", "USD", "EUR")
        - para: moeda de destino (ex: "USD", "BRL", "EUR")
        """
        de = de.strip().upper()
        para = para.strip().upper()

        if valor <= 0:
            return "❌ O valor deve ser maior que zero."

        if de == para:
            return f"✅ Conversão: {de} = {para}.\nValor: {valor:.2f} (mesma moeda, sem conversão)."

        try:
            url = f"{AWESOME_API_BASE}/last/{de}-{para}"
            response = await http_client.get(url)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Erro ao converter moeda: {e}", file=sys.stderr)
            return (
                f"❌ Erro ao consultar cotação {de}/{para}.\n"
                "Dica: verifique se os códigos de moeda são válidos (ex: BRL, USD, EUR)."
            )

        # A API retorna a chave como "{de}{para}"
        chave = f"{de}{para}"
        if chave not in data:
            return (
                f"❌ Par de moedas não encontrado: {de}/{para}.\n"
                "Dica: verifique se os códigos são válidos."
            )

        cotacao_info = data[chave]
        taxa = float(cotacao_info.get("bid", 0))
        if taxa <= 0:
            return f"❌ Cotação inválida para {de}/{para}."

        convertido = valor * taxa

        return (
            f"✅ Conversão realizada:\n"
            f"Valor original: {valor:,.2f} {de}\n"
            f"Cotação: 1 {de} = {taxa:,.4f} {para}\n"
            f"Valor convertido: {convertido:,.2f} {para}"
        )

    @mcp.tool()
    async def validar_telefone_br(telefone: str) -> str:
        """
        Valida se um telefone é um número brasileiro válido.

        Aceita formatos com ou sem DDD, com ou sem formatação.
        Valida: DDD (11-99), tamanho (10 fixo, 11 celular) e dígito inicial do celular (9).
        """
        numeros = limpar_numeros(telefone)

        if not numeros:
            return "❌ Telefone vazio. Informe o número com DDD."

        # Remover código do país se presente
        if numeros.startswith("55") and len(numeros) in (12, 13):
            numeros = numeros[2:]

        if len(numeros) not in (10, 11):
            return (
                f"❌ Telefone inválido: '{telefone}' ({len(limpar_numeros(telefone))} dígitos).\n"
                "Dica: telefone fixo tem 10 dígitos, celular tem 11 dígitos (com o 9)."
            )

        ddd = numeros[:2]
        if int(ddd) < 11 or int(ddd) > 99:
            return (
                f"❌ DDD inválido: {ddd}.\n"
                "Dica: DDDs brasileiros vão de 11 a 99."
            )

        if len(numeros) == 11 and numeros[2] != "9":
            return (
                f"❌ Celular inválido: o terceiro dígito deve ser 9.\n"
                "Dica: números de celular brasileiros começam com 9 após o DDD."
            )

        estado = _DDD_ESTADOS.get(ddd, "Desconhecido")
        telefone_fmt = formatar_telefone_br(numeros)
        tipo = "Celular" if len(numeros) == 11 else "Fixo"

        return (
            f"✅ Telefone válido.\n"
            f"Número: {telefone_fmt}\n"
            f"Tipo: {tipo}\n"
            f"DDD: {ddd} — {estado}"
        )

    @mcp.tool()
    async def formatar_telefone_br_tool(telefone: str) -> str:
        """
        Formata um telefone brasileiro com máscara e DDD.

        Celular (11 dígitos): (XX) XXXXX-XXXX
        Fixo (10 dígitos): (XX) XXXX-XXXX
        """
        numeros = limpar_numeros(telefone)

        # Remover código do país se presente
        if numeros.startswith("55") and len(numeros) in (12, 13):
            numeros = numeros[2:]

        if len(numeros) not in (10, 11):
            return (
                f"❌ Telefone inválido: '{telefone}'.\n"
                "Dica: informe com DDD (10 ou 11 dígitos)."
            )

        telefone_fmt = formatar_telefone_br(numeros)
        tipo = "Celular" if len(numeros) == 11 else "Fixo"

        return f"✅ Telefone formatado: {telefone_fmt} ({tipo})"

    @mcp.tool()
    async def buscar_banco_por_codigo(codigo: str) -> str:
        """
        Busca dados de um banco brasileiro pelo código COMPE.

        Use quando precisar identificar um banco pelo código (ex: 001 = Banco do Brasil,
        341 = Itaú, 237 = Bradesco). Consulta a BrasilAPI em tempo real.
        """
        codigo = limpar_numeros(codigo)

        if not codigo:
            return "❌ Código do banco é obrigatório. Ex: 001, 341, 237."

        try:
            url = f"{BRASIL_API_BASE}/banks/v1/{codigo}"
            response = await http_client.get(url)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Erro ao buscar banco: {e}", file=sys.stderr)
            return (
                f"❌ Banco com código '{codigo}' não encontrado.\n"
                "Dica: verifique se o código COMPE está correto (ex: 001, 341, 237)."
            )

        nome = data.get("name", data.get("fullName", "Não informado"))
        codigo_compe = data.get("code", data.get("ispb", codigo))
        ispb = data.get("ispb", "Não informado")

        return (
            f"✅ Banco encontrado:\n"
            f"Código COMPE: {codigo_compe}\n"
            f"Nome: {nome}\n"
            f"ISPB: {ispb}"
        )

    @mcp.tool()
    async def listar_ddd_estados() -> str:
        """
        Retorna o mapa completo de DDDs para estados brasileiros.

        Use quando precisar identificar a região de um DDD ou listar todos os DDDs.
        Retorna todos os 67 DDDs do Brasil organizados por estado.
        """
        # Organizar por região para melhor leitura
        regioes = {
            "Sudeste": ["SP", "RJ", "MG", "ES"],
            "Sul": ["PR", "SC", "RS"],
            "Centro-Oeste": ["DF", "GO", "MT", "MS"],
            "Nordeste": ["BA", "SE", "PE", "AL", "PB", "RN", "CE", "PI", "MA"],
            "Norte": ["PA", "AM", "RR", "AP", "TO", "RO", "AC"],
        }

        # Mapear DDDs por estado
        estado_ddds: dict[str, list[str]] = {}
        for ddd, estado in _DDD_ESTADOS.items():
            estado_ddds.setdefault(estado, []).append(ddd)

        linhas = []
        for estado, ddds in sorted(estado_ddds.items()):
            ddds_fmt = ", ".join(sorted(ddds))
            linhas.append(f"  • {estado}: {ddds_fmt}")

        return (
            f"✅ Mapa de DDDs do Brasil ({len(_DDD_ESTADOS)} DDDs):\n\n"
            + "\n".join(linhas)
        )

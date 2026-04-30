"""Módulo de endereço — CEP, logradouro, coordenadas."""

import sys
import httpx
from mcp.server.fastmcp import FastMCP

from src.utils.validators import limpar_numeros
from src.utils.formatters import formatar_cep, formatar_endereco
from src.utils import http_client
from src.config import BRASIL_API_BASE


def _sanitizar_input(valor: str, max_len: int = 500) -> str:
    """Trunca e remove caracteres de controle de uma string."""
    return valor[:max_len].strip()


def register_tools(mcp: FastMCP) -> None:
    """Registra as ferramentas de endereço no servidor MCP."""

    @mcp.tool()
    async def buscar_endereco_por_cep(cep: str) -> str:
        """
        Busca endereço completo a partir de um CEP brasileiro.

        Use quando precisar obter logradouro, bairro, cidade e estado de um CEP.
        Aceita CEP com ou sem formatação (8 dígitos ou XXXXX-XXX).
        Consulta a BrasilAPI em tempo real.
        """
        cep = _sanitizar_input(cep)
        cep_limpo = limpar_numeros(cep)

        if len(cep_limpo) != 8:
            return (
                f"❌ CEP inválido: esperados 8 dígitos, recebidos {len(cep_limpo)}.\n"
                "Dica: verifique se digitou o CEP completo."
            )

        try:
            response = await http_client.get(f"{BRASIL_API_BASE}/cep/v1/{cep_limpo}")
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Erro ao consultar CEP: {e}", file=sys.stderr)
            return (
                "❌ Erro ao consultar o CEP na base de dados.\n"
                "Dica: tente novamente em alguns segundos ou verifique se o CEP existe."
            )

        cep_formatado = formatar_cep(cep_limpo)
        logradouro = data.get("street", data.get("logradouro", ""))
        bairro = data.get("neighborhood", data.get("bairro", ""))
        cidade = data.get("city", data.get("localidade", ""))
        uf = data.get("state", data.get("uf", ""))

        endereco = formatar_endereco(
            logradouro=logradouro,
            bairro=bairro,
            cidade=cidade,
            uf=uf,
            cep=cep_limpo,
        )

        return (
            f"✅ CEP {cep_formatado} encontrado:\n"
            f"Logradouro: {logradouro or 'Não informado'}\n"
            f"Bairro: {bairro or 'Não informado'}\n"
            f"Cidade: {cidade or 'Não informado'}\n"
            f"UF: {uf or 'Não informado'}\n"
            f"Endereço completo: {endereco or 'Não informado'}"
        )

    @mcp.tool()
    async def buscar_ceps_por_logradouro(logradouro: str, cidade: str, uf: str = "") -> str:
        """
        Busca CEPs por nome de logradouro e cidade.

        Use quando o usuário sabe o nome da rua mas não o CEP.
        Retorna uma lista de CEPs correspondentes.
        Consulta a ViaCEP em tempo real.

        Parâmetros:
        - logradouro: nome da rua (ex: "Paulista")
        - cidade: nome da cidade (ex: "São Paulo")
        - uf: sigla do estado opcional (ex: "SP") — melhora a precisão da busca
        """
        logradouro = _sanitizar_input(logradouro, 200)
        cidade = _sanitizar_input(cidade, 100)
        uf = _sanitizar_input(uf, 10).upper()

        if not logradouro or not cidade:
            return (
                "❌ Parâmetros obrigatórios: logradouro e cidade.\n"
                "Dica: informe o nome da rua e a cidade para buscar os CEPs."
            )

        # ViaCEP: /ws/{UF}/{cidade}/{logradouro}/json/
        cidade_encoded = cidade.replace(" ", "%20")
        logradouro_encoded = logradouro.replace(" ", "%20")

        if uf:
            url = f"https://viacep.com.br/ws/{uf}/{cidade_encoded}/{logradouro_encoded}/json/"
        else:
            # Sem UF, tentar com cidade e logradouro apenas
            url = f"https://viacep.com.br/ws/{cidade_encoded}/{logradouro_encoded}/json/"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            print(f"Erro ao buscar CEPs ViaCEP: {type(e).__name__}: {e}", file=sys.stderr)
            return (
                f"❌ Erro ao buscar CEPs: {type(e).__name__}.\n"
                "Dica: tente novamente ou informe o UF para melhorar a busca (ex: SP)."
            )

        if not data or (isinstance(data, list) and len(data) == 0):
            return (
                f"❌ Nenhum CEP encontrado para '{logradouro}' em {cidade}.\n"
                "Dica: verifique se o nome da rua e a cidade estão corretos."
            )

        if isinstance(data, dict) and data.get("erro"):
            return (
                f"❌ Nenhum CEP encontrado para '{logradouro}' em {cidade}.\n"
                "Dica: verifique se o nome da rua e a cidade estão corretos."
            )

        results = []
        for item in (data if isinstance(data, list) else [data])[:10]:
            cep = item.get("cep", "")
            street = item.get("logradouro", "")
            neighborhood = item.get("bairro", "")
            results.append(f"  • {formatar_cep(cep)} — {street} ({neighborhood})")

        return (
            f"✅ CEPs encontrados para '{logradouro}' em {cidade}:\n"
            + "\n".join(results)
        )

    @mcp.tool()
    async def formatar_endereco_completo(
        logradouro: str,
        cidade: str,
        uf: str,
        numero: str = "",
        complemento: str = "",
        bairro: str = "",
        cep: str = "",
    ) -> str:
        """
        Formata um endereço brasileiro completo em string legível.

        Use quando precisar exibir um endereço de forma organizada.
        Parâmetros obrigatórios: logradouro, cidade, uf.
        """
        logradouro = _sanitizar_input(logradouro, 300)
        cidade = _sanitizar_input(cidade, 100)
        uf = _sanitizar_input(uf, 10)
        numero = _sanitizar_input(numero, 20)
        complemento = _sanitizar_input(complemento, 100)
        bairro = _sanitizar_input(bairro, 100)
        cep = _sanitizar_input(cep, 20)

        if not logradouro or not cidade or not uf:
            return (
                "❌ Parâmetros obrigatórios: logradouro, cidade e uf.\n"
                "Dica: informe pelo menos esses três campos."
            )

        endereco = formatar_endereco(
            logradouro=logradouro,
            numero=numero,
            complemento=complemento,
            bairro=bairro,
            cidade=cidade,
            uf=uf.upper(),
            cep=cep,
        )

        return f"✅ Endereço formatado:\n{endereco}"

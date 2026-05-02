"""Módulo de identidade — CNPJ, CPF, validações."""

import sys
from typing import Annotated

from pydantic import Field
from mcp.server.fastmcp import FastMCP

from src.utils.validators import limpar_numeros, validar_cpf, validar_cnpj, sanitizar_input
from src.utils.formatters import formatar_cpf, formatar_cnpj, formatar_cep
from src.utils import http_client
from src.config import BRASIL_API_BASE


def register_tools(mcp: FastMCP) -> None:
    """Registra as ferramentas de identidade no servidor MCP."""

    @mcp.tool()
    async def consultar_cnpj(cnpj: Annotated[str, Field(description="CNPJ da empresa (com ou sem formatação, ex: 11.222.333/0001-81 ou 11222333000181)")]) -> str:
        """
        Consulta dados cadastrais completos de uma empresa brasileira pelo CNPJ.

        Use quando precisar verificar: razão social, nome fantasia, situação cadastral
        (ativa/inativa/suspensa), endereço completo, CNAE principal, porte da empresa,
        data de abertura e QSA (quadro de sócios).

        O CNPJ pode ser enviado com ou sem formatação (14 dígitos ou XX.XXX.XXX/XXXX-XX).
        Retorna erro descritivo se o CNPJ for inválido ou a empresa não for encontrada.
        """
        cnpj = sanitizar_input(cnpj)
        cnpj_limpo = limpar_numeros(cnpj)

        if not validar_cnpj(cnpj_limpo):
            return (
                f"❌ CNPJ inválido: o número '{cnpj}' não passa na validação matemática.\n"
                "Dica: verifique se digitou todos os 14 dígitos corretamente."
            )

        try:
            response = await http_client.get(f"{BRASIL_API_BASE}/cnpj/v1/{cnpj_limpo}")
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Erro ao consultar CNPJ {cnpj_limpo}: {type(e).__name__}: {e}", file=sys.stderr)
            return (
                f"❌ Erro ao consultar o CNPJ {cnpj} na base de dados.\n"
                "Dica: tente novamente em alguns segundos ou verifique sua conexão."
            )

        cnpj_formatado = formatar_cnpj(cnpj_limpo)
        situacao = data.get("situacao_cadastral", "Desconhecida")
        razao = data.get("razao_social", "Não informado")
        fantasia = data.get("nome_fantasia", "Não informado")
        cnae_desc = data.get("cnae_fiscal_descricao", "Não informado")
        cnae_cod = data.get("cnae_fiscal", "")
        abertura = data.get("data_abertura", "Não informado")
        porte = data.get("porte", "Não informado")

        logradouro = data.get("logradouro", "")
        numero = data.get("numero", "")
        complemento = data.get("complemento", "")
        bairro = data.get("bairro", "")
        municipio = data.get("municipio", "")
        uf = data.get("uf", "")
        cep = data.get("cep", "")

        endereco_parts = []
        if logradouro:
            parte = logradouro
            if numero:
                parte += f", {numero}"
            if complemento:
                parte += f" — {complemento}"
            endereco_parts.append(parte)
        if bairro:
            endereco_parts.append(bairro)
        if municipio and uf:
            endereco_parts.append(f"{municipio}/{uf}")
        if cep:
            endereco_parts.append(formatar_cep(cep) if len(limpar_numeros(cep)) == 8 else cep)
        endereco = " — ".join(endereco_parts) if endereco_parts else "Não informado"

        cnae = f"{cnae_cod} — {cnae_desc}" if cnae_cod else cnae_desc

        qsa = data.get("qsa", [])
        socios = ""
        if qsa:
            socios_lines = []
            for socio in qsa[:10]:
                nome = socio.get("nome_socio", "")
                qualificacao = socio.get("qualificacao_socio", "")
                if nome:
                    socios_lines.append(f"  • {nome} ({qualificacao})")
            if socios_lines:
                socios = "\nSócios:\n" + "\n".join(socios_lines)

        return (
            f"✅ CNPJ {cnpj_formatado} encontrado:\n"
            f"Razão Social: {razao}\n"
            f"Nome Fantasia: {fantasia}\n"
            f"Situação: {situacao}\n"
            f"CNAE: {cnae}\n"
            f"Porte: {porte}\n"
            f"Abertura: {abertura}\n"
            f"Endereço: {endereco}"
            f"{socios}"
        )

    @mcp.tool()
    async def validar_cnpj_tool(cnpj: Annotated[str, Field(description="CNPJ para validar (com ou sem formatação)")]) -> str:
        """
        Valida matematicamente um CNPJ brasileiro.

        Use para verificar se um CNPJ é válido sem consultar a base de dados.
        Aceita com ou sem formatação. Retorna se é válido e o CNPJ formatado.
        """
        cnpj = sanitizar_input(cnpj)
        cnpj_limpo = limpar_numeros(cnpj)
        cnpj_formatado = formatar_cnpj(cnpj_limpo)

        if validar_cnpj(cnpj_limpo):
            return f"✅ CNPJ {cnpj_formatado} é válido (passou na validação matemática)."
        else:
            return (
                f"❌ CNPJ '{cnpj}' é inválido.\n"
                "Dica: verifique se digitou todos os 14 dígitos corretamente."
            )

    @mcp.tool()
    async def validar_cpf_tool(cpf: Annotated[str, Field(description="CPF para validar (com ou sem formatação, ex: 529.982.247-25 ou 52998224725)")]) -> str:
        """
        Valida matematicamente um CPF brasileiro.

        Use para verificar se um CPF é válido sem consultar a base de dados.
        Aceita com ou sem formatação. Retorna se é válido e o CPF formatado.
        """
        cpf = sanitizar_input(cpf)
        cpf_limpo = limpar_numeros(cpf)
        cpf_formatado = formatar_cpf(cpf_limpo)

        if validar_cpf(cpf_limpo):
            return f"✅ CPF {cpf_formatado} é válido (passou na validação matemática)."
        else:
            return (
                f"❌ CPF '{cpf}' é inválido.\n"
                "Dica: verifique se digitou todos os 11 dígitos corretamente."
            )

    @mcp.tool()
    async def formatar_cpf_tool(cpf: Annotated[str, Field(description="CPF para formatar (apenas dígitos ou já formatado)")]) -> str:
        """
        Formata um CPF brasileiro com máscara.

        Use quando precisar exibir um CPF de forma legível.
        Entrada: '12345678901' → Saída: '123.456.789-01'
        """
        cpf = sanitizar_input(cpf)
        cpf_limpo = limpar_numeros(cpf)

        if len(cpf_limpo) != 11:
            return (
                f"❌ CPF inválido: esperados 11 dígitos, recebidos {len(cpf_limpo)}.\n"
                "Dica: verifique se digitou o CPF completo."
            )

        cpf_formatado = formatar_cpf(cpf_limpo)
        valido = "válido" if validar_cpf(cpf_limpo) else "inválido (matematicamente)"
        return f"✅ CPF formatado: {cpf_formatado} — {valido}"

    @mcp.tool()
    async def formatar_cnpj_tool(cnpj: Annotated[str, Field(description="CNPJ para formatar (apenas dígitos ou já formatado)")]) -> str:
        """
        Formata um CNPJ brasileiro com máscara.

        Use quando precisar exibir um CNPJ de forma legível.
        Entrada: '12345678000199' → Saída: '12.345.678/0001-99'
        """
        cnpj = sanitizar_input(cnpj)
        cnpj_limpo = limpar_numeros(cnpj)

        if len(cnpj_limpo) != 14:
            return (
                f"❌ CNPJ inválido: esperados 14 dígitos, recebidos {len(cnpj_limpo)}.\n"
                "Dica: verifique se digitou o CNPJ completo."
            )

        cnpj_formatado = formatar_cnpj(cnpj_limpo)
        valido = "válido" if validar_cnpj(cnpj_limpo) else "inválido (matematicamente)"
        return f"✅ CNPJ formatado: {cnpj_formatado} — {valido}"

"""Ferramentas de validação — email, senha, número extenso."""

import math
import secrets
import string
from typing import Annotated
from pydantic import Field
from mcp.server.fastmcp import FastMCP


_TYPO_DOMINIOS = {
    "gmai.com": "gmail.com",
    "gmal.com": "gmail.com",
    "hotmal.com": "hotmail.com",
    "hotmial.com": "hotmail.com",
    "yaho.com": "yahoo.com.br",
}


def validar_email_br(email: str) -> dict:
    """Valida email com sugestões para domínios brasileiros errados.

    Use para verificar formato de email antes de salvar contato do cliente.
    Detecta typos em domínios comuns (gmai.com → gmail.com).
    """
    email = email.strip()[:254]

    if not email or "@" not in email:
        return {"valido": False, "dominio": "", "sugestao": None}

    partes = email.split("@")
    if len(partes) != 2 or not partes[0] or not partes[1]:
        return {"valido": False, "dominio": "", "sugestao": None}

    dominio = partes[1].lower()

    if len(dominio) < 3 or "." not in dominio:
        return {"valido": False, "dominio": "", "sugestao": None}

    valido = True
    sugestao = None

    if dominio in _TYPO_DOMINIOS:
        valido = False
        sugestao = _TYPO_DOMINIOS[dominio]

    return {"valido": valido, "dominio": dominio, "sugestao": sugestao}


def gerar_senha_segura(
    tamanho: Annotated[int, Field(description="Tamanho da senha (4-128)", default=16)] = 16,
    incluir_simbolos: Annotated[bool, Field(description="Incluir símbolos (!@#$%...)", default=True)] = True,
    incluir_numeros: Annotated[bool, Field(description="Incluir números", default=True)] = True,
    incluir_maiusculas: Annotated[bool, Field(description="Incluir maiúsculas (A-Z)", default=True)] = True,
) -> dict:
    """Gera senha aleatória com nível de segurança.

    Use para criar senhas seguras para usuários ou sistemas.
    Níveis: fraca (<40 bits entropia), média (40-60), forte (60-80), muito forte (>80).
    """
    if tamanho < 4:
        return {"erro": "Tamanho mínimo é 4 caracteres.\nDica: use tamanho >= 4."}
    if tamanho > 128:
        return {"erro": "Tamanho máximo é 128 caracteres.\nDica: use tamanho <= 128."}

    chars = ""
    if incluir_simbolos:
        chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if incluir_numeros:
        chars += string.digits
    if incluir_maiusculas:
        chars += string.ascii_uppercase

    chars += string.ascii_lowercase

    if not chars:
        return {"erro": "Pool de caracteres vazio.\nDica: selecione pelo menos um tipo de caractere."}

    senha = "".join(secrets.choice(chars) for _ in range(tamanho))

    bits = round(tamanho * math.log2(len(chars)))

    if bits < 40:
        nivel = "fraca"
    elif bits < 60:
        nivel = "media"
    elif bits < 80:
        nivel = "forte"
    else:
        nivel = "muito forte"

    return {"senha": senha, "nivel_seguranca": nivel}


def converter_numero_extenso(
    valor: Annotated[float, Field(description="Valor a converter")],
    moeda: Annotated[str, Field(description="Moeda (padrão BRL)", default="BRL")] = "BRL",
) -> str:
    """Converte número float para extenso em PT-BR (BRL).

    Use para converter valores monetários em texto por extenso (notas fiscais, contratos).
    Ex: 1234.56 → 'um mil duzentos e trinta e quatro reais e cinquenta e seis centavos'
    """
    from num2words import num2words

    if valor < 0:
        return "❌ Valor negativo não é válido para conversão.\nDica: use um número positivo."

    if valor > 1e15:
        return "❌ Valor muito alto para conversão por extenso.\nDica: máximo suportado é R$ 1.000.000.000.000.000,00 (um quadrilhão)."

    if valor == 0:
        if moeda.upper() == "BRL":
            return "zero reais"
        return num2words(0, lang="pt_BR")

    reais = int(valor)
    centavos = int(round((valor - reais) * 100))

    extenso_reais = num2words(reais, to="cardinal", lang="pt_BR")
    extenso_centavos = num2words(centavos, to="cardinal", lang="pt_BR")

    if reais == 1 and centavos == 0:
        return "um real"
    elif reais == 0 and centavos == 1:
        return "um centavo"
    elif centavos == 0:
        return f"{extenso_reais} reais"
    else:
        return f"{extenso_reais} reais e {extenso_centavos} centavos"


def register_tools(mcp: FastMCP) -> None:
    """Registra ferramentas de validação no servidor MCP."""
    @mcp.tool()
    async def validar_email_br_tool(email: Annotated[str, Field(description="Email para validar")]) -> str:
        """Valida formato de email com sugestões para domínios brasileiros errados.

        Use para verificar email antes de salvar contato do cliente.
        Detecta typos: gmai.com → gmail.com, hotmal.com → hotmail.com.
        """
        result = validar_email_br(email)

        if not result["valido"]:
            msg = f"❌ Email inválido: '{email}'"
            if result["sugestao"]:
                msg += f"\nDica: você quis dizer '{result['sugestao']}'?"
            return msg

        return f"✅ Email válido.\nDomínio: {result['dominio']}"

    @mcp.tool()
    async def gerar_senha_segura_tool(
        tamanho: Annotated[int, Field(description="Tamanho da senha (4-128)", default=16)] = 16,
        incluir_simbolos: Annotated[bool, Field(description="Incluir símbolos (!@#$%...)", default=True)] = True,
        incluir_numeros: Annotated[bool, Field(description="Incluir números", default=True)] = True,
        incluir_maiusculas: Annotated[bool, Field(description="Incluir maiúsculas (A-Z)", default=True)] = True,
    ) -> str:
        """Gera senha aleatória com nível de segurança.

        Use para criar senhas seguras para usuários ou sistemas.
        Níveis: fraca, média, forte, muito forte.
        """
        result = gerar_senha_segura(tamanho, incluir_simbolos, incluir_numeros, incluir_maiusculas)

        if "erro" in result:
            return f"❌ {result['erro']}"

        return f"✅ Senha gerada:\n`{result['senha']}`\nNível: {result['nivel_seguranca']}"

    @mcp.tool()
    async def converter_numero_extenso_tool(
        valor: Annotated[float, Field(description="Valor a converter")],
        moeda: Annotated[str, Field(description="Moeda (padrão BRL)", default="BRL")] = "BRL",
    ) -> str:
        """Converte número float para extenso em PT-BR (BRL).

        Use para converter valores monetários em texto por extenso.
        Ex: 1234.56 → 'um mil duzentos e trinta e quatro reais e cinquenta e seis centavos'
        """
        result = converter_numero_extenso(valor, moeda)
        if result.startswith("❌"):
            return result
        return f"✅ {result}"
"""Códigos de erro padronizados para o Brazil MCP Server."""

from enum import Enum


class CodigoErro(str, Enum):
    """Códigos de erro padronizados."""
    ENTRADA_INVALIDA = "ENTRADA_INVALIDA"
    API_EXTERNA_INDISPONIVEL = "API_EXTERNA_INDISPONIVEL"
    LIMITE_EXCEDIDO = "LIMITE_EXCEDIDO"
    NAO_ENCONTRADO = "NAO_ENCONTRADO"
    ERRO_INTERNO = "ERRO_INTERNO"


def formatar_erro(codigo: CodigoErro, detalhe: str, dica: str) -> str:
    """
    Formata mensagem de erro no padrão do servidor.

    Formato: "❌ [CODIGO] Mensagem.\nDica: orientação."
    """
    return f"❌ [{codigo.value}] {detalhe}.\nDica: {dica}"


def erro_entrada_invalida(detalhe: str, dica: str) -> str:
    """Retorna erro de entrada do usuário."""
    return formatar_erro(CodigoErro.ENTRADA_INVALIDA, detalhe, dica)


def erro_api_indisponivel(detalhe: str, dica: str = "tente novamente em alguns segundos") -> str:
    """Retorna erro de API externa indisponível."""
    return formatar_erro(CodigoErro.API_EXTERNA_INDISPONIVEL, detalhe, dica)


def erro_limite_excedido(detalhe: str, dica: str) -> str:
    """Retorna erro de limite excedido."""
    return formatar_erro(CodigoErro.LIMITE_EXCEDIDO, detalhe, dica)


def erro_nao_encontrado(detalhe: str, dica: str) -> str:
    """Retorna erro de item não encontrado."""
    return formatar_erro(CodigoErro.NAO_ENCONTRADO, detalhe, dica)


def erro_interno(detalhe: str = "erro inesperado", dica: str = "tente novamente") -> str:
    """Retorna erro interno do servidor."""
    return formatar_erro(CodigoErro.ERRO_INTERNO, detalhe, dica)

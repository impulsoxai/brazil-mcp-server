"""Testes para o middleware de autenticacao e rate limiting."""

import pytest
from src.middleware.auth import verificar_autenticacao
from src.middleware.rate_limit import verificar_rate_limit, verificar_limite_mensal
from src.services import usage


@pytest.fixture(autouse=True)
def setup_usage():
    """Initialize usage service with test keys."""
    usage.init()
    # Ensure test key exists
    if not usage.validate_key("test-key-free"):
        usage.create_key("test-key-free", "free")
    if not usage.validate_key("test-key-starter"):
        usage.create_key("test-key-starter", "starter")
    yield
    # Reset usage for test keys
    for key in ["test-key-free", "test-key-starter"]:
        data = usage.validate_key(key)
        if data:
            data["usage"] = 0


class TestVerificarAutenticacao:
    def test_sem_header_retorna_invalido(self):
        resultado = verificar_autenticacao({})
        assert resultado["valid"] is False
        assert resultado["error"] == "Invalid or missing API key"

    def test_header_vazio_retorna_invalido(self):
        resultado = verificar_autenticacao({"x-api-key": ""})
        assert resultado["valid"] is False

    def test_header_espacos_retorna_invalido(self):
        resultado = verificar_autenticacao({"x-api-key": "   "})
        assert resultado["valid"] is False

    def test_chave_invalida_retorna_invalido(self):
        resultado = verificar_autenticacao({"x-api-key": "chave-que-nao-existe"})
        assert resultado["valid"] is False

    def test_chave_valida_retorna_valido(self):
        resultado = verificar_autenticacao({"x-api-key": "test-key-free"})
        assert resultado["valid"] is True
        assert resultado["api_key"] == "test-key-free"
        assert resultado["plan"] == "free"

    def test_chave_starter_retorna_starter(self):
        resultado = verificar_autenticacao({"x-api-key": "test-key-starter"})
        assert resultado["valid"] is True
        assert resultado["plan"] == "starter"


class TestRateLimit:
    def test_primeira_requisicao_permitida(self):
        resultado = verificar_rate_limit("test-key-free")
        assert resultado["allowed"] is True
        assert resultado["count"] >= 1

    def test_limite_mensal_permitido(self):
        resultado = verificar_limite_mensal("test-key-free")
        assert resultado["allowed"] is True
        assert resultado["limit"] == 2000
        assert resultado["remaining"] >= 0

    def test_chave_invalida_bloqueada(self):
        resultado = verificar_rate_limit("chave-inexistente")
        assert resultado["allowed"] is False

    def test_limite_mensal_chave_invalida(self):
        resultado = verificar_limite_mensal("chave-inexistente")
        assert resultado["allowed"] is False

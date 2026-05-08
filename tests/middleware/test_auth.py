"""Testes para o middleware de autenticacao e rate limiting."""

import pytest
from unittest.mock import AsyncMock, patch
from src.middleware.auth import verificar_autenticacao
from src.middleware.rate_limit import verificar_rate_limit, verificar_limite_mensal
from src.services import database as usage


@pytest.fixture(autouse=True)
async def setup_usage():
    """Initialize usage service with test keys using mocks."""
    with patch("src.middleware.auth.usage") as mock_auth_usage, \
         patch("src.middleware.rate_limit.usage") as mock_rl_usage:
        # Setup mock return values
        mock_auth_usage.validate_key = AsyncMock(side_effect=lambda k: {
            "test-key-free": {"plan": "free", "scope": "public", "usage": 0, "reset_date": "2099-01-01T00:00:00+00:00"},
            "test-key-starter": {"plan": "starter", "scope": "public", "usage": 0, "reset_date": "2099-01-01T00:00:00+00:00"},
        }.get(k))

        mock_rl_usage.check_rate_limit = lambda k: {
            "test-key-free": {"allowed": True, "count": 1, "limit": 20, "remaining": 19},
            "test-key-starter": {"allowed": True, "count": 1, "limit": 60, "remaining": 59},
        }.get(k, {"allowed": False, "count": 0, "limit": 0, "remaining": 0})

        mock_rl_usage.check_monthly_limit = AsyncMock(side_effect=lambda k: {
            "test-key-free": {"allowed": True, "usage": 0, "limit": 1000, "remaining": 1000},
            "test-key-starter": {"allowed": True, "usage": 0, "limit": 10000, "remaining": 10000},
        }.get(k, {"allowed": False, "usage": 0, "limit": 0, "remaining": 0}))

        yield


class TestVerificarAutenticacao:
    @pytest.mark.asyncio
    async def test_sem_header_retorna_invalido(self):
        resultado = await verificar_autenticacao({})
        assert resultado["valid"] is False
        assert resultado["error"] == "Invalid or missing API key"

    @pytest.mark.asyncio
    async def test_header_vazio_retorna_invalido(self):
        resultado = await verificar_autenticacao({"x-api-key": ""})
        assert resultado["valid"] is False

    @pytest.mark.asyncio
    async def test_header_espacos_retorna_invalido(self):
        resultado = await verificar_autenticacao({"x-api-key": "   "})
        assert resultado["valid"] is False

    @pytest.mark.asyncio
    async def test_chave_invalida_retorna_invalido(self):
        resultado = await verificar_autenticacao({"x-api-key": "chave-que-nao-existe"})
        assert resultado["valid"] is False

    @pytest.mark.asyncio
    async def test_chave_valida_retorna_valido(self):
        resultado = await verificar_autenticacao({"x-api-key": "test-key-free"})
        assert resultado["valid"] is True
        assert resultado["api_key"] == "test-key-free"
        assert resultado["plan"] == "free"

    @pytest.mark.asyncio
    async def test_chave_starter_retorna_starter(self):
        resultado = await verificar_autenticacao({"x-api-key": "test-key-starter"})
        assert resultado["valid"] is True
        assert resultado["plan"] == "starter"


class TestRateLimit:
    def test_primeira_requisicao_permitida(self):
        resultado = verificar_rate_limit("test-key-free")
        assert resultado["allowed"] is True
        assert resultado["count"] >= 1

    @pytest.mark.asyncio
    async def test_limite_mensal_permitido(self):
        resultado = await verificar_limite_mensal("test-key-free")
        assert resultado["allowed"] is True
        assert resultado["limit"] == 1000
        assert resultado["remaining"] >= 0

    def test_chave_invalida_bloqueada(self):
        resultado = verificar_rate_limit("chave-inexistente")
        assert resultado["allowed"] is False

    @pytest.mark.asyncio
    async def test_limite_mensal_chave_invalida(self):
        resultado = await verificar_limite_mensal("chave-inexistente")
        assert resultado["allowed"] is False

"""Testes para o middleware de autenticação e rate limiting."""

import pytest
from src.middleware.auth import verificar_autenticacao, TIER_FREE, TIER_PAID
from src.middleware.rate_limit import verificar_rate_limit, limpar_contadores


class TestVerificarAutenticacao:
    def test_sem_header_retorna_free(self):
        resultado = verificar_autenticacao({})
        assert resultado["tier"] == TIER_FREE
        assert resultado["api_key"] is None

    def test_header_vazio_retorna_free(self):
        resultado = verificar_autenticacao({"x-api-key": ""})
        assert resultado["tier"] == TIER_FREE

    def test_header_espacos_retorna_free(self):
        resultado = verificar_autenticacao({"x-api-key": "   "})
        assert resultado["tier"] == TIER_FREE

    def test_chave_valida_retorna_paid(self):
        resultado = verificar_autenticacao({"x-api-key": "minha-chave-123"})
        assert resultado["tier"] == TIER_PAID
        assert resultado["api_key"] == "minha-chave-123"

    def test_chave_qualquer_retorna_paid(self):
        resultado = verificar_autenticacao({"x-api-key": "abc"})
        assert resultado["tier"] == TIER_PAID

    def test_paid_tem_limite_maior(self):
        free = verificar_autenticacao({})
        paid = verificar_autenticacao({"x-api-key": "key"})
        assert paid["daily_limit"] > free["daily_limit"]


class TestRateLimit:
    def setup_method(self):
        limpar_contadores()

    def teardown_method(self):
        limpar_contadores()

    def test_primeira_requisicao_permitida(self):
        resultado = verificar_rate_limit("192.168.1.1", TIER_FREE, 100)
        assert resultado["allowed"] is True
        assert resultado["count"] == 1
        assert resultado["remaining"] == 99

    def test_contador_incrementa(self):
        verificar_rate_limit("192.168.1.1", TIER_FREE, 100)
        verificar_rate_limit("192.168.1.1", TIER_FREE, 100)
        resultado = verificar_rate_limit("192.168.1.1", TIER_FREE, 100)
        assert resultado["count"] == 3
        assert resultado["remaining"] == 97

    def test_limite_atingido_bloqueia(self):
        resultado = verificar_rate_limit("192.168.1.1", TIER_FREE, 2)
        assert resultado["allowed"] is True

        resultado = verificar_rate_limit("192.168.1.1", TIER_FREE, 2)
        assert resultado["allowed"] is True

        resultado = verificar_rate_limit("192.168.1.1", TIER_FREE, 2)
        assert resultado["allowed"] is False
        assert resultado["remaining"] == 0

    def test_ips_diferentes_contam_separado(self):
        verificar_rate_limit("192.168.1.1", TIER_FREE, 1)
        resultado = verificar_rate_limit("192.168.1.2", TIER_FREE, 1)
        assert resultado["allowed"] is True

    def test_tiers_diferentes_contam_separado(self):
        verificar_rate_limit("key1", TIER_FREE, 1)
        resultado = verificar_rate_limit("key1", TIER_PAID, 10000)
        assert resultado["allowed"] is True

    def test_limpar_contadores(self):
        verificar_rate_limit("192.168.1.1", TIER_FREE, 1)
        limpar_contadores()
        resultado = verificar_rate_limit("192.168.1.1", TIER_FREE, 1)
        assert resultado["count"] == 1

"""Fixtures compartilhadas para testes."""

import pytest


@pytest.fixture
def cpf_valido():
    """CPF válido para testes."""
    return "52998224725"


@pytest.fixture
def cpf_invalido():
    """CPF inválido para testes."""
    return "11111111111"


@pytest.fixture
def cnpj_valido():
    """CNPJ válido para testes."""
    return "11222333000181"


@pytest.fixture
def cnpj_invalido():
    """CNPJ inválido para testes."""
    return "11111111000111"

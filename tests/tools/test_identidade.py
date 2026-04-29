"""Testes para o módulo de identidade — validação e formatação."""

import pytest
from src.utils.validators import validar_cpf, validar_cnpj, limpar_numeros
from src.utils.formatters import formatar_cpf, formatar_cnpj


class TestLimparNumeros:
    def test_remove_formatacao_cpf(self):
        assert limpar_numeros("123.456.789-09") == "12345678909"

    def test_remove_formatacao_cnpj(self):
        assert limpar_numeros("11.222.333/0001-81") == "11222333000181"

    def test_string_sem_digitos(self):
        assert limpar_numeros("abc") == ""

    def test_string_vazia(self):
        assert limpar_numeros("") == ""


class TestValidarCPF:
    def test_cpf_valido(self):
        assert validar_cpf("52998224725") is True

    def test_cpf_valido_com_formatacao(self):
        assert validar_cpf("529.982.247-25") is True

    def test_cpf_invalido_digitos_iguais(self):
        assert validar_cpf("11111111111") is False
        assert validar_cpf("00000000000") is False

    def test_cpf_invalido_tamanho(self):
        assert validar_cpf("123456789") is False
        assert validar_cpf("123456789012") is False

    def test_cpf_invalido_digito_verificador(self):
        assert validar_cpf("52998224726") is False

    def test_cpf_vazio(self):
        assert validar_cpf("") is False


class TestValidarCNPJ:
    def test_cnpj_valido(self):
        assert validar_cnpj("11222333000181") is True

    def test_cnpj_valido_com_formatacao(self):
        assert validar_cnpj("11.222.333/0001-81") is True

    def test_cnpj_invalido_digitos_iguais(self):
        assert validar_cnpj("11111111111111") is False

    def test_cnpj_invalido_tamanho(self):
        assert validar_cnpj("123456789") is False
        assert validar_cnpj("123456789012345") is False

    def test_cnpj_invalido_digito_verificador(self):
        assert validar_cnpj("11222333000182") is False

    def test_cnpj_vazio(self):
        assert validar_cnpj("") is False


class TestFormatarCPF:
    def test_formatacao_correta(self):
        assert formatar_cpf("12345678909") == "123.456.789-09"

    def test_formatacao_com_entrada_formatada(self):
        assert formatar_cpf("123.456.789-09") == "123.456.789-09"

    def test_tamanho_incorreto(self):
        assert formatar_cpf("12345") == "12345"


class TestFormatarCNPJ:
    def test_formatacao_correta(self):
        assert formatar_cnpj("11222333000181") == "11.222.333/0001-81"

    def test_formatacao_com_entrada_formatada(self):
        assert formatar_cnpj("11.222.333/0001-81") == "11.222.333/0001-81"

    def test_tamanho_incorreto(self):
        assert formatar_cnpj("12345") == "12345"

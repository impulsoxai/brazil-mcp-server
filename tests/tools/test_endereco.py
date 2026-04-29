"""Testes para formatação de CEP, telefone e endereço."""

import pytest
from src.utils.formatters import formatar_cep, formatar_telefone_br, formatar_endereco


class TestFormatarCEP:
    def test_cep_valido(self):
        assert formatar_cep("01310100") == "01310-100"

    def test_cep_com_formatacao(self):
        assert formatar_cep("01310-100") == "01310-100"

    def test_cep_tamanho_incorreto(self):
        assert formatar_cep("1234") == "1234"

    def test_cep_vazio(self):
        assert formatar_cep("") == ""

    def test_cep_com_letras(self):
        # 'a' é removido, resultando em 7 dígitos — não formata
        assert formatar_cep("0131a100") == "0131100"


class TestFormatarTelefone:
    def test_celular_11_digitos(self):
        assert formatar_telefone_br("11999998888") == "(11) 99999-8888"

    def test_fixo_10_digitos(self):
        assert formatar_telefone_br("1133334444") == "(11) 3333-4444"

    def test_com_formatacao(self):
        assert formatar_telefone_br("(11) 99999-8888") == "(11) 99999-8888"

    def test_tamanho_incorreto(self):
        assert formatar_telefone_br("123") == "123"

    def test_vazio(self):
        assert formatar_telefone_br("") == ""


class TestFormatarEndereco:
    def test_endereco_completo(self):
        resultado = formatar_endereco(
            logradouro="Rua das Flores",
            numero="123",
            complemento="Sala 4",
            bairro="Centro",
            cidade="São Paulo",
            uf="SP",
            cep="01310100",
        )
        assert "Rua das Flores, 123 — Sala 4" in resultado
        assert "Centro" in resultado
        assert "São Paulo/SP" in resultado
        assert "01310-100" in resultado

    def test_endereco_minimo(self):
        resultado = formatar_endereco(logradouro="Rua A", cidade="SP", uf="SP")
        assert "Rua A" in resultado
        assert "SP/SP" in resultado

    def test_endereco_vazio(self):
        assert formatar_endereco() == ""

    def test_so_logradouro(self):
        resultado = formatar_endereco(logradouro="Rua B")
        assert resultado == "Rua B"

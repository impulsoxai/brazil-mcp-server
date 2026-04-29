"""Testes para o módulo de pagamentos — PIX, juros, multa."""

import pytest
from src.tools.pagamentos import (
    _identificar_tipo_chave,
    _formatar_valor_brl,
    _calcular_crc16,
)


class TestIdentificarTipoChave:
    def test_cpf(self):
        assert _identificar_tipo_chave("52998224725") == "cpf"

    def test_cpf_formatado(self):
        assert _identificar_tipo_chave("529.982.247-25") == "cpf"

    def test_cnpj(self):
        assert _identificar_tipo_chave("11222333000181") == "cnpj"

    def test_cnpj_formatado(self):
        assert _identificar_tipo_chave("11.222.333/0001-81") == "cnpj"

    def test_email(self):
        assert _identificar_tipo_chave("user@example.com") == "email"

    def test_email_com_ponto(self):
        assert _identificar_tipo_chave("nome.sobrenome@empresa.com.br") == "email"

    def test_telefone_com_55(self):
        assert _identificar_tipo_chave("+5511999998888") == "telefone"

    def test_telefone_sem_mais(self):
        assert _identificar_tipo_chave("5511999998888") == "telefone"

    def test_telefone_10_digitos(self):
        assert _identificar_tipo_chave("1133334444") == "telefone"

    def test_telefone_11_digitos(self):
        assert _identificar_tipo_chave("11999998888") == "telefone"

    def test_aleatoria_uuid(self):
        assert _identificar_tipo_chave("a1b2c3d4-e5f6-7890-abcd-ef1234567890") == "aleatoria"

    def test_invalida(self):
        assert _identificar_tipo_chave("abc") is None

    def test_invalida_vazia(self):
        assert _identificar_tipo_chave("") is None

    def test_invalida_numeros_poucos(self):
        assert _identificar_tipo_chave("12345") is None


class TestFormatarValorBrl:
    def test_valor_simples(self):
        assert _formatar_valor_brl(100.00) == "100.00"

    def test_valor_com_centavos(self):
        assert _formatar_valor_brl(1234.56) == "1234.56"

    def test_valor_zero(self):
        assert _formatar_valor_brl(0.00) == "0.00"


class TestCalcularCrc16:
    def test_crc_nao_vazio(self):
        resultado = _calcular_crc16("000201")
        assert len(resultado) == 4
        assert resultado.isalnum()

    def test_crc_diferente_para_diferentes_inputs(self):
        crc1 = _calcular_crc16("000201")
        crc2 = _calcular_crc16("000202")
        assert crc1 != crc2

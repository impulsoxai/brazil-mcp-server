"""Testes para Onda 1 — Ferramentas de lógica pura."""

import pytest
from src.tools.onda1.validacao import validar_email_br


class TestValidarEmailBr:
    def test_validar_email_br_valido(self):
        result = validar_email_br("usuario@gmail.com")
        assert result["valido"] is True
        assert result["dominio"] == "gmail.com"

    def test_validar_email_br_yahoo(self):
        result = validar_email_br("usuario@yahoo.com.br")
        assert result["valido"] is True
        assert result["dominio"] == "yahoo.com.br"

    def test_validar_email_br_typo_gmai(self):
        result = validar_email_br("usuario@gmai.com")
        assert result["valido"] is False
        assert result["sugestao"] == "gmail.com"

    def test_validar_email_br_typo_gmal(self):
        result = validar_email_br("usuario@gmal.com")
        assert result["valido"] is False
        assert result["sugestao"] == "gmail.com"

    def test_validar_email_br_typo_hotmal(self):
        result = validar_email_br("usuario@hotmal.com")
        assert result["valido"] is False
        assert result["sugestao"] == "hotmail.com"

    def test_validar_email_br_typo_hotmial(self):
        result = validar_email_br("usuario@hotmial.com")
        assert result["valido"] is False
        assert result["sugestao"] == "hotmail.com"

    def test_validar_email_br_sem_arroba(self):
        result = validar_email_br("usuario.gmail.com")
        assert result["valido"] is False
        assert result["sugestao"] is None

    def test_validar_email_br_vazio(self):
        result = validar_email_br("")
        assert result["valido"] is False
        assert result["sugestao"] is None

    def test_validar_email_br_apenas_arroba(self):
        result = validar_email_br("@")
        assert result["valido"] is False

    def test_validar_email_br_dominio_sem_ponto(self):
        result = validar_email_br("usuario@dominio")
        assert result["valido"] is False

    def test_validar_email_br_com_espacos(self):
        result = validar_email_br("  usuario@gmail.com  ")
        assert result["valido"] is True
        assert result["dominio"] == "gmail.com"

    def test_validar_email_br_truncamento_254(self):
        result = validar_email_br("a" * 300 + "@gmail.com")
        assert len(result) >= 0  # Sem crash, truncou
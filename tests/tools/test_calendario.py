"""Testes para o módulo de calendário — datas, feriados, dias úteis."""

import pytest
from datetime import date
from src.tools.calendario import (
    _parse_data,
    _formatar_data,
    _eh_feriado,
    _eh_dia_util,
)


class TestParseData:
    def test_formato_iso(self):
        assert _parse_data("2026-04-15") == date(2026, 4, 15)

    def test_formato_brasileiro(self):
        assert _parse_data("15/04/2026") == date(2026, 4, 15)

    def test_data_invalida(self):
        assert _parse_data("data-invalida") is None

    def test_data_vazia(self):
        assert _parse_data("") is None

    def test_com_espacos(self):
        assert _parse_data("  2026-04-15  ") == date(2026, 4, 15)


class TestFormatarData:
    def test_formatacao(self):
        assert _formatar_data(date(2026, 4, 15)) == "15/04/2026"

    def test_formatacao_janeiro(self):
        assert _formatar_data(date(2026, 1, 1)) == "01/01/2026"


class TestEhFeriado:
    def test_carnaval_nao_eh(self):
        # Carnaval não é feriado nacional
        feriados = {"01-01", "04-21", "09-07"}
        assert _eh_feriado(date(2026, 2, 17), feriados) is False

    def test_tiradentes_eh(self):
        feriados = {"01-01", "04-21", "09-07"}
        assert _eh_feriado(date(2026, 4, 21), feriados) is True

    def test_nao_feriado(self):
        feriados = {"01-01", "04-21"}
        assert _eh_feriado(date(2026, 3, 10), feriados) is False

    def test_dia_dos_trabalhadores(self):
        feriados = {"05-01"}
        assert _eh_feriado(date(2026, 5, 1), feriados) is True


class TestEhDiaUtil:
    def test_segunda_normal(self):
        # 2026-04-13 é segunda-feira
        feriados: set[str] = set()
        assert _eh_dia_util(date(2026, 4, 13), feriados) is True

    def test_sabado(self):
        # 2026-04-11 é sábado
        feriados: set[str] = set()
        assert _eh_dia_util(date(2026, 4, 11), feriados) is False

    def test_domingo(self):
        # 2026-04-12 é domingo
        feriados: set[str] = set()
        assert _eh_dia_util(date(2026, 4, 12), feriados) is False

    def test_feriado_em_dia_util(self):
        # 2026-04-21 é terça-feira (Tiradentes)
        feriados = {"04-21"}
        assert _eh_dia_util(date(2026, 4, 21), feriados) is False

    def test_sexta_normal(self):
        # 2026-04-10 é sexta-feira
        feriados: set[str] = set()
        assert _eh_dia_util(date(2026, 4, 10), feriados) is True

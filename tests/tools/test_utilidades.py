"""Testes para o módulo de utilidades — telefone, DDD."""

import pytest
from src.tools.utilidades import _DDD_ESTADOS


class TestDDDEstados:
    def test_ddds_sao_paulo(self):
        assert "11" in _DDD_ESTADOS
        assert _DDD_ESTADOS["11"] == "São Paulo"

    def test_ddds_rio(self):
        assert _DDD_ESTADOS["21"] == "Rio de Janeiro"

    def test_ddds_brasilia(self):
        assert _DDD_ESTADOS["61"] == "Distrito Federal / Goiás"

    def test_ddds_amazonas(self):
        assert _DDD_ESTADOS["92"] == "Amazonas"

    def test_total_ddds(self):
        # Brasil tem 67 DDDs
        assert len(_DDD_ESTADOS) == 67

    def test_todos_ddds_2_digitos(self):
        for ddd in _DDD_ESTADOS:
            assert len(ddd) == 2
            assert ddd.isdigit()

    def test_ddds_entre_11_e_99(self):
        for ddd in _DDD_ESTADOS:
            assert 11 <= int(ddd) <= 99

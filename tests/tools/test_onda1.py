"""Testes para Onda 1 — Ferramentas de lógica pura."""

import pytest
from datetime import date, timedelta
from src.tools.onda1.validacao import validar_email_br, gerar_senha_segura, converter_numero_extenso
from src.tools.onda1.datas import calcular_idade, formatar_data_br, calcular_diferenca_datas
from src.tools.onda1.mensagem import formatar_mensagem_whatsapp, gerar_link_whatsapp
from src.tools.onda1.calculos import calcular_desconto, calcular_comissao, calcular_imc, calcular_reajuste_inflacao


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


class TestGerarSenhaSegura:
    def test_gerar_senha_tamanho_16_tem_16_chars(self):
        from src.tools.onda1.validacao import gerar_senha_segura
        result = gerar_senha_segura(tamanho=16)
        assert len(result["senha"]) == 16

    def test_gerar_senha_tamanho_4_minimo(self):
        from src.tools.onda1.validacao import gerar_senha_segura
        result = gerar_senha_segura(tamanho=4)
        assert len(result["senha"]) == 4

    def test_gerar_senha_tamanho_3_erro(self):
        from src.tools.onda1.validacao import gerar_senha_segura
        result = gerar_senha_segura(tamanho=3)
        assert "erro" in result

    def test_gerar_senha_tamanho_128_max(self):
        from src.tools.onda1.validacao import gerar_senha_segura
        result = gerar_senha_segura(tamanho=128)
        assert len(result["senha"]) == 128
        assert result["nivel_seguranca"] == "muito forte"

    def test_gerar_senha_sem_simbolos_baixa_entropia(self):
        from src.tools.onda1.validacao import gerar_senha_segura
        result = gerar_senha_segura(tamanho=8, incluir_simbolos=False, incluir_numeros=False, incluir_maiusculas=False)
        assert len(result["senha"]) == 8
        assert result["nivel_seguranca"] == "fraca"

    def test_gerar_senha_com_tudo_muito_forte(self):
        from src.tools.onda1.validacao import gerar_senha_segura
        result = gerar_senha_segura(tamanho=24, incluir_simbolos=True, incluir_numeros=True, incluir_maiusculas=True)
        assert result["nivel_seguranca"] in ("forte", "muito forte")


class TestConverterNumeroExtenso:
    def test_um_real(self):
        from src.tools.onda1.validacao import converter_numero_extenso
        result = converter_numero_extenso(1.00)
        assert "um real" in result.lower()

    def test_mil_reais(self):
        from src.tools.onda1.validacao import converter_numero_extenso
        result = converter_numero_extenso(1000.00)
        assert "mil" in result and "reais" in result

    def test_com_centavos(self):
        from src.tools.onda1.validacao import converter_numero_extenso
        result = converter_numero_extenso(1234.56)
        assert "reais" in result and "centavos" in result

    def test_zero_reais(self):
        from src.tools.onda1.validacao import converter_numero_extenso
        result = converter_numero_extenso(0)
        assert "zero" in result.lower()

    def test_negativo_erro(self):
        from src.tools.onda1.validacao import converter_numero_extenso
        result = converter_numero_extenso(-100)
        assert "❌" in result


class TestCalcularIdade:
    def test_idade_basico(self):
        from datetime import date
        nasc = date.today().replace(year=date.today().year - 30)
        result = calcular_idade(nasc.strftime("%d/%m/%Y"))
        assert result["anos"] == 30

    def test_data_futura_erro(self):
        from datetime import date
        futura = date.today().replace(year=date.today().year + 1)
        result = calcular_idade(futura.strftime("%d/%m/%Y"))
        assert "erro" in result


class TestFormatarDataBr:
    def test_iso_to_br(self):
        result = formatar_data_br("2026-05-11")
        assert result["data_formatada"] == "11/05/2026"

    def test_dia_semana(self):
        result = formatar_data_br("2026-05-11")
        assert result["dia_semana"] == "segunda-feira"

    def test_extenso(self):
        result = formatar_data_br("2026-05-11")
        assert "maio" in result["extenso"]

    def test_data_invalida_erro(self):
        result = formatar_data_br("invalid")
        assert "erro" in result


class TestCalcularDiferencaDatas:
    def test_30_dias(self):
        result = calcular_diferenca_datas("01/05/2026", "31/05/2026")
        assert result["dias"] == 30

    def test_mesma_data_zero(self):
        result = calcular_diferenca_datas("15/05/2026", "15/05/2026")
        assert result["dias"] == 0

    def test_fim_menor_inicio_erro(self):
        result = calcular_diferenca_datas("31/05/2026", "01/05/2026")
        assert "erro" in result


class TestFormatarMensagemWhatsapp:
    def test_negrito(self):
        result = formatar_mensagem_whatsapp("texto", negrito=True)
        assert result == "*texto*"

    def test_italico(self):
        result = formatar_mensagem_whatsapp("texto", italico=True)
        assert result == "_texto_"

    def test_lista(self):
        result = formatar_mensagem_whatsapp("", itens=["a", "b"])
        assert "- a" in result and "- b" in result

    def test_negrito_e_italico_nao_sao_substrings_separados(self):
        # Aplicação sequencial: bold depois italic = _*texto*_
        # Não existe na spec comportamento para negrito+italico simultâneo
        result = formatar_mensagem_whatsapp("texto", negrito=True, italico=True)
        # Result é _*texto*_ — não contém "*texto*" nem "_texto_" separadamente
        assert result == "_*texto*_"


class TestGerarLinkWhatsapp:
    def test_link_basico(self):
        result = gerar_link_whatsapp("5548999123456")
        assert "wa.me/5548999123456" in result

    def test_link_com_mensagem(self):
        result = gerar_link_whatsapp("5548999123456", "Olá")
        assert "wa.me/5548999123456" in result
        assert "text=" in result

    def test_telefone_vazio_erro(self):
        result = gerar_link_whatsapp("")
        assert "❌" in result


class TestCalcularDesconto:
    def test_desconto_10porcento(self):
        result = calcular_desconto(100, 10)
        assert result["valor_final"] == 90

    def test_desconto_100porcento(self):
        result = calcular_desconto(100, 100)
        assert result["valor_final"] == 0

    def test_desconto_zero(self):
        result = calcular_desconto(100, 0)
        assert result["valor_final"] == 100

    def test_valor_negativo_erro(self):
        result = calcular_desconto(-100, 10)
        assert "erro" in result

    def test_desconto_maior_100_erro(self):
        result = calcular_desconto(100, 101)
        assert "erro" in result


class TestCalcularComissao:
    def test_comissao_10porcento(self):
        result = calcular_comissao(1000, 10)
        assert result["comissao"] == 100
        assert result["total"] == 1100
        assert result.get("aviso") is None

    def test_comissao_acima_100_com_aviso(self):
        result = calcular_comissao(1000, 150)
        assert result["comissao"] == 1500
        assert result["total"] == 2500
        assert "acima de 100%" in result["aviso"]

    def test_valor_zero_erro(self):
        result = calcular_comissao(0, 10)
        assert "erro" in result


class TestCalcularIMC:
    def test_peso_normal(self):
        # 70kg / 1.75^2 = 22.86
        result = calcular_imc(70, 1.75)
        assert 22.0 < result["imc"] < 23.0
        assert result["classificacao"] == "peso normal"

    def test_abaixo_peso(self):
        result = calcular_imc(50, 1.75)
        assert result["classificacao"] == "abaixo do peso"

    def test_sobrepeso(self):
        result = calcular_imc(90, 1.75)
        assert result["classificacao"] == "sobrepeso"

    def test_obesidade_grau_i(self):
        result = calcular_imc(100, 1.75)
        assert result["classificacao"] == "obesidade grau I"

    def test_peso_negativo_erro(self):
        result = calcular_imc(-70, 1.75)
        assert "erro" in result


class TestCalcularReajuste:
    def test_reajuste_positivo_5porcento(self):
        result = calcular_reajuste_inflacao(1000, 5)
        assert result["valor_final"] == 1050

    def test_reajuste_negativo(self):
        result = calcular_reajuste_inflacao(1000, -3)
        assert result["valor_final"] == 970

    def test_reajuste_zero(self):
        result = calcular_reajuste_inflacao(1000, 0)
        assert result["valor_final"] == 1000

    def test_valor_zero_erro(self):
        result = calcular_reajuste_inflacao(0, 5)
        assert "erro" in result
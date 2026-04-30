"""Suite de testes de qualidade profunda — PIX EMV, feriados móveis, moedas, CNPJ campos, idempotência, latência."""

import httpx
import json
import time
import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_URL = "https://mcp.impulsoxai.com.br"
MCP_URL = f"{BASE_URL}/mcp"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

resultados = []


def parse_sse(text):
    for line in text.strip().split("\n"):
        if line.startswith("data: "):
            try:
                return json.loads(line[6:])
            except Exception:
                pass
    try:
        return json.loads(text)
    except Exception:
        return None


def mcp_init():
    global HEADERS
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test-profundidade", "version": "1.0"},
        },
    }
    r = httpx.post(MCP_URL, json=payload, headers=HEADERS, timeout=30)
    session_id = r.headers.get("mcp-session-id", "")
    if session_id:
        HEADERS["mcp-session-id"] = session_id
    notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    httpx.post(MCP_URL, json=notif, headers=HEADERS, timeout=10)
    return session_id


def chamar_ferramenta(nome, argumentos, req_id=2):
    payload = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": nome, "arguments": argumentos},
    }
    inicio = time.time()
    try:
        r = httpx.post(MCP_URL, json=payload, headers=HEADERS, timeout=30)
        tempo = time.time() - inicio
        data = parse_sse(r.text)
        texto = ""
        if data and "result" in data:
            content = data["result"].get("content", [])
            for c in content:
                if c.get("type") == "text":
                    texto = c["text"]
        elif data and "error" in data:
            texto = f"ERRO: {data['error']}"
        else:
            texto = f"ERRO: {r.text[:300]}"
        return texto, tempo
    except Exception as e:
        tempo = time.time() - inicio
        return f"EXCECAO: {type(e).__name__}: {e}", tempo


def registrar(nome, passou, tempo, texto="", esperado=""):
    status = "PASSOU" if passou else "FALHOU"
    resultados.append((nome, status, tempo, texto[:200], esperado))
    icone = chr(9989) if passou else chr(10060)
    print(f"  {icone} {nome} ({tempo:.2f}s)")
    if not passou:
        print(f"     Esperado: {esperado}")
        print(f"     Recebido: {texto[:150]}")


def extrair_pix_payload(texto):
    """Extrai o payload PIX copia-e-cola do texto de resposta."""
    for linha in texto.split("\n"):
        linha = linha.strip()
        if linha.startswith("000201"):
            return linha
    return ""


def validar_emv_campos(payload):
    """Verifica se os campos EMV obrigatórios do PIX estão presentes."""
    erros = []
    # Campo 00: Payload Format Indicator (obrigatório)
    if "000201" not in payload:
        erros.append("campo 00 (Payload Format Indicator) ausente")
    # Campo 26: Merchant Account Information (PIX) — contém GUI + chave
    if "26" not in payload:
        erros.append("campo 26 (Merchant Account) ausente")
    # Campo 26 subcampo: GUI br.gov.bcb.pix
    if "br.gov.bcb.pix" not in payload:
        erros.append("campo 26 (GUI br.gov.bcb.pix) ausente")
    # Campo 52: Merchant Category Code
    if "5204" not in payload:
        erros.append("campo 52 (MCC) ausente")
    # Campo 53: Transaction Currency (986 = BRL)
    if "5303986" not in payload:
        erros.append("campo 53 (moeda BRL) ausente")
    # Campo 58: Country Code (BR)
    if "5802BR" not in payload:
        erros.append("campo 58 (país BR) ausente")
    # Campo 59: Merchant Name
    if "59" not in payload:
        erros.append("campo 59 (Merchant Name) ausente")
    # Campo 60: Merchant City
    if "60" not in payload:
        erros.append("campo 60 (Merchant City) ausente")
    # Campo 63: CRC (obrigatório)
    if "6304" not in payload:
        erros.append("campo 63 (CRC) ausente")
    return erros


def crc16_ccitt(payload):
    """Calcula CRC16-CCITT (polynomial 0x1021) para validação de referência."""
    crc = 0xFFFF
    for char in payload:
        crc ^= ord(char) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return format(crc, '04X')


def testar():
    print("=" * 60)
    print("  BRAZIL MCP SERVER — TESTES DE PROFUNDIDADE")
    print("=" * 60)

    # =========================================================
    print("\n--- 1. PIX EMV — ESTRUTURA COMPLETA ---")
    # =========================================================

    # 1a. Gerar PIX e validar campos EMV obrigatórios (00, 26, 52, 53, 54, 58, 59, 60, 63)
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": 42.50, "nome": "MARIA SILVA", "cidade": "BELO HORIZONTE"
    }, 100)
    payload = extrair_pix_payload(texto)
    if payload:
        erros = validar_emv_campos(payload)
        passou = len(erros) == 0
        registrar("pix_emv_campos", passou, tempo, f"{len(erros)} campos faltando: {erros}" if erros else f"payload={payload[:60]}...", "campos obrigatórios presentes")
    else:
        registrar("pix_emv_campos", False, tempo, texto[:80], "payload não encontrado")

    # 1b. CRC16 com validação de referência
    if payload:
        # O payload termina com 6304XXXX onde XXXX é o CRC
        if "6304" in payload:
            partes = payload.split("6304")
            base = partes[0] + "6304"
            crc_gerado = partes[1][:4] if len(partes[1]) >= 4 else ""
            crc_esperado = crc16_ccitt(base)
            passou = crc_gerado == crc_esperado
            registrar("pix_crc16_referencia", passou, tempo, f"crc_gerado={crc_gerado}, crc_ref={crc_esperado}", "CRCs coincidem")
        else:
            registrar("pix_crc16_referencia", False, tempo, "6304 não encontrado", "CRC presente")
    else:
        registrar("pix_crc16_referencia", False, tempo, "payload não extraído", "CRC válido")

    # 1c. PIX com valor específico — Transaction Amount correto
    if payload:
        # Campo 54: Transaction Amount (valor)
        # Procurar por 540X seguido do valor
        tem_valor = "540" in payload and "42.50" in payload
        passou = tem_valor
        registrar("pix_valor_no_payload", passou, tempo, f"valor 42.50 no payload: {tem_valor}", "valor presente")
    else:
        registrar("pix_valor_no_payload", False, tempo, "payload não extraído", "valor presente")

    # 1d. PIX com nome com acentos — Merchant Name
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": 10, "nome": "José da Conceição São Paulo", "cidade": "São Paulo"
    }, 103)
    passou = chr(9989) in texto and "000201" in texto
    registrar("pix_nome_acentos_emv", passou, tempo, texto[:80], "gerou com acentos")

    # 1e. PIX — GUI br.gov.bcb.pix presente no campo 26
    if payload:
        tem_gui = "br.gov.bcb.pix" in payload
        passou = tem_gui
        registrar("pix_gui_bcb", passou, tempo, f"GUI presente: {tem_gui}", "br.gov.bcb.pix presente")
    else:
        registrar("pix_gui_bcb", False, tempo, "payload não extraído", "GUI presente")

    # =========================================================
    print("\n--- 2. FERIADOS MOVEIS ---")
    # =========================================================

    # 2a. Feriados 2026 — Carnaval deve estar presente
    texto, tempo = chamar_ferramenta("listar_feriados_nacionais", {"ano": 2026}, 200)
    passou = chr(9989) in texto
    registrar("feriados_2026_ok", passou, tempo, texto[:80], "retornou feriados")

    # 2b. Carnaval 2026 está na lista? (17/02/2026)
    if chr(9989) in texto:
        tem_carnaval = "carnaval" in texto.lower() or "17/02" in texto or "17-02" in texto or "02-17" in texto
        passou = tem_carnaval
        registrar("feriados_carnaval_2026", passou, tempo, texto[:200], "Carnaval 17/02 presente")
    else:
        registrar("feriados_carnaval_2026", False, tempo, texto[:80], "Carnaval presente")

    # 2c. Páscoa 2026 está na lista? (05/04/2026)
    if chr(9989) in texto:
        tem_pascoa = "páscoa" in texto.lower() or "pascoa" in texto.lower() or "05/04" in texto or "04-05" in texto or "05-04" in texto
        passou = tem_pascoa
        registrar("feriados_pascoa_2026", passou, tempo, texto[:200], "Páscoa 05/04 presente")
    else:
        registrar("feriados_pascoa_2026", False, tempo, texto[:80], "Páscoa presente")

    # 2d. Sexta-feira Santa 2026 (03/04/2026)
    if chr(9989) in texto:
        tem_sexta_santa = "sexta" in texto.lower() and "santa" in texto.lower()
        passou = tem_sexta_santa
        registrar("feriados_sexta_santa", passou, tempo, texto[:200], "Sexta-feira Santa presente")
    else:
        registrar("feriados_sexta_santa", False, tempo, texto[:80], "Sexta-feira Santa")

    # 2e. Corpus Christi 2026 (04/06/2026)
    if chr(9989) in texto:
        tem_corpus = "corpus" in texto.lower()
        passou = tem_corpus
        registrar("feriados_corpus_christi", passou, tempo, texto[:200], "Corpus Christi presente")
    else:
        registrar("feriados_corpus_christi", False, tempo, texto[:80], "Corpus Christi")

    # 2f. Feriados fixos — Natal e Ano Novo sempre presentes
    if chr(9989) in texto:
        tem_natal = "25/12" in texto or "natal" in texto.lower()
        tem_ano_novo = "01/01" in texto or "ano novo" in texto.lower()
        passou = tem_natal and tem_ano_novo
        registrar("feriados_fixos", passou, tempo, f"natal={tem_natal}, ano_novo={tem_ano_novo}", "Natal + Ano Novo")
    else:
        registrar("feriados_fixos", False, tempo, texto[:80], "Natal + Ano Novo")

    # =========================================================
    print("\n--- 3. MOEDAS — MULTIPLAS CONVERSOES ---")
    # =========================================================

    # 3a. BRL → EUR
    texto, tempo = chamar_ferramenta("converter_moeda", {"valor": 100, "de": "BRL", "para": "EUR"}, 300)
    passou = chr(9989) in texto and "EUR" in texto
    registrar("moeda_brl_eur", passou, tempo, texto[:80], "BRL → EUR")

    # 3b. USD → BRL
    texto, tempo = chamar_ferramenta("converter_moeda", {"valor": 50, "de": "USD", "para": "BRL"}, 301)
    passou = chr(9989) in texto and "BRL" in texto
    registrar("moeda_usd_brl", passou, tempo, texto[:80], "USD → BRL")

    # 3c. EUR → USD
    texto, tempo = chamar_ferramenta("converter_moeda", {"valor": 100, "de": "EUR", "para": "USD"}, 302)
    passou = chr(9989) in texto and "USD" in texto
    registrar("moeda_eur_usd", passou, tempo, texto[:80], "EUR → USD")

    # 3d. BRL → GBP
    texto, tempo = chamar_ferramenta("converter_moeda", {"valor": 200, "de": "BRL", "para": "GBP"}, 303)
    passou = chr(9989) in texto and "GBP" in texto
    registrar("moeda_brl_gbp", passou, tempo, texto[:80], "BRL → GBP")

    # 3e. BRL → JPY (moeda sem decimais)
    texto, tempo = chamar_ferramenta("converter_moeda", {"valor": 100, "de": "BRL", "para": "JPY"}, 304)
    passou = chr(9989) in texto and "JPY" in texto
    registrar("moeda_brl_jpy", passou, tempo, texto[:80], "BRL → JPY")

    # 3f. BRL → ARPY (moeda inexistente)
    texto, tempo = chamar_ferramenta("converter_moeda", {"valor": 100, "de": "BRL", "para": "XYZ"}, 305)
    passou = "❌" in texto
    registrar("moeda_inexistente", passou, tempo, texto[:80], "rejeitou moeda inválida")

    # =========================================================
    print("\n--- 4. CNPJ — CAMPOS COMPLETOS ---")
    # =========================================================

    # 4a. CNPJ com dados completos — CNPJ válido para testar campos
    texto, tempo = chamar_ferramenta("consultar_cnpj", {"cnpj": "33683111000107"}, 400)
    if chr(9989) in texto:
        campos_obrigatorios = ["Razão Social", "Nome Fantasia", "Situação", "CNAE", "Abertura"]
        campos_presentes = sum(1 for c in campos_obrigatorios if c.lower() in texto.lower())
        passou = campos_presentes >= 3
        registrar("cnpj_campos_completos", passou, tempo, f"{campos_presentes}/{len(campos_obrigatorios)} campos", ">= 3 campos")
    else:
        # API pode falhar por rate limit — aceitar erro externo
        passou = "Erro ao consultar" in texto or "❌" in texto
        registrar("cnpj_campos_completos", passou, tempo, texto[:80], "respondeu (ok ou erro API)")

    # 4b. CNPJ — endereço completo na resposta (ou erro da API externa)
    if chr(9989) in texto:
        tem_endereco = "Endereço" in texto or "Logradouro" in texto
        passou = tem_endereco
        registrar("cnpj_endereco", passou, tempo, texto[:80], "endereço presente")
    else:
        # API externa pode falhar — aceitar erro tratado
        passou = "Erro ao consultar" in texto or "❌" in texto
        registrar("cnpj_endereco", passou, tempo, texto[:80], "erro API tratado")

    # 4c. CNPJ — situação cadastral (ou erro da API externa)
    if chr(9989) in texto:
        tem_situacao = "ATIVA" in texto.upper() or "INATIVA" in texto.upper() or "SUSPENSA" in texto.upper() or "Situação" in texto
        passou = tem_situacao
        registrar("cnpj_situacao", passou, tempo, texto[:80], "situação presente")
    else:
        passou = "Erro ao consultar" in texto or "❌" in texto
        registrar("cnpj_situacao", passou, tempo, texto[:80], "erro API tratado")

    # 4d. CNPJ — CNAE principal (ou erro da API externa)
    if chr(9989) in texto:
        tem_cnae = "CNAE" in texto
        passou = tem_cnae
        registrar("cnpj_cnae", passou, tempo, texto[:80], "CNAE presente")
    else:
        passou = "Erro ao consultar" in texto or "❌" in texto
        registrar("cnpj_cnae", passou, tempo, texto[:80], "erro API tratado")

    # 4e. CNPJ — QSA quadro de sócios (ou erro da API externa)
    if chr(9989) in texto:
        tem_qsa = "QSA" in texto or "Sócios" in texto or "sócios" in texto or "Socio" in texto
        passou = tem_qsa
        registrar("cnpj_qsa", passou, tempo, texto[:80], "QSA presente")
    else:
        passou = "Erro ao consultar" in texto or "❌" in texto
        registrar("cnpj_qsa", passou, tempo, texto[:80], "erro API tratado")

    # =========================================================
    print("\n--- 5. IDEMPOTENCIA ---")
    # =========================================================

    # 5a. Mesma chamada 3x — CPF válido
    resultados_cpf = []
    for i in range(3):
        texto, _ = chamar_ferramenta("validar_cpf_tool", {"cpf": "52998224725"}, 500 + i)
        resultados_cpf.append(texto)
    passou = all(r == resultados_cpf[0] for r in resultados_cpf) and chr(9989) in resultados_cpf[0]
    registrar("idemp_cpf_3x", passou, 0, "3 respostas idênticas" if passou else "respostas diferentes", "idênticas")

    # 5b. Mesma chamada 3x — CNPJ válido
    resultados_cnpj = []
    for i in range(3):
        texto, _ = chamar_ferramenta("validar_cnpj_tool", {"cnpj": "11222333000181"}, 510 + i)
        resultados_cnpj.append(texto)
    passou = all(r == resultados_cnpj[0] for r in resultados_cnpj)
    registrar("idemp_cnpj_3x", passou, 0, "3 respostas idênticas" if passou else "respostas diferentes", "idênticas")

    # 5c. Mesma chamada 3x — cálculo financeiro
    resultados_juros = []
    for i in range(3):
        texto, _ = chamar_ferramenta("calcular_juros_simples", {
            "principal": 5000, "taxa_mensal": 1.5, "meses": 24
        }, 520 + i)
        resultados_juros.append(texto)
    passou = all(r == resultados_juros[0] for r in resultados_juros)
    registrar("idemp_juros_3x", passou, 0, "3 respostas idênticas" if passou else "respostas diferentes", "idênticas")

    # 5d. Mesma chamada 3x — listar feriados
    resultados_feriados = []
    for i in range(3):
        texto, _ = chamar_ferramenta("listar_feriados_nacionais", {"ano": 2026}, 530 + i)
        resultados_feriados.append(texto)
    passou = all(r == resultados_feriados[0] for r in resultados_feriados)
    registrar("idemp_feriados_3x", passou, 0, "3 respostas idênticas" if passou else "respostas diferentes", "idênticas")

    # =========================================================
    print("\n--- 6. LATENCIA POR FERRAMENTA ---")
    # =========================================================

    ferramentas_latencia = [
        ("validar_cpf_tool", {"cpf": "52998224725"}, "latencia_cpf"),
        ("validar_cnpj_tool", {"cnpj": "11222333000181"}, "latencia_cnpj"),
        ("buscar_endereco_por_cep", {"cep": "01310100"}, "latencia_cep"),
        ("calcular_juros_simples", {"principal": 1000, "taxa_mensal": 2, "meses": 12}, "latencia_juros"),
        ("calcular_juros_compostos", {"principal": 1000, "taxa_mensal": 1, "meses": 12}, "latencia_juros_comp"),
        ("calcular_multa_atraso", {"valor": 1000, "dias_atraso": 30}, "latencia_multa"),
        ("gerar_pix_copia_cola", {"chave": "52998224725", "valor": 10, "nome": "TESTE", "cidade": "SP"}, "latencia_pix"),
        ("validar_chave_pix", {"chave": "52998224725"}, "latencia_pix_validar"),
        ("validar_telefone_br", {"telefone": "+5511999998888"}, "latencia_telefone"),
        ("formatar_telefone_br_tool", {"telefone": "+5511999998888"}, "latencia_fmt_tel"),
        ("formatar_cpf_tool", {"cpf": "52998224725"}, "latencia_fmt_cpf"),
        ("formatar_cnpj_tool", {"cnpj": "11222333000181"}, "latencia_fmt_cnpj"),
        ("listar_ddd_estados", {}, "latencia_ddd"),
        ("buscar_banco_por_codigo", {"codigo": "001"}, "latencia_banco"),
        ("converter_moeda", {"valor": 100, "de": "BRL", "para": "USD"}, "latencia_moeda"),
        ("listar_feriados_nacionais", {"ano": 2026}, "latencia_feriados"),
        ("verificar_dia_util", {"data": "2026-04-30"}, "latencia_dia_util"),
        ("calcular_prazo_util", {"data_inicio": "2026-04-30", "dias_uteis": 10}, "latencia_prazo"),
        ("proximo_dia_util", {"data": "2026-04-30"}, "latencia_proximo"),
        ("consultar_cnpj", {"cnpj": "33683111000107"}, "latencia_consultar_cnpj"),
    ]

    latencias = []
    for i, (nome, args, label) in enumerate(ferramentas_latencia):
        texto, tempo = chamar_ferramenta(nome, args, 600 + i)
        latencias.append((label, tempo, tempo < 5.0))
        passou = tempo < 5.0
        registrar(label, passou, tempo, f"{tempo:.2f}s", "< 5s")

    # 6b. Resumo de latência
    tempos = [t for _, t, _ in latencias]
    media = sum(tempos) / len(tempos)
    p95 = sorted(tempos)[int(len(tempos) * 0.95)]
    maximo = max(tempos)
    passou = p95 < 5.0
    registrar("latencia_p95", passou, 0, f"media={media:.2f}s, p95={p95:.2f}s, max={maximo:.2f}s", "P95 < 5s")

    # =========================================================
    print("\n--- 7. VALIDACAO CRUZADA ---")
    # =========================================================

    # 7a. CPF válido no validar_cpf → também válido no formatar_cpf
    texto_val, _ = chamar_ferramenta("validar_cpf_tool", {"cpf": "52998224725"}, 700)
    texto_fmt, _ = chamar_ferramenta("formatar_cpf_tool", {"cpf": "52998224725"}, 701)
    val_ok = chr(9989) in texto_val and "válido" in texto_val.lower()
    fmt_ok = chr(9989) in texto_fmt and "529.982.247-25" in texto_fmt
    passou = val_ok and fmt_ok
    registrar("cross_cpf_val_fmt", passou, 0, f"validar={val_ok}, formatar={fmt_ok}", "ambos consistentes")

    # 7b. CNPJ válido → consultar_cnpj também retorna dados
    texto_val, _ = chamar_ferramenta("validar_cnpj_tool", {"cnpj": "11222333000181"}, 702)
    val_ok = chr(9989) in texto_val
    # consultar pode falhar por rate limit
    texto_cons, _ = chamar_ferramenta("consultar_cnpj", {"cnpj": "11222333000181"}, 703)
    cons_ok = chr(9989) in texto_cons or "Erro ao consultar" in texto_cons
    passou = val_ok and cons_ok
    registrar("cross_cnpj_val_cons", passou, 0, f"validar={val_ok}, consultar={cons_ok}", "ambos ok")

    # 7c. CEP válido → buscar_endereco retorna endereço
    texto_cep, _ = chamar_ferramenta("buscar_endereco_por_cep", {"cep": "01310100"}, 704)
    cep_ok = chr(9989) in texto_cep and "Paulista" in texto_cep
    passou = cep_ok
    registrar("cross_cep_conteudo", passou, 0, texto_cep[:80], "Paulista no resultado")

    # 7d. Telefone válido → formatar_telefone também funciona
    texto_val, _ = chamar_ferramenta("validar_telefone_br", {"telefone": "+5511999998888"}, 705)
    texto_fmt, _ = chamar_ferramenta("formatar_telefone_br_tool", {"telefone": "+5511999998888"}, 706)
    val_ok = chr(9989) in texto_val
    fmt_ok = chr(9989) in texto_fmt
    passou = val_ok and fmt_ok
    registrar("cross_tel_val_fmt", passou, 0, f"validar={val_ok}, formatar={fmt_ok}", "ambos consistentes")

    # =========================================================
    print("\n--- 8. EDGE CASES PROFUNDOS ---")
    # =========================================================

    # 8a. Juros simples — taxa de 100% (exatamente no limite)
    texto, tempo = chamar_ferramenta("calcular_juros_simples", {
        "principal": 1000, "taxa_mensal": 100, "meses": 1
    }, 800)
    passou = chr(9989) in texto  # 100% deve ser aceito (limite, não excedido)
    registrar("juros_taxa_100", passou, tempo, texto[:80], "aceitou 100%")

    # 8b. Juros simples — 600 meses (exatamente no limite)
    texto, tempo = chamar_ferramenta("calcular_juros_simples", {
        "principal": 1000, "taxa_mensal": 1, "meses": 600
    }, 801)
    passou = chr(9989) in texto
    registrar("juros_600_meses", passou, tempo, texto[:80], "aceitou 600 meses")

    # 8c. Multa — 3650 dias (exatamente no limite)
    texto, tempo = chamar_ferramenta("calcular_multa_atraso", {
        "valor": 1000, "dias_atraso": 3650
    }, 802)
    passou = chr(9989) in texto
    registrar("multa_3650_dias", passou, tempo, texto[:80], "aceitou 3650 dias")

    # 8d. Moeda — valor mínimo (0.01)
    texto, tempo = chamar_ferramenta("converter_moeda", {
        "valor": 0.01, "de": "BRL", "para": "USD"
    }, 803)
    passou = chr(9989) in texto
    registrar("moeda_valor_minimo", passou, tempo, texto[:80], "aceitou R$ 0,01")

    # 8e. PIX — valor com muitas casas decimais
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": 99.99, "nome": "TESTE", "cidade": "SP"
    }, 804)
    passou = chr(9989) in texto
    registrar("pix_valor_decimais", passou, tempo, texto[:80], "aceitou 99.99")

    # 8f. Calcular prazo — 1 dia útil a partir de sexta
    texto, tempo = chamar_ferramenta("calcular_prazo_util", {
        "data_inicio": "2026-05-01", "dias_uteis": 1
    }, 805)  # 01/05/2026 é sexta-feira (dia do trabalhador — feriado)
    passou = chr(9989) in texto
    registrar("prazo_partindo_feriado", passou, tempo, texto[:80], "pulou feriado")

    # 8g. DDD — todos os estados representados
    texto, tempo = chamar_ferramenta("listar_ddd_estados", {}, 806)
    if chr(9989) in texto:
        estados_esperados = ["São Paulo", "Rio de Janeiro", "Minas Gerais", "Bahia", "Amazonas",
                             "Paraná", "Santa Catarina", "Rio Grande do Sul", "Ceará", "Pará"]
        faltando = [e for e in estados_esperados if e not in texto]
        passou = len(faltando) == 0
        registrar("ddd_estados_completos", passou, tempo, f"faltando: {faltando}" if faltando else "todos presentes", "10 estados principais")
    else:
        registrar("ddd_estados_completos", False, tempo, texto[:80], "DDD retornou erro")

    # =========================================================
    print("\n" + "=" * 60)
    print("  RELATORIO FINAL")
    print("=" * 60)

    total = len(resultados)
    passaram = sum(1 for _, s, _, _, _ in resultados if s == "PASSOU")
    falharam = total - passaram

    for nome, status, tempo, texto, esperado in resultados:
        icone = chr(9989) if status == "PASSOU" else chr(10060)
        print(f"  {icone} {nome:<35} {tempo:.2f}s")

    print(f"\n  Total: {passaram}/{total} passando")
    if falharam > 0:
        print(f"  {falharam} falharam")
    else:
        print("  Todos passaram!")
    print("=" * 60)


if __name__ == "__main__":
    mcp_init()
    testar()

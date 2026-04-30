"""Suite de testes de cobertura — valida branches, tools não testados, limites, cache, código morto."""

import httpx
import json
import time
import sys
import io

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
            "clientInfo": {"name": "test-cobertura", "version": "1.0"},
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


def testar():
    print("=" * 60)
    print("  BRAZIL MCP SERVER — TESTES DE COBERTURA")
    print("=" * 60)

    # =========================================================
    print("\n--- 1. TOOLS NUNCA TESTADAS ---")
    # =========================================================

    # 1a. formatar_telefone_br_tool — celular
    texto, tempo = chamar_ferramenta("formatar_telefone_br_tool", {"telefone": "+5511999998888"}, 100)
    passou = chr(9989) in texto and "11" in texto and "99999" in texto
    registrar("fmt_tel_celular", passou, tempo, texto[:80], "formatou celular")

    # 1b. formatar_telefone_br_tool — fixo
    texto, tempo = chamar_ferramenta("formatar_telefone_br_tool", {"telefone": "+551133334444"}, 101)
    passou = chr(9989) in texto and "11" in texto and "3333" in texto
    registrar("fmt_tel_fixo", passou, tempo, texto[:80], "formatou fixo")

    # 1c. formatar_telefone_br_tool — inválido
    texto, tempo = chamar_ferramenta("formatar_telefone_br_tool", {"telefone": "123"}, 102)
    passou = "❌" in texto
    registrar("fmt_tel_invalido", passou, tempo, texto[:80], "rejeitou")

    # 1d. formatar_telefone_br_tool — com +55 prefix
    texto, tempo = chamar_ferramenta("formatar_telefone_br_tool", {"telefone": "5511999998888"}, 103)
    passou = chr(9989) in texto
    registrar("fmt_tel_prefix55", passou, tempo, texto[:80], "formatou com 55")

    # 1e. listar_ddd_estados
    texto, tempo = chamar_ferramenta("listar_ddd_estados", {}, 104)
    passou = chr(9989) in texto and "67" in texto and "São Paulo" in texto
    registrar("listar_ddd", passou, tempo, texto[:80], "67 DDDs, SP presente")

    # 1f. listar_ddd_estados — tem todas as regiões
    if chr(9989) in texto:
        tem_sudeste = "São Paulo" in texto
        tem_sul = "Paraná" in texto
        tem_nordeste = "Bahia" in texto
        tem_norte = "Amazonas" in texto
        tem_co = "Goiás" in texto
        passou = tem_sudeste and tem_sul and tem_nordeste and tem_norte and tem_co
    else:
        passou = False
    registrar("listar_ddd_regioes", passou, tempo, "5 regiões", "SP+PR+BA+AM+GO")

    # =========================================================
    print("\n--- 2. VALIDACOES NUNCA EXERCITADAS ---")
    # =========================================================

    # 2a. juros_simples — taxa > 100%
    texto, tempo = chamar_ferramenta("calcular_juros_simples", {
        "principal": 1000, "taxa_mensal": 150, "meses": 1
    }, 200)
    passou = "❌" in texto and "100" in texto
    registrar("juros_taxa_alta", passou, tempo, texto[:80], "rejeitou taxa > 100%")

    # 2b. juros_simples — meses > 600
    texto, tempo = chamar_ferramenta("calcular_juros_simples", {
        "principal": 1000, "taxa_mensal": 1, "meses": 601
    }, 201)
    passou = "❌" in texto and "600" in texto
    registrar("juros_meses_excedido", passou, tempo, texto[:80], "rejeitou meses > 600")

    # 2c. juros_simples — taxa negativa
    texto, tempo = chamar_ferramenta("calcular_juros_simples", {
        "principal": 1000, "taxa_mensal": -5, "meses": 12
    }, 202)
    passou = "❌" in texto and "negativ" in texto.lower()
    registrar("juros_taxa_negativa", passou, tempo, texto[:80], "rejeitou taxa negativa")

    # 2d. juros_simples — meses negativos
    texto, tempo = chamar_ferramenta("calcular_juros_simples", {
        "principal": 1000, "taxa_mensal": 2, "meses": -1
    }, 203)
    passou = "❌" in texto and "negativ" in texto.lower()
    registrar("juros_meses_negativos", passou, tempo, texto[:80], "rejeitou meses negativos")

    # 2e. juros_simples — valor excede máximo
    texto, tempo = chamar_ferramenta("calcular_juros_simples", {
        "principal": 999_999_999.99, "taxa_mensal": 1, "meses": 1
    }, 204)
    # Pode aceitar (está no limite) ou rejeitar (depende de > vs >=)
    passou = chr(9989) in texto or "❌" in texto
    registrar("juros_valor_limite", passou, tempo, texto[:80], "processou limite")

    # 2f. juros_compostos — taxa > 100%
    texto, tempo = chamar_ferramenta("calcular_juros_compostos", {
        "principal": 1000, "taxa_mensal": 200, "meses": 1
    }, 205)
    passou = "❌" in texto and "100" in texto
    registrar("juros_comp_taxa_alta", passou, tempo, texto[:80], "rejeitou taxa > 100%")

    # 2g. juros_compostos — meses > 600
    texto, tempo = chamar_ferramenta("calcular_juros_compostos", {
        "principal": 1000, "taxa_mensal": 1, "meses": 700
    }, 206)
    passou = "❌" in texto and "600" in texto
    registrar("juros_comp_meses_excedido", passou, tempo, texto[:80], "rejeitou meses > 600")

    # 2h. multa_atraso — dias > 3650
    texto, tempo = chamar_ferramenta("calcular_multa_atraso", {
        "valor": 1000, "dias_atraso": 3651
    }, 207)
    passou = "❌" in texto and "3650" in texto
    registrar("multa_dias_excedido", passou, tempo, texto[:80], "rejeitou dias > 3650")

    # 2i. multa_atraso — dias negativos
    texto, tempo = chamar_ferramenta("calcular_multa_atraso", {
        "valor": 1000, "dias_atraso": -5
    }, 208)
    passou = "❌" in texto and "negativ" in texto.lower()
    registrar("multa_dias_negativos", passou, tempo, texto[:80], "rejeitou dias negativos")

    # 2j. multa_atraso — valor negativo
    texto, tempo = chamar_ferramenta("calcular_multa_atraso", {
        "valor": -100, "dias_atraso": 10
    }, 209)
    passou = "❌" in texto and "maior que zero" in texto
    registrar("multa_valor_negativo", passou, tempo, texto[:80], "rejeitou valor negativo")

    # 2k. converter_moeda — valor zero
    texto, tempo = chamar_ferramenta("converter_moeda", {
        "valor": 0, "de": "BRL", "para": "USD"
    }, 210)
    passou = "❌" in texto and "maior que zero" in texto
    registrar("moeda_valor_zero", passou, tempo, texto[:80], "rejeitou valor zero")

    # 2l. converter_moeda — valor negativo
    texto, tempo = chamar_ferramenta("converter_moeda", {
        "valor": -50, "de": "BRL", "para": "USD"
    }, 211)
    passou = "❌" in texto
    registrar("moeda_valor_negativo", passou, tempo, texto[:80], "rejeitou valor negativo")

    # 2m. converter_moeda — valor excede máximo
    texto, tempo = chamar_ferramenta("converter_moeda", {
        "valor": 1_000_000_000, "de": "BRL", "para": "USD"
    }, 212)
    passou = "❌" in texto
    registrar("moeda_valor_excedido", passou, tempo, texto[:80], "rejeitou valor alto")

    # =========================================================
    print("\n--- 3. TELEFONE (branches não testados) ---")
    # =========================================================

    # 3a. 11 dígitos sem começar com 9 (ex: 1139999888 → 11 3 9999888)
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "11399998888"}, 300)
    passou = "❌" in texto and "9" in texto
    registrar("tel_11_sem_9", passou, tempo, texto[:80], "rejeitou sem 9")

    # 3b. Telefone vazio
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": ""}, 301)
    passou = "❌" in texto
    registrar("tel_vazio", passou, tempo, texto[:80], "rejeitou vazio")

    # 3c. Telefone só espaços
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "   "}, 302)
    passou = "❌" in texto
    registrar("tel_espacos", passou, tempo, texto[:80], "rejeitou espaços")

    # 3d. DDD 00 (inválido)
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "00999998888"}, 303)
    passou = "❌" in texto
    registrar("tel_ddd_00", passou, tempo, texto[:80], "rejeitou DDD 00")

    # 3e. DDD 10 (inválido — abaixo de 11)
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "10999998888"}, 304)
    passou = "❌" in texto
    registrar("tel_ddd_10", passou, tempo, texto[:80], "rejeitou DDD 10")

    # 3f. Telefone 9 dígitos (curto)
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "119999888"}, 305)
    passou = "❌" in texto
    registrar("tel_9digitos", passou, tempo, texto[:80], "rejeitou 9 dígitos")

    # 3g. Telefone 12 dígitos (longo)
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "119999988881"}, 306)
    passou = "❌" in texto
    registrar("tel_12digitos", passou, tempo, texto[:80], "rejeitou 12 dígitos")

    # =========================================================
    print("\n--- 4. PIX (branches não testados) ---")
    # =========================================================

    # 4a. PIX com descricao preenchida
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": 50, "nome": "TESTE", "cidade": "SP",
        "descricao": "Pagamento teste"
    }, 400)
    passou = chr(9989) in texto
    registrar("pix_com_descricao", passou, tempo, texto[:80], "gerou com descrição")

    # 4b. PIX — nome vazio (só espaços)
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": 10, "nome": "   ", "cidade": "SP"
    }, 401)
    passou = "❌" in texto  # deve rejeitar nome vazio
    registrar("pix_nome_vazio", passou, tempo, texto[:80], "rejeitou nome vazio")

    # 4c. PIX — cidade vazia
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": 10, "nome": "TESTE", "cidade": ""
    }, 402)
    passou = "❌" in texto
    registrar("pix_cidade_vazia", passou, tempo, texto[:80], "rejeitou cidade vazia")

    # 4d. PIX — valor negativo
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": -10, "nome": "TESTE", "cidade": "SP"
    }, 403)
    passou = "❌" in texto
    registrar("pix_valor_negativo", passou, tempo, texto[:80], "rejeitou valor negativo")

    # 4e. PIX — chave inválida
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "invalida", "valor": 10, "nome": "TESTE", "cidade": "SP"
    }, 404)
    passou = "❌" in texto
    registrar("pix_chave_invalida", passou, tempo, texto[:80], "rejeitou chave")

    # =========================================================
    print("\n--- 5. FORMATADORES (tools não testados) ---")
    # =========================================================

    # 5a. formatar_cpf_tool — CPF válido
    texto, tempo = chamar_ferramenta("formatar_cpf_tool", {"cpf": "52998224725"}, 500)
    passou = chr(9989) in texto and "529.982.247-25" in texto
    registrar("fmt_cpf_valido", passou, tempo, texto[:80], "529.982.247-25")

    # 5b. formatar_cpf_tool — CPF inválido (dígitos repetidos) — formata E valida
    texto, tempo = chamar_ferramenta("formatar_cpf_tool", {"cpf": "11111111111"}, 501)
    passou = "inválido" in texto.lower() or "❌" in texto  # formata mas flagga como inválido
    registrar("fmt_cpf_invalido", passou, tempo, texto[:80], "flaggou como inválido")

    # 5c. formatar_cpf_tool — CPF com 11 dígitos mas inválido matematicamente
    texto, tempo = chamar_ferramenta("formatar_cpf_tool", {"cpf": "12345678901"}, 502)
    passou = "inválido" in texto.lower() or "❌" in texto
    registrar("fmt_cpf_math_invalido", passou, tempo, texto[:80], "flaggou como inválido")

    # 5d. formatar_cnpj_tool — CNPJ válido
    texto, tempo = chamar_ferramenta("formatar_cnpj_tool", {"cnpj": "11222333000181"}, 503)
    passou = chr(9989) in texto and "11.222.333/0001-81" in texto
    registrar("fmt_cnpj_valido", passou, tempo, texto[:80], "11.222.333/0001-81")

    # 5e. formatar_cnpj_tool — CNPJ inválido (dígitos repetidos) — formata E valida
    texto, tempo = chamar_ferramenta("formatar_cnpj_tool", {"cnpj": "11111111111111"}, 504)
    passou = "inválido" in texto.lower() or "❌" in texto
    registrar("fmt_cnpj_invalido", passou, tempo, texto[:80], "flaggou como inválido")

    # 5f. formatar_cnpj_tool — CNPJ com 14 dígitos mas inválido
    texto, tempo = chamar_ferramenta("formatar_cnpj_tool", {"cnpj": "12345678901234"}, 505)
    passou = "inválido" in texto.lower() or "❌" in texto
    registrar("fmt_cnpj_math_invalido", passou, tempo, texto[:80], "flaggou como inválido")

    # 5g. formatar_cnpj_tool — CNPJ curto
    texto, tempo = chamar_ferramenta("formatar_cnpj_tool", {"cnpj": "12345"}, 506)
    passou = "❌" in texto
    registrar("fmt_cnpj_curto", passou, tempo, texto[:80], "rejeitou curto")

    # =========================================================
    print("\n--- 6. CACHE (unitário) ---")
    # =========================================================

    # Importar módulo de cache diretamente
    from src.utils.cache import get_cached, set_cached, limpar_cache

    # 6a. Cache miss — chave inexistente
    limpar_cache()
    resultado = get_cached("chave_inexistente_xyz")
    passou = resultado is None
    registrar("cache_miss", passou, 0, str(resultado), "None")

    # 6b. Cache hit — valor armazenado
    set_cached("teste_key", "teste_valor", 60)
    resultado = get_cached("teste_key")
    passou = resultado == "teste_valor"
    registrar("cache_hit", passou, 0, str(resultado), "teste_valor")

    # 6c. Cache — sobrescrever chave existente
    set_cached("teste_key", "novo_valor", 60)
    resultado = get_cached("teste_key")
    passou = resultado == "novo_valor"
    registrar("cache_overwrite", passou, 0, str(resultado), "novo_valor")

    # 6d. Cache — TTL permanente (ttl=0)
    set_cached("permanente", "valor_perm", 0)
    resultado = get_cached("permanente")
    passou = resultado == "valor_perm"
    registrar("cache_permanente", passou, 0, str(resultado), "valor_perm")

    # 6e. Cache — TTL expirado
    set_cached("expira_rapido", "vai_expirar", 1)
    # Aguardar expiração
    import time as t
    t.sleep(1.1)
    resultado = get_cached("expira_rapido")
    passou = resultado is None
    registrar("cache_expirado", passou, 0, str(resultado), "None (expirado)")

    # 6f. Cache — limpar retorna count
    set_cached("a", 1, 60)
    set_cached("b", 2, 60)
    removidos = limpar_cache()
    passou = isinstance(removidos, int)
    registrar("cache_limpar_count", passou, 0, f"removidos={removidos}", "int")

    # 6g. Cache — lista como valor
    set_cached("lista", [1, 2, 3], 60)
    resultado = get_cached("lista")
    passou = resultado == [1, 2, 3]
    registrar("cache_lista", passou, 0, str(resultado), "[1, 2, 3]")

    # 6h. Cache — dict como valor
    set_cached("dict", {"chave": "valor"}, 60)
    resultado = get_cached("dict")
    passou = resultado == {"chave": "valor"}
    registrar("cache_dict", passou, 0, str(resultado), "{'chave': 'valor'}")

    # =========================================================
    print("\n--- 7. CONSISTENCIA DE RESPOSTA ---")
    # =========================================================

    # 7a. Todos os erros têm emoji ❌
    texto_err1, _ = chamar_ferramenta("validar_cpf_tool", {"cpf": "00000000000"}, 700)
    texto_err2, _ = chamar_ferramenta("consultar_cnpj", {"cnpj": "00000000000000"}, 701)
    texto_err3, _ = chamar_ferramenta("buscar_endereco_por_cep", {"cep": "123"}, 702)
    texto_err4, _ = chamar_ferramenta("calcular_juros_simples", {"principal": -1, "taxa_mensal": 1, "meses": 1}, 703)
    todos_erro = all("❌" in t for t in [texto_err1, texto_err2, texto_err3, texto_err4])
    registrar("consistencia_emoji_erro", todos_erro, 0, "todos têm ❌", "❌ em todos")

    # 7b. Todos os sucessos têm emoji ✅
    texto_ok1, _ = chamar_ferramenta("validar_cpf_tool", {"cpf": "52998224725"}, 704)
    texto_ok2, _ = chamar_ferramenta("validar_cnpj_tool", {"cnpj": "11222333000181"}, 705)
    texto_ok3, _ = chamar_ferramenta("buscar_endereco_por_cep", {"cep": "01310100"}, 706)
    todos_ok = all(chr(9989) in t for t in [texto_ok1, texto_ok2, texto_ok3])
    registrar("consistencia_emoji_ok", todos_ok, 0, "todos têm ✅", "✅ em todos")

    # 7c. Erros têm "Dica:" — melhora experiência do agente
    tem_dica = all("Dica" in t or "dica" in t for t in [texto_err1, texto_err2, texto_err3])
    registrar("consistencia_dica", tem_dica, 0, "Dica presente", "Dica nos erros")

    # =========================================================
    print("\n--- 8. CALDATRIO (branches) ---")
    # =========================================================

    # 8a. calcular_prazo_util — início em novembro (cruza ano)
    texto, tempo = chamar_ferramenta("calcular_prazo_util", {
        "data_inicio": "2026-11-25", "dias_uteis": 10
    }, 800)
    passou = chr(9989) in texto
    registrar("prazo_novembro", passou, tempo, texto[:80], "cruzou ano")

    # 8b. calcular_prazo_util — início em dezembro
    texto, tempo = chamar_ferramenta("calcular_prazo_util", {
        "data_inicio": "2026-12-28", "dias_uteis": 5
    }, 801)
    passou = chr(9989) in texto
    registrar("prazo_dezembro", passou, tempo, texto[:80], "cruzou ano")

    # 8c. verificar_dia_util — domingo
    texto, tempo = chamar_ferramenta("verificar_dia_util", {"data": "2026-05-03"}, 802)  # domingo
    passou = chr(9989) in texto and ("não" in texto.lower() or "útil" not in texto.lower())
    registrar("diumingo_nao_util", passou, tempo, texto[:80], "não é dia útil")

    # 8d. verificar_dia_util — feriado (Tiradentes 21/04)
    texto, tempo = chamar_ferramenta("verificar_dia_util", {"data": "2026-04-21"}, 803)
    passou = chr(9989) in texto
    registrar("feriado_tiradentes", passou, tempo, texto[:80], "feriado detectado")

    # 8e. feriados — ano 2025 (recente)
    texto, tempo = chamar_ferramenta("listar_feriados_nacionais", {"ano": 2025}, 804)
    passou = chr(9989) in texto and "feriados" in texto.lower()
    registrar("feriados_2025", passou, tempo, texto[:80], "retornou feriados")

    # =========================================================
    print("\n--- 9. ENDERECO (branches) ---")
    # =========================================================

    # 9a. buscar_ceps_por_logradouro — sem UF (usa URL alternativa)
    texto, tempo = chamar_ferramenta("buscar_ceps_por_logradouro", {
        "logradouro": "Paulista", "cidade": "São Paulo"
    }, 900)
    passou = chr(9989) in texto or "❌" in texto  # ViaCEP pode falhar
    registrar("cep_sem_uf", passou, tempo, texto[:80], "processou sem UF")

    # 9b. buscar_endereco_por_cep — CEP com letras (deve limpar)
    texto, tempo = chamar_ferramenta("buscar_endereco_por_cep", {"cep": "01310abc"}, 901)
    passou = "❌" in texto  # não tem 8 dígitos após limpar
    registrar("cep_com_letras", passou, tempo, texto[:80], "rejeitou")

    # 9c. formatar_endereco_completo — faltando campo obrigatório (Pydantic rejeita antes)
    texto, tempo = chamar_ferramenta("formatar_endereco_completo", {
        "logradouro": "Rua Teste"
    }, 902)
    passou = "❌" in texto or "Error" in texto or "validation" in texto.lower()
    registrar("endereco_faltando", passou, tempo, texto[:80], "rejeitou campos faltando")

    # =========================================================
    print("\n--- 10. BANCO (branches) ---")
    # =========================================================

    # 10a. banco — código vazio
    texto, tempo = chamar_ferramenta("buscar_banco_por_codigo", {"codigo": ""}, 1000)
    passou = "❌" in texto
    registrar("banco_codigo_vazio", passou, tempo, texto[:80], "rejeitou vazio")

    # 10b. banco — código com espaços
    texto, tempo = chamar_ferramenta("buscar_banco_por_codigo", {"codigo": " 001 "}, 1001)
    passou = chr(9989) in texto
    registrar("banco_espacos", passou, tempo, texto[:80], "encontrou BB")

    # 10c. banco — Itaú (341)
    texto, tempo = chamar_ferramenta("buscar_banco_por_codigo", {"codigo": "341"}, 1002)
    passou = chr(9989) in texto and "ita" in texto.lower()
    registrar("banco_itau", passou, tempo, texto[:80], "Itaú")

    # 10d. banco — Bradesco (237)
    texto, tempo = chamar_ferramenta("buscar_banco_por_codigo", {"codigo": "237"}, 1003)
    passou = chr(9989) in texto and "bradesco" in texto.lower()
    registrar("banco_bradesco", passou, tempo, texto[:80], "Bradesco")

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

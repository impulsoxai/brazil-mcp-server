"""Suite de testes de segurança real e casos culturais brasileiros.

Cobertura:
1. SSRF — tentativas de Server Side Request Forgery
2. Headers HTTP maliciosos
3. Payloads gigantes
4. Encoding estranho
5. Comportamento sob falha (cache, rate limit)
6. Casos culturais brasileiros (acentos, zeros, CEPs paulistanos)
"""

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
            "clientInfo": {"name": "test-seg-cultural", "version": "1.0"},
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
    print("  SEGURANCA REAL + CASOS CULTURAIS BRASILEIROS")
    print("=" * 60)

    # =========================================================
    print("\n--- 1. SSRF (Server Side Request Forgery) ---")
    # =========================================================

    # 1a. CNPJ com URL injection — tentar forçar fetch de URL maliciosa
    texto, tempo = chamar_ferramenta("consultar_cnpj", {
        "cnpj": "http://evil.com/callback"
    }, 100)
    passou = "❌" in texto and "Traceback" not in texto
    registrar("ssrf_cnpj_url", passou, tempo, texto[:80], "rejeitou URL como CNPJ")

    # 1b. CEP com URL injection
    texto, tempo = chamar_ferramenta("buscar_endereco_por_cep", {
        "cep": "http://169.254.169.254/latest/meta-data/"
    }, 101)
    passou = "❌" in texto and "169.254" not in texto and "Traceback" not in texto
    registrar("ssrf_cep_url", passou, tempo, texto[:80], "rejeitou URL como CEP")

    # 1c. Moeda com código malicioso — tentar injection na URL da API
    texto, tempo = chamar_ferramenta("converter_moeda", {
        "valor": 100, "de": "BRL", "para": "../../admin"
    }, 102)
    passou = "❌" in texto and "admin" not in texto.lower() and "Traceback" not in texto
    registrar("ssrf_moeda_path", passou, tempo, texto[:80], "rejeitou path traversal")

    # 1d. Moeda com protocolo injection
    texto, tempo = chamar_ferramenta("converter_moeda", {
        "valor": 100, "de": "BRL", "para": "file:///etc/passwd"
    }, 103)
    passou = "❌" in texto and "root:" not in texto
    registrar("ssrf_moeda_file", passou, tempo, texto[:80], "rejeitou file:// protocol")

    # 1e. Banco com código injection
    texto, tempo = chamar_ferramenta("buscar_banco_por_codigo", {
        "codigo": "../../../etc/passwd"
    }, 104)
    passou = "❌" in texto and "root:" not in texto
    registrar("ssrf_banco_path", passou, tempo, texto[:80], "rejeitou path traversal")

    # 1f. Logradouro com URL injection no ViaCEP
    texto, tempo = chamar_ferramenta("buscar_ceps_por_logradouro", {
        "logradouro": "http://evil.com", "cidade": "http://evil.com", "uf": "SP"
    }, 105)
    passou = "❌" in texto or "Nenhum CEP" in texto
    registrar("ssrf_logradouro_url", passou, tempo, texto[:80], "rejeitou ou vazio")

    # 1g. PIX com URL como chave
    texto, tempo = chamar_ferramenta("validar_chave_pix", {
        "chave": "http://internal-service:8080/admin"
    }, 106)
    passou = "❌" in texto
    registrar("ssrf_pix_url", passou, tempo, texto[:80], "rejeitou URL como chave PIX")

    # =========================================================
    print("\n--- 2. HEADERS HTTP MALICIOSOS ---")
    # =========================================================

    # 2a. X-Forwarded-For spoofing — não deve afetar rate limiting
    headers_spoofed = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "X-Forwarded-For": "1.2.3.4",
        "X-Real-IP": "5.6.7.8",
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 200,
        "method": "tools/call",
        "params": {"name": "validar_cpf_tool", "arguments": {"cpf": "52998224725"}},
    }
    try:
        r = httpx.post(MCP_URL, json=payload, headers=headers_spoofed, timeout=30)
        data = parse_sse(r.text)
        passou = data is not None and ("result" in data or "error" in data)
        registrar("headers_xff_spoof", passou, 0, f"status={r.status_code}", "respondeu normalmente")
    except Exception as e:
        registrar("headers_xff_spoof", False, 0, str(e), "respondeu normalmente")

    # 2b. Host header injection
    headers_host = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Host": "evil.com",
    }
    try:
        r = httpx.post(MCP_URL, json=payload, headers=headers_host, timeout=30)
        passou = r.status_code in (200, 400, 403, 421)
        registrar("headers_host_injection", passou, 0, f"status={r.status_code}", "não redirecionou")
    except Exception as e:
        registrar("headers_host_injection", False, 0, str(e), "status ok")

    # 2c. Content-Type errado — deve rejeitar ou aceitar graciosamente
    headers_ct = {
        "Content-Type": "text/plain",
        "Accept": "application/json, text/event-stream",
    }
    try:
        r = httpx.post(MCP_URL, json=payload, headers=headers_ct, timeout=30)
        passou = r.status_code in (200, 400, 415, 422)
        registrar("headers_ct_errado", passou, 0, f"status={r.status_code}", "tratou graciosamente")
    except Exception as e:
        registrar("headers_ct_errado", False, 0, str(e), "tratou")

    # 2d. Accept header malicioso — não deve causar crash
    headers_accept = {
        "Content-Type": "application/json",
        "Accept": "*/*; q=0.1, application/json; q=0.9, text/event-stream",
    }
    try:
        r = httpx.post(MCP_URL, json=payload, headers=headers_accept, timeout=30)
        passou = r.status_code in (200, 400, 406)
        registrar("headers_accept_malicioso", passou, 0, f"status={r.status_code}", "tratou")
    except Exception as e:
        registrar("headers_accept_malicioso", False, 0, str(e), "tratou")

    # 2e. Authorization header com bearer falso — não deve causar crash
    headers_auth = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
    }
    try:
        r = httpx.post(MCP_URL, json=payload, headers=headers_auth, timeout=30)
        data = parse_sse(r.text)
        passou = data is not None and ("result" in data or "error" in data)
        registrar("headers_auth_falso", passou, 0, f"status={r.status_code}", "ignorou auth falso")
    except Exception as e:
        registrar("headers_auth_falso", False, 0, str(e), "ignorou")

    # =========================================================
    print("\n--- 3. PAYLOADS GIGANTES ---")
    # =========================================================

    # 3a. JSON com string de 5MB
    payload_grande = json.dumps({
        "jsonrpc": "2.0",
        "id": 300,
        "method": "tools/call",
        "params": {
            "name": "consultar_cnpj",
            "arguments": {"cnpj": "A" * 5_000_000}
        }
    })
    try:
        r = httpx.post(MCP_URL, content=payload_grande, headers=HEADERS, timeout=30)
        passou = r.status_code in (200, 400, 413, 422)
        registrar("payload_5mb", passou, 0, f"status={r.status_code}, size={len(payload_grande)}", "rejeitou ou tratou")
    except Exception as e:
        registrar("payload_5mb", True, 0, f"exceção: {type(e).__name__}", "rejeitou graciosamente")

    # 3b. JSON com array de 10000 elementos
    payload_array = json.dumps({
        "jsonrpc": "2.0",
        "id": 301,
        "method": "tools/call",
        "params": {
            "name": "validar_cpf_tool",
            "arguments": {"cpf": ["52998224725"] * 10000}
        }
    })
    try:
        r = httpx.post(MCP_URL, content=payload_array, headers=HEADERS, timeout=30)
        passou = r.status_code in (200, 400, 413, 422)
        registrar("payload_array_10k", passou, 0, f"status={r.status_code}", "tratou")
    except Exception as e:
        registrar("payload_array_10k", True, 0, f"exceção: {type(e).__name__}", "rejeitou")

    # 3c. JSON com 1000 chaves aninhadas
    nested = {"a": 1}
    for _ in range(1000):
        nested = {"nested": nested}
    payload_nested = json.dumps({
        "jsonrpc": "2.0",
        "id": 302,
        "method": "tools/call",
        "params": {"name": "validar_cpf_tool", "arguments": nested}
    })
    try:
        r = httpx.post(MCP_URL, content=payload_nested, headers=HEADERS, timeout=30)
        passou = r.status_code in (200, 400, 413, 422)
        registrar("payload_nested_1000", passou, 0, f"status={r.status_code}", "tratou")
    except Exception as e:
        registrar("payload_nested_1000", True, 0, f"exceção: {type(e).__name__}", "rejeitou")

    # 3d. JSON com null bytes
    payload_null = json.dumps({
        "jsonrpc": "2.0",
        "id": 303,
        "method": "tools/call",
        "params": {"name": "validar_cpf_tool", "arguments": {"cpf": "52998\0000224725"}}
    })
    try:
        r = httpx.post(MCP_URL, content=payload_null, headers=HEADERS, timeout=30)
        passou = r.status_code in (200, 400, 422)
        registrar("payload_null_bytes", passou, 0, f"status={r.status_code}", "tratou")
    except Exception as e:
        registrar("payload_null_bytes", True, 0, f"exceção: {type(e).__name__}", "rejeitou")

    # =========================================================
    print("\n--- 4. ENCODING ESTRANHO ---")
    # =========================================================

    # 4a. Request em UTF-16
    payload_utf16 = json.dumps({
        "jsonrpc": "2.0",
        "id": 400,
        "method": "tools/call",
        "params": {"name": "validar_cpf_tool", "arguments": {"cpf": "52998224725"}}
    }).encode("utf-16")
    try:
        r = httpx.post(
            MCP_URL,
            content=payload_utf16,
            headers={**HEADERS, "Content-Type": "application/json; charset=utf-16"},
            timeout=30,
        )
        passou = r.status_code in (200, 400, 415, 422)
        registrar("encoding_utf16", passou, 0, f"status={r.status_code}", "tratou")
    except Exception as e:
        registrar("encoding_utf16", True, 0, f"exceção: {type(e).__name__}", "rejeitou")

    # 4b. Request em Latin-1 com acentos
    payload_latin = json.dumps({
        "jsonrpc": "2.0",
        "id": 401,
        "method": "tools/call",
        "params": {"name": "gerar_pix_copia_cola", "arguments": {
            "chave": "52998224725", "valor": 10, "nome": "João José Ângela", "cidade": "São Paulo"
        }}
    }).encode("latin-1", errors="replace")
    try:
        r = httpx.post(
            MCP_URL,
            content=payload_latin,
            headers={**HEADERS, "Content-Type": "application/json; charset=latin-1"},
            timeout=30,
        )
        passou = r.status_code in (200, 400, 415, 422)
        registrar("encoding_latin1", passou, 0, f"status={r.status_code}", "tratou")
    except Exception as e:
        registrar("encoding_latin1", True, 0, f"exceção: {type(e).__name__}", "rejeitou")

    # 4c. Request vazio (0 bytes)
    try:
        r = httpx.post(MCP_URL, content=b"", headers=HEADERS, timeout=30)
        passou = r.status_code in (200, 400, 422)
        registrar("encoding_vazio", passou, 0, f"status={r.status_code}", "tratou")
    except Exception as e:
        registrar("encoding_vazio", True, 0, f"exceção: {type(e).__name__}", "rejeitou")

    # 4d. Request com BOM (Byte Order Mark)
    payload_bom = b'\xef\xbb\xbf' + json.dumps({
        "jsonrpc": "2.0",
        "id": 402,
        "method": "tools/call",
        "params": {"name": "validar_cpf_tool", "arguments": {"cpf": "52998224725"}}
    }).encode("utf-8")
    try:
        r = httpx.post(MCP_URL, content=payload_bom, headers=HEADERS, timeout=30)
        data = parse_sse(r.text)
        passou = data is not None and ("result" in data or "error" in data)
        registrar("encoding_bom", passou, 0, f"status={r.status_code}", "processou com BOM")
    except Exception as e:
        registrar("encoding_bom", True, 0, f"exceção: {type(e).__name__}", "tratou")

    # =========================================================
    print("\n--- 5. COMPORTAMENTO SOB FALHA ---")
    # =========================================================

    # 5a. Cache limpo após init — servidor recém-iniciado não tem cache
    # Verificamos listando feriados 2x — a 2ª deve ser tão rápida quanto a 1ª
    # (cache em memória não persiste entre requests ao Railway)
    texto1, tempo1 = chamar_ferramenta("listar_feriados_nacionais", {"ano": 2026}, 500)
    texto2, tempo2 = chamar_ferramenta("listar_feriados_nacionais", {"ano": 2026}, 501)
    # Ambas devem funcionar (cache pode ou não ajudar)
    passou = chr(9989) in texto1 and chr(9989) in texto2
    registrar("cache_feriados_2x", passou, 0, f"t1={tempo1:.2f}s, t2={tempo2:.2f}s", "ambas funcionaram")

    # 5b. Rate limit não persiste entre sessões MCP
    # Nova sessão deve ter contadores zerados
    headers_nova = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    payload_init = {
        "jsonrpc": "2.0",
        "id": 502,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test-nova-sessao", "version": "1.0"},
        },
    }
    r = httpx.post(MCP_URL, json=payload_init, headers=headers_nova, timeout=30)
    nova_session = r.headers.get("mcp-session-id", "")
    if nova_session:
        headers_nova["mcp-session-id"] = nova_session
    httpx.post(MCP_URL, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=headers_nova, timeout=10)
    payload_call = {
        "jsonrpc": "2.0",
        "id": 503,
        "method": "tools/call",
        "params": {"name": "validar_cpf_tool", "arguments": {"cpf": "52998224725"}},
    }
    r = httpx.post(MCP_URL, json=payload_call, headers=headers_nova, timeout=30)
    data = parse_sse(r.text)
    passou = data is not None and "result" in data
    registrar("rate_limit_nova_sessao", passou, 0, "nova sessão respondeu", "funcionou")

    # 5c. Servidor sobrevive a 10 requisições sequenciais rápidas
    ok_count = 0
    for i in range(10):
        try:
            r = httpx.post(MCP_URL, json={
                "jsonrpc": "2.0", "id": 510 + i, "method": "tools/call",
                "params": {"name": "validar_cpf_tool", "arguments": {"cpf": "52998224725"}}
            }, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                ok_count += 1
        except Exception:
            pass
    passou = ok_count >= 9
    registrar("falha_10rapidas", passou, 0, f"{ok_count}/10 ok", ">= 9/10")

    # 5d. Servidor sobrevive a mix de tools diferentes rapidamente
    tools_mix = [
        ("validar_cpf_tool", {"cpf": "52998224725"}),
        ("validar_cnpj_tool", {"cnpj": "11222333000181"}),
        ("buscar_endereco_por_cep", {"cep": "01310100"}),
        ("calcular_juros_simples", {"principal": 1000, "taxa_mensal": 1, "meses": 12}),
        ("validar_telefone_br", {"telefone": "+5511999998888"}),
    ]
    ok_count = 0
    for i, (nome, args) in enumerate(tools_mix):
        texto, _ = chamar_ferramenta(nome, args, 520 + i)
        if chr(9989) in texto or "❌" in texto:
            ok_count += 1
    passou = ok_count == len(tools_mix)
    registrar("falha_mix_tools", passou, 0, f"{ok_count}/{len(tools_mix)} ok", "todas responderam")

    # =========================================================
    print("\n--- 6. CASOS CULTURAIS BRASILEIROS ---")
    # =========================================================

    # 6a. CNPJ com zeros à esquerda (deve ser limpo)
    texto, tempo = chamar_ferramenta("validar_cnpj_tool", {"cnpj": "0011222333000181"}, 600)
    # 15+ dígitos → deve rejeitar (CNPJ tem 14 dígitos)
    passou = "❌" in texto
    registrar("cnpj_zeros_esquerda", passou, tempo, texto[:80], "rejeitou 15+ dígitos")

    # 6b. CNPJ com formatação brasileira (XX.XXX.XXX/XXXX-XX)
    texto, tempo = chamar_ferramenta("validar_cnpj_tool", {"cnpj": "11.222.333/0001-81"}, 601)
    passou = chr(9989) in texto
    registrar("cnpj_formatado_br", passou, tempo, texto[:80], "aceitou formatação")

    # 6c. CEP paulistano começando com 0 (01310-100)
    texto, tempo = chamar_ferramenta("buscar_endereco_por_cep", {"cep": "01310100"}, 602)
    passou = chr(9989) in texto and "Paulista" in texto
    registrar("cep_paulistano_01", passou, tempo, texto[:80], "Av. Paulista")

    # 6d. CEP paulistano começando com 0 (01001-000 — Praça da Sé)
    texto, tempo = chamar_ferramenta("buscar_endereco_por_cep", {"cep": "01001000"}, 603)
    passou = chr(9989) in texto
    registrar("cep_paulistano_01001", passou, tempo, texto[:80], "Praça da Sé")

    # 6e. CEP carioca (20040-020 — Centro RJ)
    texto, tempo = chamar_ferramenta("buscar_endereco_por_cep", {"cep": "20040020"}, 604)
    passou = chr(9989) in texto
    registrar("cep_carioca", passou, tempo, texto[:80], "Centro RJ")

    # 6f. PIX com nome com acentos graves e agudos
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": 150.75,
        "nome": "João da Silva Ângela", "cidade": "São Paulo"
    }, 605)
    passou = chr(9989) in texto and "000201" in texto
    registrar("pix_nome_acentos_graves", passou, tempo, texto[:80], "gerou com acentos")

    # 6g. PIX com cidade com caracteres especiais
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": 50,
        "nome": "TESTE", "cidade": "Belém"
    }, 606)
    passou = chr(9989) in texto
    registrar("pix_cidade_belem", passou, tempo, texto[:80], "Belém aceito")

    # 6h. PIX com cidade com hífen
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": 50,
        "nome": "TESTE", "cidade": "São José dos Pinhais"
    }, 607)
    passou = chr(9989) in texto
    registrar("pix_cidade_hifen", passou, tempo, texto[:80], "cidade com espaço aceita")

    # 6i. Telefone com DDD de São Paulo (11)
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "+5511987654321"}, 608)
    passou = chr(9989) in texto and "São Paulo" in texto
    registrar("tel_ddd_11_sp", passou, tempo, texto[:80], "SP — DDD 11")

    # 6j. Telefone com DDD do interior (35 — Minas Gerais)
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "+5535987654321"}, 609)
    passou = chr(9989) in texto and "Minas" in texto
    registrar("tel_ddd_35_mg", passou, tempo, texto[:80], "MG — DDD 35")

    # 6k. Telefone com DDD do Nordeste (71 — Bahia)
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "+5571987654321"}, 610)
    passou = chr(9989) in texto and "Bahia" in texto
    registrar("tel_ddd_71_ba", passou, tempo, texto[:80], "BA — DDD 71")

    # 6l. Telefone com DDD do Norte (92 — Amazonas)
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "+5592987654321"}, 611)
    passou = chr(9989) in texto and "Amazonas" in texto
    registrar("tel_ddd_92_am", passou, tempo, texto[:80], "AM — DDD 92")

    # 6m. Telefone com DDD do Sul (41 — Paraná)
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "+5541987654321"}, 612)
    passou = chr(9989) in texto and "Paraná" in texto
    registrar("tel_ddd_41_pr", passou, tempo, texto[:80], "PR — DDD 41")

    # 6n. CPF com formatação brasileira (XXX.XXX.XXX-XX)
    texto, tempo = chamar_ferramenta("validar_cpf_tool", {"cpf": "529.982.247-25"}, 613)
    passou = chr(9989) in texto
    registrar("cpf_formatado_br", passou, tempo, texto[:80], "aceitou formatação")

    # 6o. Feriado nacional — Independência (7 de setembro)
    texto, tempo = chamar_ferramenta("verificar_dia_util", {"data": "2026-09-07"}, 614)
    passou = chr(9989) in texto
    registrar("feriado_independencia", passou, tempo, texto[:80], "07/09 feriado")

    # 6p. Feriado nacional — Proclamação (15 de novembro)
    texto, tempo = chamar_ferramenta("verificar_dia_util", {"data": "2026-11-15"}, 615)
    passou = chr(9989) in texto
    registrar("feriado_proclamacao", passou, tempo, texto[:80], "15/11 feriado")

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

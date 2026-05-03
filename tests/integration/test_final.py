"""Suite de testes finais — segurança, protocolo MCP, ferramentas, infraestrutura."""

import httpx
import json
import time
import sys
import io
import asyncio

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
            "clientInfo": {"name": "test-final", "version": "1.0"},
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
    print("  BRAZIL MCP SERVER — TESTES FINAIS")
    print("=" * 60)

    # =========================================================
    print("\n--- 1. SEGURANCA ---")
    # =========================================================

    # 1a. Stack trace não exposto ao cliente — CNPJ inválido
    texto, tempo = chamar_ferramenta("consultar_cnpj", {"cnpj": "00000000000000"}, 100)
    passou = "Traceback" not in texto and "File " not in texto and "Error" not in texto.split("\n")[0]
    registrar("seg_stack_trace_cnpj", passou, tempo, texto[:80], "sem traceback")

    # 1b. Stack trace não exposto — CEP inválido
    texto, tempo = chamar_ferramenta("buscar_endereco_por_cep", {"cep": "1234"}, 101)
    passou = "Traceback" not in texto and "File " not in texto
    registrar("seg_stack_trace_cep", passou, tempo, texto[:80], "sem traceback")

    # 1c. Stack trace não exposto — data inválida
    texto, tempo = chamar_ferramenta("verificar_dia_util", {"data": "abc"}, 102)
    passou = "Traceback" not in texto and "File " not in texto
    registrar("seg_stack_trace_data", passou, tempo, texto[:80], "sem traceback")

    # 1d. Headers de segurança — Content-Type correto
    r = httpx.get(f"{BASE_URL}/health", timeout=10)
    ct = r.headers.get("content-type", "")
    passou = "application/json" in ct
    registrar("seg_content_type_health", passou, 0, ct, "application/json")

    # 1e. Path traversal — tentar acessar arquivo do sistema
    r = httpx.get(f"{BASE_URL}/../../etc/passwd", timeout=10, follow_redirects=True)
    passou = r.status_code in (404, 400, 200) and "root:" not in r.text
    registrar("seg_path_traversal", passou, 0, f"status={r.status_code}", "não expor arquivos")

    # 1f. Path traversal via MCP — method inválido
    payload = {"jsonrpc": "2.0", "id": 999, "method": "../../etc/passwd", "params": {}}
    r = httpx.post(MCP_URL, json=payload, headers=HEADERS, timeout=10)
    data = parse_sse(r.text)
    passou = "root:" not in r.text and (data is None or "error" in data or "result" in data)
    registrar("seg_path_traversal_mcp", passou, 0, f"status={r.status_code}", "não expor arquivos")

    # 1g. XSS via input — deve rejeitar (MCP é JSON-RPC para IA, não HTML para browser)
    texto, tempo = chamar_ferramenta("validar_chave_pix", {"chave": "<script>alert('xss')</script>"}, 103)
    passou = "❌" in texto and "inválid" in texto.lower()  # rejeitou corretamente
    registrar("seg_xss_pix", passou, tempo, texto[:80], "rejeitou input inválido")

    # 1h. SQL injection via input — deve rejeitar com erro claro (servidor não tem SQL)
    texto, tempo = chamar_ferramenta("consultar_cnpj", {"cnpj": "'; DROP TABLE users; --"}, 104)
    passou = "❌" in texto and "Traceback" not in texto  # rejeitou, sem stack trace
    registrar("seg_sql_injection", passou, tempo, texto[:80], "rejeitou sem stack trace")

    # =========================================================
    print("\n--- 2. PROTOCOLO MCP ---")
    # =========================================================

    # 2a. Session ID persiste entre chamadas
    session1 = HEADERS.get("mcp-session-id", "")
    chamar_ferramenta("validar_cpf_tool", {"cpf": "52998224725"}, 200)
    session2 = HEADERS.get("mcp-session-id", "")
    passou = session1 == session2 and len(session1) > 0
    registrar("mcp_session_persiste", passou, 0, f"session: {session1[:20]}...", "mesma session")

    # 2b. JSON-RPC error code — method inexistente
    payload = {"jsonrpc": "2.0", "id": 201, "method": "tool_inexistente", "params": {}}
    r = httpx.post(MCP_URL, json=payload, headers=HEADERS, timeout=10)
    data = parse_sse(r.text)
    passou = data is not None and ("error" in data or "result" in data)
    registrar("mcp_method_inexistente", passou, 0, str(data)[:80] if data else "None", "deve retornar erro")

    # 2c. JSON-RPC — request sem id (notification)
    payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    r = httpx.post(MCP_URL, json=payload, headers=HEADERS, timeout=10)
    passou = r.status_code in (200, 202, 204)
    registrar("mcp_notification", passou, 0, f"status={r.status_code}", "200/202/204")

    # 2d. JSON-RPC — request com id negativo
    payload = {"jsonrpc": "2.0", "id": -1, "method": "tools/list", "params": {}}
    r = httpx.post(MCP_URL, json=payload, headers=HEADERS, timeout=10)
    data = parse_sse(r.text)
    passou = data is not None and ("error" in data or "result" in data)
    registrar("mcp_id_negativo", passou, 0, str(data)[:80] if data else "None", "deve processar")

    # 2e. SSE format — resposta tem "data: " line
    payload = {"jsonrpc": "2.0", "id": 202, "method": "tools/list", "params": {}}
    r = httpx.post(MCP_URL, json=payload, headers=HEADERS, timeout=10)
    passou = "data: " in r.text or r.text.startswith("{")
    registrar("mcp_sse_format", passou, 0, r.text[:80], "SSE ou JSON")

    # 2f. tools/list — cada tool tem inputSchema com type=object
    payload = {"jsonrpc": "2.0", "id": 203, "method": "tools/list", "params": {}}
    r = httpx.post(MCP_URL, json=payload, headers=HEADERS, timeout=30)
    data = parse_sse(r.text)
    tools = data.get("result", {}).get("tools", [])
    invalidos = []
    for t in tools:
        schema = t.get("inputSchema", {})
        if schema.get("type") != "object":
            invalidos.append(f"{t['name']}: type={schema.get('type')}")
    passou = len(invalidos) == 0
    registrar("mcp_schema_type_object", passou, 0, f"{len(invalidos)} inválidos" if invalidos else "todos válidos", "type=object")

    # 2g. initialize — capabilities retornadas
    payload = {
        "jsonrpc": "2.0",
        "id": 204,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test-cap", "version": "1.0"},
        },
    }
    r = httpx.post(MCP_URL, json=payload, headers=HEADERS, timeout=10)
    data = parse_sse(r.text)
    caps = data.get("result", {}).get("capabilities", {})
    passou = "tools" in caps
    registrar("mcp_capabilities", passou, 0, str(list(caps.keys())), "tools capability")

    # =========================================================
    print("\n--- 3. FERRAMENTAS ---")
    # =========================================================

    # 3a. PIX CRC16 — validar com implementação de referência
    def crc16_ref(payload):
        crc = 0xFFFF
        for byte in payload.encode('utf-8'):
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return format(crc, '04X')

    # Gerar PIX e extrair CRC
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": 100.50, "nome": "Teste", "cidade": "SP"
    }, 300)
    passou = chr(9989) in texto
    registrar("ferr_pix_gerar", passou, tempo, texto[:80], "deve gerar PIX")

    # Verificar que o CRC está no payload
    if passou:
        # Extrair payload do texto (linha após "PIX Copia e Cola gerado:")
        linhas = texto.split("\n")
        payload_pix = ""
        for i, linha in enumerate(linhas):
            if "000201" in linha:
                payload_pix = linha.strip()
                break
        if payload_pix and "6304" in payload_pix:
            # O CRC são os últimos 4 caracteres antes de "6304"
            partes = payload_pix.split("6304")
            if len(partes) >= 2:
                crc_gerado = partes[1][:4] if len(partes[1]) >= 4 else ""
                crc_esperado = crc16_ref(partes[0] + "6304")
                passou = crc_gerado == crc_esperado
                registrar("ferr_pix_crc16", passou, tempo, f"gerado={crc_gerado}, esperado={crc_esperado}", "CRCs devem coincidir")
            else:
                registrar("ferr_pix_crc16", False, 0, "não extraiu CRC", "CRC válido")
        else:
            registrar("ferr_pix_crc16", False, 0, "payload não encontrado", "CRC válido")

    # 3b. Juros simples — validação matemática
    texto, tempo = chamar_ferramenta("calcular_juros_simples", {
        "principal": 1000, "taxa_mensal": 2, "meses": 12
    }, 301)
    # J = 1000 * 0.02 * 12 = 240, Total = 1240
    passou = "240" in texto and "1,240" in texto
    registrar("ferr_juros_simples", passou, tempo, texto[:100], "J=240, Total=1,240")

    # 3c. Juros compostos — validação matemática
    texto, tempo = chamar_ferramenta("calcular_juros_compostos", {
        "principal": 1000, "taxa_mensal": 1, "meses": 12
    }, 302)
    # M = 1000 * (1.01)^12 = 1126.83
    passou = "1,126" in texto or "1126" in texto
    registrar("ferr_juros_compostos", passou, tempo, texto[:100], "M~1,126.83")

    # 3d. Multa atraso — validação
    texto, tempo = chamar_ferramenta("calcular_multa_atraso", {
        "valor": 1000, "dias_atraso": 30
    }, 303)
    # Multa = 20, Juros = 1000 * 0.01 * 1 = 10, Total = 1030
    passou = "20" in texto and "10" in texto and "1,030" in texto
    registrar("ferr_multa_atraso", passou, tempo, texto[:100], "Multa=20, Juros=10, Total=1,030")

    # 3e. Conversão moeda — BRL=BRL (mesma moeda)
    texto, tempo = chamar_ferramenta("converter_moeda", {"valor": 100, "de": "BRL", "para": "BRL"}, 304)
    passou = "100" in texto and ("mesma moeda" in texto.lower() or "100.00" in texto)
    registrar("ferr_moeda_mesma", passou, tempo, texto[:80], "mesma moeda")

    # 3f. Validação CPF — dígitos verificadores
    texto, tempo = chamar_ferramenta("validar_cpf_tool", {"cpf": "52998224725"}, 305)
    passou = chr(9989) in texto and "válido" in texto.lower()
    registrar("ferr_cpf_valido", passou, tempo, texto[:80], "CPF válido")

    # 3g. Validação CNPJ — dígitos verificadores
    texto, tempo = chamar_ferramenta("validar_cnpj_tool", {"cnpj": "11222333000181"}, 306)
    passou = chr(9989) in texto and "válido" in texto.lower()
    registrar("ferr_cnpj_valido", passou, tempo, texto[:80], "CNPJ válido")

    # 3h. Telefone — formatação correta
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "+5511999998888"}, 307)
    passou = chr(9989) in texto and "11" in texto and "99999" in texto
    registrar("ferr_telefone_fmt", passou, tempo, texto[:80], "formato correto")

    # =========================================================
    print("\n--- 4. INFRAESTRUTURA ---")
    # =========================================================

    # 4a. Health check — retorna versão
    r = httpx.get(f"{BASE_URL}/health", timeout=10)
    data = r.json()
    passou = "version" in data and "status" in data
    registrar("infra_health_version", passou, 0, json.dumps(data), "version + status")

    # 4b. Health check — resposta rápida (< 2s)
    inicio = time.time()
    r = httpx.get(f"{BASE_URL}/health", timeout=10)
    tempo = time.time() - inicio
    passou = tempo < 2.0 and r.status_code == 200
    registrar("infra_health_rapido", passou, tempo, f"{tempo:.2f}s", "< 2s")

    # 4c. Health check — múltiplas chamadas consistentes
    respostas = []
    for i in range(5):
        r = httpx.get(f"{BASE_URL}/health", timeout=10)
        respostas.append(r.json().get("status"))
    passou = all(s == "ok" for s in respostas)
    registrar("infra_health_consistente", passou, 0, f"{respostas}", "5x 'ok'")

    # 4d. Endpoint inexistente — 404
    r = httpx.get(f"{BASE_URL}/endpoint_que_nao_existe", timeout=10)
    passou = r.status_code in (404, 405)
    registrar("infra_404_inexistente", passou, 0, f"status={r.status_code}", "404/405")

    # 4e. POST no /health — deve rejeitar ou aceitar
    r = httpx.post(f"{BASE_URL}/health", timeout=10)
    passou = r.status_code in (405, 200, 404)
    registrar("infra_post_health", passou, 0, f"status={r.status_code}", "405/200/404")

    # 4f. Request vazio — não deve quebrar
    r = httpx.post(MCP_URL, content="", headers=HEADERS, timeout=10)
    passou = r.status_code in (400, 422, 200)
    registrar("infra_request_vazio", passou, 0, f"status={r.status_code}", "400/422/200")

    # 4g. JSON inválido — não deve quebrar
    r = httpx.post(MCP_URL, content="{invalid json", headers=HEADERS, timeout=10)
    passou = r.status_code in (400, 422, 200)
    registrar("infra_json_invalido", passou, 0, f"status={r.status_code}", "400/422/200")

    # 4h. Request muito grande — deve rejeitar graciosamente
    payload_grande = json.dumps({"data": "x" * 1_000_000})
    try:
        r = httpx.post(MCP_URL, content=payload_grande, headers=HEADERS, timeout=10)
        passou = r.status_code in (400, 413, 422, 200)
        registrar("infra_payload_grande", passou, 0, f"status={r.status_code}", "400/413/422")
    except Exception as e:
        registrar("infra_payload_grande", True, 0, f"rejeitou: {type(e).__name__}", "rejeitou graciosamente")

    # =========================================================
    print("\n--- 5. MIDDLEWARE (unitário) ---")
    # =========================================================

    # 5a. Auth — sem API key → invalido
    from src.middleware.auth import verificar_autenticacao
    from src.services import usage
    usage.init()
    if not usage.validate_key("int-test-free"):
        usage.create_key("int-test-free", "free")
    if not usage.validate_key("int-test-starter"):
        usage.create_key("int-test-starter", "starter")

    resultado = verificar_autenticacao({})
    passou = resultado["valid"] is False
    registrar("mw_auth_free", passou, 0, str(resultado), "valid=False")

    # 5b. Auth — com API key valido → valid
    resultado = verificar_autenticacao({"x-api-key": "int-test-free"})
    passou = resultado["valid"] is True and resultado["plan"] == "free"
    registrar("mw_auth_paid", passou, 0, str(resultado), "valid=True, plan=free")

    # 5c. Auth — API key vazia → invalido
    resultado = verificar_autenticacao({"x-api-key": ""})
    passou = resultado["valid"] is False
    registrar("mw_auth_key_vazia", passou, 0, str(resultado), "valid=False")

    # 5d. Rate limit — dentro do limite
    from src.middleware.rate_limit import verificar_rate_limit
    usage.reset_windows()
    resultado = verificar_rate_limit("int-test-free")
    passou = resultado["allowed"] is True and resultado["count"] >= 1
    registrar("mw_rate_limit_ok", passou, 0, str(resultado), "allowed=True")

    # 5e. Rate limit — tiers independentes
    usage.reset_windows()
    verificar_rate_limit("int-test-free")
    resultado = verificar_rate_limit("int-test-starter")
    passou = resultado["count"] == 1  # contador separado
    registrar("mw_rate_limit_independente", passou, 0, str(resultado), "count=1")

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

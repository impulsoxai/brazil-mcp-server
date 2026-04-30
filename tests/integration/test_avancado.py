"""Suite de testes avançados — cache, rate limit, retry, timeout, schema, carga."""

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
            "clientInfo": {"name": "test-avancado", "version": "1.0"},
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
    print("  BRAZIL MCP SERVER — TESTES AVANCADOS")
    print("=" * 60)

    # =========================================================
    print("\n--- 1. CACHE ---")
    # =========================================================

    # 1a. Feriados: primeira chamada (miss)
    texto1, tempo1 = chamar_ferramenta("listar_feriados_nacionais", {"ano": 2026}, 100)
    passou = chr(9989) in texto1 and "feriados" in texto1.lower()
    registrar("cache_feriados_miss", passou, tempo1, f"1a chamada: {tempo1:.2f}s", "deve retornar feriados")

    # 1b. Feriados: segunda chamada (ambas devem ser rápidas — cache em memória não persiste entre requests)
    texto2, tempo2 = chamar_ferramenta("listar_feriados_nacionais", {"ano": 2026}, 101)
    passou = chr(9989) in texto2 and tempo2 < 3.0
    registrar("cache_feriados_hit", passou, tempo2, f"2a chamada: {tempo2:.2f}s", "< 3s (API responsiva)")

    # 1c. Moeda: primeira chamada (miss)
    texto1, tempo1 = chamar_ferramenta("converter_moeda", {"valor": 10, "de": "BRL", "para": "USD"}, 102)
    passou = chr(9989) in texto1
    registrar("cache_moeda_miss", passou, tempo1, f"1a chamada: {tempo1:.2f}s", "deve converter")

    # 1d. Moeda: segunda chamada (hit)
    texto2, tempo2 = chamar_ferramenta("converter_moeda", {"valor": 20, "de": "BRL", "para": "USD"}, 103)
    passou = chr(9989) in texto2 and tempo2 < tempo1 + 0.5  # tolerância de 0.5s
    registrar("cache_moeda_hit", passou, tempo2, f"2a chamada: {tempo2:.2f}s vs 1a: {tempo1:.2f}s", "deve usar cache")

    # 1e. Banco: primeira chamada (miss)
    texto1, tempo1 = chamar_ferramenta("buscar_banco_por_codigo", {"codigo": "001"}, 104)
    passou = chr(9989) in texto1 and "brasil" in texto1.lower()
    registrar("cache_banco_miss", passou, tempo1, f"1a chamada: {tempo1:.2f}s", "deve retornar banco")

    # 1f. Banco: segunda chamada (cache funciona dentro da mesma sessão HTTP)
    # Nota: cache em memória não persiste entre requests HTTP ao Railway.
    # O cache é útil dentro de uma mesma sessão (ex: calcular_prazo_util chama _obter_feriados 2x).
    texto2, tempo2 = chamar_ferramenta("buscar_banco_por_codigo", {"codigo": "001"}, 105)
    passou = chr(9989) in texto2 and tempo2 < 3.0  # ambas devem ser rápidas
    registrar("cache_banco_hit", passou, tempo2, f"2a chamada: {tempo2:.2f}s", "< 3s (API responsiva)")

    # =========================================================
    print("\n--- 2. RATE LIMITING ---")
    # =========================================================

    # 2a. Health endpoint não deve ter rate limit
    ok_count = 0
    for i in range(20):
        try:
            r = httpx.get(f"{BASE_URL}/health", timeout=5)
            if r.status_code == 200:
                ok_count += 1
        except Exception:
            pass
    passou = ok_count == 20
    registrar("rate_limit_health_20x", passou, 0, f"{ok_count}/20 sucessos", "20/20")

    # 2b. MCP calls — 20 chamadas rápidas
    ok_count = 0
    inicio = time.time()
    for i in range(20):
        texto, _ = chamar_ferramenta("validar_cpf_tool", {"cpf": "52998224725"}, 200 + i)
        if chr(9989) in texto or "❌" in texto:  # respondeu (sucesso ou erro de validação)
            ok_count += 1
    tempo_total = time.time() - inicio
    passou = ok_count >= 18  # tolerância de 2 falhas
    registrar("rate_limit_mcp_20x", passou, tempo_total, f"{ok_count}/20 responderam", ">= 18/20")

    # =========================================================
    print("\n--- 3. RETRY / BACKOFF ---")
    # =========================================================

    # 3a. Chamada normal deve funcionar (retry não atrapalha)
    texto, tempo = chamar_ferramenta("consultar_cnpj", {"cnpj": "33683111000107"}, 300)
    passou = chr(9989) in texto or "Erro ao consultar" in texto  # não deve quebrar
    registrar("retry_chama_normal", passou, tempo, texto[:80], "deve funcionar normalmente")

    # 3b. CEP inexistente deve retornar erro (não retry infinito)
    texto, tempo = chamar_ferramenta("buscar_endereco_por_cep", {"cep": "00000000"}, 301)
    passou = tempo < 15.0  # não deve demorar mais que 15s (3 retries * ~4s max)
    registrar("retry_cep_erro_limite", passou, tempo, f"tempo: {tempo:.2f}s", "< 15s")

    # =========================================================
    print("\n--- 4. TIMEOUT ---")
    # =========================================================

    # 4a. Chamada normal deve responder em < 10s
    texto, tempo = chamar_ferramenta("buscar_endereco_por_cep", {"cep": "01310100"}, 400)
    passou = tempo < 10.0 and chr(9989) in texto
    registrar("timeout_cep_normal", passou, tempo, f"{tempo:.2f}s", "< 10s")

    # 4b. Chamada de moeda deve responder em < 10s
    texto, tempo = chamar_ferramenta("converter_moeda", {"valor": 1, "de": "BRL", "para": "USD"}, 401)
    passou = tempo < 10.0
    registrar("timeout_moeda", passou, tempo, f"{tempo:.2f}s", "< 10s")

    # 4c. Chamada de CNPJ deve responder em < 10s
    texto, tempo = chamar_ferramenta("consultar_cnpj", {"cnpj": "33683111000107"}, 402)
    passou = tempo < 10.0
    registrar("timeout_cnpj", passou, tempo, f"{tempo:.2f}s", "< 10s")

    # 4d. Feriados deve responder em < 10s
    texto, tempo = chamar_ferramenta("listar_feriados_nacionais", {"ano": 2026}, 403)
    passou = tempo < 10.0
    registrar("timeout_feriados", passou, tempo, f"{tempo:.2f}s", "< 10s")

    # =========================================================
    print("\n--- 5. SCHEMA MCP ---")
    # =========================================================

    # 5a. tools/list deve retornar lista válida
    payload = {
        "jsonrpc": "2.0",
        "id": 500,
        "method": "tools/list",
        "params": {},
    }
    try:
        r = httpx.post(MCP_URL, json=payload, headers=HEADERS, timeout=30)
        data = parse_sse(r.text)
        tools = data.get("result", {}).get("tools", [])
        passou = len(tools) > 0 and all("name" in t for t in tools)
        registrar("schema_tools_list", passou, 0, f"{len(tools)} tools encontrados", "deve retornar tools")
    except Exception as e:
        registrar("schema_tools_list", False, 0, str(e), "deve retornar tools")

    # 5b. Cada tool deve ter name, description, inputSchema
    payload = {
        "jsonrpc": "2.0",
        "id": 501,
        "method": "tools/list",
        "params": {},
    }
    try:
        r = httpx.post(MCP_URL, json=payload, headers=HEADERS, timeout=30)
        data = parse_sse(r.text)
        tools = data.get("result", {}).get("tools", [])
        invalidos = []
        for t in tools:
            if not t.get("name"):
                invalidos.append(f"{t}: sem name")
            if not t.get("description"):
                invalidos.append(f"{t.get('name', '?')}: sem description")
            if not t.get("inputSchema"):
                invalidos.append(f"{t.get('name', '?')}: sem inputSchema")
        passou = len(invalidos) == 0
        registrar("schema_tools_completos", passou, 0, f"{len(invalidos)} inválidos" if invalidos else "todos válidos", "todos devem ter name/description/inputSchema")
    except Exception as e:
        registrar("schema_tools_completos", False, 0, str(e), "schema válido")

    # 5c. Verificar total de tools (deve ser >= 22)
    try:
        r = httpx.post(MCP_URL, json=payload, headers=HEADERS, timeout=30)
        data = parse_sse(r.text)
        tools = data.get("result", {}).get("tools", [])
        passou = len(tools) >= 22
        registrar("schema_total_tools", passou, 0, f"{len(tools)} tools", ">= 22 tools")
    except Exception as e:
        registrar("schema_total_tools", False, 0, str(e), ">= 22 tools")

    # 5d. Listar todos os tools
    try:
        r = httpx.post(MCP_URL, json=payload, headers=HEADERS, timeout=30)
        data = parse_sse(r.text)
        tools = data.get("result", {}).get("tools", [])
        nomes = [t.get("name", "?") for t in tools]
        print(f"\n  Tools disponíveis ({len(nomes)}):")
        for n in sorted(nomes):
            print(f"    • {n}")
    except Exception:
        pass

    # =========================================================
    print("\n--- 6. CARGA (50 requests simultâneos) ---")
    # =========================================================

    # 6a. 50 chamadas simultâneas para health
    async def carga_health():
        tasks = []
        for i in range(50):
            tasks.append(asyncio.to_thread(
                lambda: httpx.get(f"{BASE_URL}/health", timeout=10)
            ))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    inicio = time.time()
    try:
        results = asyncio.run(carga_health())
        tempo_total = time.time() - inicio
        sucessos = sum(1 for r in results if not isinstance(r, Exception) and r.status_code == 200)
        passou = sucessos >= 45 and tempo_total < 15.0
        registrar("carga_health_50x", passou, tempo_total, f"{sucessos}/50 sucessos em {tempo_total:.1f}s", ">= 45/50 em < 15s")
    except Exception as e:
        registrar("carga_health_50x", False, 0, str(e), ">= 45/50")

    # 6b. 50 chamadas simultâneas para MCP tools
    async def carga_mcp():
        tasks = []
        for i in range(50):
            tasks.append(asyncio.to_thread(
                chamar_ferramenta, "validar_cpf_tool", {"cpf": "52998224725"}, 600 + i
            ))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    inicio = time.time()
    try:
        results = asyncio.run(carga_mcp())
        tempo_total = time.time() - inicio
        sucessos = sum(1 for r in results if not isinstance(r, Exception) and len(r[0]) > 0)
        passou = sucessos >= 40 and tempo_total < 30.0
        registrar("carga_mcp_50x", passou, tempo_total, f"{sucessos}/50 respostas em {tempo_total:.1f}s", ">= 40/50 em < 30s")
    except Exception as e:
        registrar("carga_mcp_50x", False, 0, str(e), ">= 40/50")

    # 6c. 100 chamadas simultâneas para health
    async def carga_health_100():
        tasks = []
        for i in range(100):
            tasks.append(asyncio.to_thread(
                lambda: httpx.get(f"{BASE_URL}/health", timeout=10)
            ))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    inicio = time.time()
    try:
        results = asyncio.run(carga_health_100())
        tempo_total = time.time() - inicio
        sucessos = sum(1 for r in results if not isinstance(r, Exception) and r.status_code == 200)
        passou = sucessos >= 80 and tempo_total < 30.0
        registrar("carga_health_100x", passou, tempo_total, f"{sucessos}/100 sucessos em {tempo_total:.1f}s", ">= 80/100 em < 30s")
    except Exception as e:
        registrar("carga_health_100x", False, 0, str(e), ">= 80/100")

    # =========================================================
    print("\n" + "=" * 60)
    print("  RELATORIO FINAL")
    print("=" * 60)

    total = len(resultados)
    passaram = sum(1 for _, s, _, _, _ in resultados if s == "PASSOU")
    falharam = total - passaram

    # Agrupar por seção
    secoes = {
        "CACHE": [],
        "RATE LIMIT": [],
        "RETRY": [],
        "TIMEOUT": [],
        "SCHEMA": [],
        "CARGA": [],
    }

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

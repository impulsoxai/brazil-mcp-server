"""Suite de testes de robustez — inputs maliciosos, concorrência e fallback."""

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
            "clientInfo": {"name": "test-robustez", "version": "1.0"},
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
    print("  BRAZIL MCP SERVER — TESTES DE ROBUSTEZ")
    print("=" * 60)

    # =========================================================
    print("\n--- 1. INPUTS MALICIOSOS ---")
    # =========================================================

    # CNPJ com 1000 caracteres
    texto, tempo = chamar_ferramenta("consultar_cnpj", {"cnpj": "1" * 1000}, 100)
    passou = "❌" in texto and "invál" in texto.lower()
    registrar("cnpj_1000_chars", passou, tempo, texto, "deve retornar erro sem quebrar")

    # CEP com caracteres especiais
    texto, tempo = chamar_ferramenta("buscar_endereco_por_cep", {"cep": "!@#$%^&*()"}, 101)
    passou = "❌" in texto and "invál" in texto.lower()
    registrar("cep_caracteres_especiais", passou, tempo, texto, "deve retornar erro sem quebrar")

    # Valor monetário absurdo
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": 999999999999, "nome": "Teste", "cidade": "SP"
    }, 102)
    passou = "❌" in texto and "limite" in texto.lower()
    registrar("valor_monetario_absurdo", passou, tempo, texto, "deve retornar erro de limite")

    # Ano de feriado inválido
    texto, tempo = chamar_ferramenta("listar_feriados_nacionais", {"ano": 9999}, 103)
    passou = "❌" in texto and "invál" in texto.lower()
    registrar("ano_feriado_9999", passou, tempo, texto, "deve retornar erro")

    # Moeda com injection
    texto, tempo = chamar_ferramenta("converter_moeda", {"valor": 100, "de": "BRL'; DROP TABLE", "para": "USD"}, 104)
    passou = "❌" in texto or "erro" in texto.lower() or "invál" in texto.lower()
    registrar("moeda_injection", passou, tempo, texto, "deve retornar erro sem quebrar")

    # Nome PIX com emojis e caracteres especiais
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": 50, "nome": "🔥💀<script>alert('xss')</script>", "cidade": "SP"
    }, 105)
    passou = "✅" in texto or "❌" in texto  # não deve quebrar
    registrar("nome_pix_emojis_xss", passou, tempo, texto, "não deve quebrar")

    # Data com timezone
    texto, tempo = chamar_ferramenta("verificar_dia_util", {"data": "2026-04-29T10:00:00Z"}, 106)
    passou = "❌" in texto and "invál" in texto.lower()
    registrar("data_timezone", passou, tempo, texto, "deve retornar erro")

    # Telefone com 50 dígitos
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "1" * 50}, 107)
    passou = "❌" in texto and "invál" in texto.lower()
    registrar("telefone_50_digitos", passou, tempo, texto, "deve retornar erro")

    # =========================================================
    print("\n--- 2. CONCORRÊNCIA ---")
    # =========================================================

    # 10 chamadas simultâneas para consultar_cnpj
    async def testar_concorrencia_cnpj():
        tasks = []
        for i in range(10):
            tasks.append(asyncio.to_thread(
                chamar_ferramenta, "consultar_cnpj", {"cnpj": "33683111000107"}, 200 + i
            ))
        results = await asyncio.gather(*tasks)
        return results

    inicio = time.time()
    try:
        results = asyncio.run(testar_concorrencia_cnpj())
        tempo_total = time.time() - inicio
        todos_responderam = all(len(r[0]) > 0 for r in results)
        passou = todos_responderam and tempo_total < 10.0
        registrar("conc_cnpj_10x", passou, tempo_total, f"{len(results)} respostas em {tempo_total:.1f}s", "< 10s")
    except Exception as e:
        registrar("conc_cnpj_10x", False, 0, str(e), "< 10s")

    # 10 chamadas simultâneas para converter_moeda
    async def testar_concorrencia_moeda():
        tasks = []
        for i in range(10):
            tasks.append(asyncio.to_thread(
                chamar_ferramenta, "converter_moeda", {"valor": 1, "de": "BRL", "para": "USD"}, 300 + i
            ))
        results = await asyncio.gather(*tasks)
        return results

    inicio = time.time()
    try:
        results = asyncio.run(testar_concorrencia_moeda())
        tempo_total = time.time() - inicio
        todos_responderam = all(len(r[0]) > 0 for r in results)
        passou = todos_responderam and tempo_total < 10.0
        registrar("conc_moeda_10x", passou, tempo_total, f"{len(results)} respostas em {tempo_total:.1f}s", "< 10s")
    except Exception as e:
        registrar("conc_moeda_10x", False, 0, str(e), "< 10s")

    # =========================================================
    print("\n--- 3. FALLBACK ---")
    # =========================================================

    # Erro em ferramenta não deve derrubar servidor
    texto_err, _ = chamar_ferramenta("consultar_cnpj", {"cnpj": "00000000000000"}, 400)
    texto_ok, _ = chamar_ferramenta("validar_cpf_tool", {"cpf": "52998224725"}, 401)
    passou = "✅" in texto_ok or "❌" in texto_ok  # servidor respondeu
    registrar("erro_nao_derruba_servidor", passou, 0, f"err: {texto_err[:50]} | ok: {texto_ok[:50]}", "servidor responde após erro")

    # Health continua respondendo após erros
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=10)
        data = r.json()
        passou = data.get("status") == "ok"
    except Exception:
        passou = False
    registrar("health_pos_erros", passou, 0, "", '{"status": "ok"}')

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

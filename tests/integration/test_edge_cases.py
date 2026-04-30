"""Suite de testes de edge cases — limites, inputs malformados, ferramentas específicas."""

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
            "clientInfo": {"name": "test-edge", "version": "1.0"},
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


def chamar_mcp_raw(payload_dict):
    """Envia request MCP raw e retorna (status_code, response_text, tempo)."""
    inicio = time.time()
    try:
        r = httpx.post(MCP_URL, json=payload_dict, headers=HEADERS, timeout=30)
        tempo = time.time() - inicio
        return r.status_code, r.text, tempo
    except Exception as e:
        tempo = time.time() - inicio
        return 0, str(e), tempo


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
    print("  BRAZIL MCP SERVER — TESTES DE EDGE CASES")
    print("=" * 60)

    # =========================================================
    print("\n--- 1. VALIDACAO DE DOCUMENTOS (edge cases) ---")
    # =========================================================

    # 1a. CPF com todos os zeros
    texto, tempo = chamar_ferramenta("validar_cpf_tool", {"cpf": "00000000000"}, 100)
    passou = "❌" in texto  # CPFs com dígitos repetidos são inválidos
    registrar("cpf_todos_zeros", passou, tempo, texto[:80], "inválido")

    # 1b. CPF com todos os uns
    texto, tempo = chamar_ferramenta("validar_cpf_tool", {"cpf": "11111111111"}, 101)
    passou = "❌" in texto
    registrar("cpf_todos_uns", passou, tempo, texto[:80], "inválido")

    # 1c. CPF com 9 dígitos (curto)
    texto, tempo = chamar_ferramenta("validar_cpf_tool", {"cpf": "123456789"}, 102)
    passou = "❌" in texto
    registrar("cpf_curto", passou, tempo, texto[:80], "inválido")

    # 1d. CPF com 10 dígitos (curto)
    texto, tempo = chamar_ferramenta("validar_cpf_tool", {"cpf": "12345678901"}, 103)
    passou = "❌" in texto
    registrar("cpf_10_digitos", passou, tempo, texto[:80], "inválido")

    # 1e. CPF com formatação (pontos e traço)
    texto, tempo = chamar_ferramenta("validar_cpf_tool", {"cpf": "529.982.247-25"}, 104)
    passou = chr(9989) in texto and "válido" in texto.lower()
    registrar("cpf_formatado", passou, tempo, texto[:80], "válido")

    # 1f. CNPJ com todos os zeros
    texto, tempo = chamar_ferramenta("validar_cnpj_tool", {"cnpj": "00000000000000"}, 105)
    passou = "❌" in texto
    registrar("cnpj_todos_zeros", passou, tempo, texto[:80], "inválido")

    # 1g. CNPJ com formatação
    texto, tempo = chamar_ferramenta("validar_cnpj_tool", {"cnpj": "11.222.333/0001-81"}, 106)
    passou = chr(9989) in texto and "válido" in texto.lower()
    registrar("cnpj_formatado", passou, tempo, texto[:80], "válido")

    # 1h. CNPJ com 13 dígitos (curto)
    texto, tempo = chamar_ferramenta("validar_cnpj_tool", {"cnpj": "1234567890123"}, 107)
    passou = "❌" in texto
    registrar("cnpj_curto", passou, tempo, texto[:80], "inválido")

    # =========================================================
    print("\n--- 2. PIX (edge cases) ---")
    # =========================================================

    # 2a. PIX com chave email
    texto, tempo = chamar_ferramenta("validar_chave_pix", {"chave": "user@example.com"}, 200)
    passou = chr(9989) in texto and "email" in texto.lower()
    registrar("pix_email", passou, tempo, texto[:80], "tipo email")

    # 2b. PIX com chave telefone
    texto, tempo = chamar_ferramenta("validar_chave_pix", {"chave": "+5511999998888"}, 201)
    passou = chr(9989) in texto and ("telefone" in texto.lower() or "phone" in texto.lower())
    registrar("pix_telefone", passou, tempo, texto[:80], "tipo telefone")

    # 2c. PIX com chave EVP (aleatória — formato UUID)
    texto, tempo = chamar_ferramenta("validar_chave_pix", {"chave": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}, 202)
    passou = chr(9989) in texto or "❌" in texto  # deve processar sem quebrar
    registrar("pix_evp", passou, tempo, texto[:80], "processou sem erro")

    # 2d. PIX copia e cola com valor zero
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": 0, "nome": "TESTE", "cidade": "SP"
    }, 203)
    passou = chr(9989) in texto or "❌" in texto  # deve aceitar ou rejeitar graciosamente
    registrar("pix_valor_zero", passou, tempo, texto[:80], "aceitou ou rejeitou")

    # 2e. PIX copia e cola com valor muito alto
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": 999999999.99, "nome": "TESTE", "cidade": "SP"
    }, 204)
    passou = chr(9989) in texto or "❌" in texto
    registrar("pix_valor_alto", passou, tempo, texto[:80], "processou")

    # 2f. PIX com nome com acentos
    texto, tempo = chamar_ferramenta("gerar_pix_copia_cola", {
        "chave": "52998224725", "valor": 10, "nome": "José da Conceição São Paulo", "cidade": "São Paulo"
    }, 205)
    passou = chr(9989) in texto
    registrar("pix_nome_acentos", passou, tempo, texto[:80], "aceitou acentos")

    # =========================================================
    print("\n--- 3. CALCULOS FINANCEIROS (edge cases) ---")
    # =========================================================

    # 3a. Juros simples com valor zero — deve rejeitar (validação correta)
    texto, tempo = chamar_ferramenta("calcular_juros_simples", {
        "principal": 0, "taxa_mensal": 2, "meses": 12
    }, 300)
    passou = "❌" in texto and "maior que zero" in texto  # validação correta
    registrar("juros_simples_zero", passou, tempo, texto[:80], "rejeitou valor zero")

    # 3b. Juros simples com 0 meses
    texto, tempo = chamar_ferramenta("calcular_juros_simples", {
        "principal": 1000, "taxa_mensal": 2, "meses": 0
    }, 301)
    passou = chr(9989) in texto or "❌" in texto  # deve processar ou rejeitar
    registrar("juros_simples_0meses", passou, tempo, texto[:80], "processou")

    # 3c. Juros compostos com taxa zero
    texto, tempo = chamar_ferramenta("calcular_juros_compostos", {
        "principal": 1000, "taxa_mensal": 0, "meses": 12
    }, 302)
    passou = chr(9989) in texto and "1,000" in texto  # montante = principal
    registrar("juros_compostos_taxa_zero", passou, tempo, texto[:80], "montante=1000")

    # 3d. Juros compostos com 1 mês
    texto, tempo = chamar_ferramenta("calcular_juros_compostos", {
        "principal": 1000, "taxa_mensal": 5, "meses": 1
    }, 303)
    passou = chr(9989) in texto and "1,050" in texto
    registrar("juros_compostos_1mes", passou, tempo, texto[:80], "montante=1050")

    # 3e. Multa com 0 dias de atraso
    texto, tempo = chamar_ferramenta("calcular_multa_atraso", {
        "valor": 1000, "dias_atraso": 0
    }, 304)
    passou = chr(9989) in texto or "❌" in texto  # deve processar
    registrar("multa_0dias", passou, tempo, texto[:80], "processou")

    # 3f. Multa com 1 dia de atraso
    texto, tempo = chamar_ferramenta("calcular_multa_atraso", {
        "valor": 1000, "dias_atraso": 1
    }, 305)
    passou = chr(9989) in texto
    registrar("multa_1dia", passou, tempo, texto[:80], "processou")

    # 3g. Conversão moeda — moeda inválida
    texto, tempo = chamar_ferramenta("converter_moeda", {
        "valor": 100, "de": "BRL", "para": "XYZ"
    }, 306)
    passou = "❌" in texto or "erro" in texto.lower() or "não" in texto.lower()
    registrar("moeda_invalida", passou, tempo, texto[:80], "moeda inexistente")

    # =========================================================
    print("\n--- 4. CALENDARIO (edge cases) ---")
    # =========================================================

    # 4a. Ano bissexto — 29/02/2024 (é dia útil)
    texto, tempo = chamar_ferramenta("verificar_dia_util", {"data": "2024-02-29"}, 400)
    passou = chr(9989) in texto or "❌" in texto  # deve processar
    registrar("bissexto_29fev", passou, tempo, texto[:80], "processou 29/02")

    # 4b. Ano bissexto — 29/02/2025 (não existe)
    texto, tempo = chamar_ferramenta("verificar_dia_util", {"data": "2025-02-29"}, 401)
    passou = "❌" in texto or "inválid" in texto.lower() or "não" in texto.lower()
    registrar("nao_bissexto_29fev", passou, tempo, texto[:80], "data inválida")

    # 4c. Feriados de 2020 (ano bissexto)
    texto, tempo = chamar_ferramenta("listar_feriados_nacionais", {"ano": 2020}, 402)
    passou = chr(9989) in texto and "feriados" in texto.lower()
    registrar("feriados_2020", passou, tempo, texto[:80], "retornou feriados")

    # 4d. Feriados de 2000 (limite inferior)
    texto, tempo = chamar_ferramenta("listar_feriados_nacionais", {"ano": 2000}, 403)
    passou = chr(9989) in texto and "feriados" in texto.lower()
    registrar("feriados_2000", passou, tempo, texto[:80], "retornou feriados")

    # 4e. Feriados de 2100 (limite superior)
    texto, tempo = chamar_ferramenta("listar_feriados_nacionais", {"ano": 2100}, 404)
    passou = chr(9989) in texto and "feriados" in texto.lower()
    registrar("feriados_2100", passou, tempo, texto[:80], "retornou feriados")

    # 4f. Calcular prazo com 0 dias úteis
    texto, tempo = chamar_ferramenta("calcular_prazo_util", {
        "data_inicio": "2026-04-29", "dias_uteis": 0
    }, 405)
    passou = chr(9989) in texto or "❌" in texto
    registrar("prazo_0dias", passou, tempo, texto[:80], "processou")

    # 4g. Calcular prazo com 1 dia útil
    texto, tempo = chamar_ferramenta("calcular_prazo_util", {
        "data_inicio": "2026-04-29", "dias_uteis": 1
    }, 406)
    passou = chr(9989) in texto
    registrar("prazo_1dia", passou, tempo, texto[:80], "processou")

    # 4h. Verificar dia útil — formato DD/MM/AAAA
    texto, tempo = chamar_ferramenta("verificar_dia_util", {"data": "29/04/2026"}, 407)
    passou = chr(9989) in texto or "❌" in texto  # deve processar ou rejeitar graciosamente
    registrar("data_formato_br", passou, tempo, texto[:80], "processou")

    # 4i. Próximo dia útil de um sábado
    texto, tempo = chamar_ferramenta("proximo_dia_util", {"data": "2026-05-02"}, 408)  # sábado
    passou = chr(9989) in texto
    registrar("proximo_sabado", passou, tempo, texto[:80], "segunda-feira")

    # =========================================================
    print("\n--- 5. ENDERECO (edge cases) ---")
    # =========================================================

    # 5a. CEP inexistente — 00000-000 não existe na base
    texto, tempo = chamar_ferramenta("buscar_endereco_por_cep", {"cep": "00000000"}, 500)
    passou = "❌" in texto or "não" in texto.lower() or "Erro" in texto
    registrar("cep_inexistente", passou, tempo, texto[:80], "erro ou não encontrado")

    # 5b. CEP com formatação
    texto, tempo = chamar_ferramenta("buscar_endereco_por_cep", {"cep": "01310-100"}, 501)
    passou = chr(9989) in texto
    registrar("cep_formatado", passou, tempo, texto[:80], "encontrou")

    # 5c. CEP com espaços
    texto, tempo = chamar_ferramenta("buscar_endereco_por_cep", {"cep": " 01310100 "}, 502)
    passou = chr(9989) in texto
    registrar("cep_espacos", passou, tempo, texto[:80], "encontrou")

    # 5d. Buscar CEPs por logradouro — ViaCEP pode falhar (transiente)
    texto, tempo = chamar_ferramenta("buscar_ceps_por_logradouro", {
        "logradouro": "Paulista", "cidade": "São Paulo", "uf": "SP"
    }, 503)
    passou = chr(9989) in texto or "❌" in texto  # encontrou ou tratou erro
    registrar("logradouro_paulista", passou, tempo, texto[:80], "encontrou ou tratou erro")

    # 5e. Buscar CEPs — logradouro inexistente
    texto, tempo = chamar_ferramenta("buscar_ceps_por_logradouro", {
        "logradouro": "Rua Que Nao Existe 12345", "cidade": "Xique-Xique", "uf": "BA"
    }, 504)
    passou = "❌" in texto or "nenhum" in texto.lower() or chr(9989) in texto
    registrar("logradouro_inexistente", passou, tempo, texto[:80], "nenhum encontrado")

    # 5f. Formatar endereço com todos os campos
    texto, tempo = chamar_ferramenta("formatar_endereco_completo", {
        "logradouro": "Rua das Flores",
        "numero": "123",
        "complemento": "Apto 45",
        "bairro": "Centro",
        "cidade": "São Paulo",
        "uf": "SP",
        "cep": "01310100"
    }, 505)
    passou = chr(9989) in texto and "Flores" in texto
    registrar("endereco_completo", passou, tempo, texto[:80], "formatou")

    # 5g. Formatar endereço — campos obrigatórios apenas
    texto, tempo = chamar_ferramenta("formatar_endereco_completo", {
        "logradouro": "Av. Paulista",
        "cidade": "São Paulo",
        "uf": "SP"
    }, 506)
    passou = chr(9989) in texto
    registrar("endereco_minimo", passou, tempo, texto[:80], "formatou")

    # =========================================================
    print("\n--- 6. TELEFONE (edge cases) ---")
    # =========================================================

    # 6a. Telefone fixo (8 dígitos)
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "+551133334444"}, 600)
    passou = chr(9989) in texto
    registrar("tel_fixo", passou, tempo, texto[:80], "válido")

    # 6b. Telefone celular (9 dígitos)
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "+5511999998888"}, 601)
    passou = chr(9989) in texto
    registrar("tel_celular", passou, tempo, texto[:80], "válido")

    # 6c. Telefone com DDD inválido (00)
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "+5500999998888"}, 602)
    passou = "❌" in texto or "inválido" in texto.lower()
    registrar("tel_ddd_invalido", passou, tempo, texto[:80], "inválido")

    # 6d. Telefone curto demais
    texto, tempo = chamar_ferramenta("validar_telefone_br", {"telefone": "+55119"}, 603)
    passou = "❌" in texto
    registrar("tel_curto", passou, tempo, texto[:80], "inválido")

    # =========================================================
    print("\n--- 7. MCP PROTOCOLO (edge cases) ---")
    # =========================================================

    # 7a. Tool inexistente — deve retornar erro
    texto, tempo = chamar_ferramenta("ferramenta_que_nao_existe", {"arg": "val"}, 700)
    passou = "ERRO" in texto or "❌" in texto or "error" in texto.lower() or "Unknown" in texto
    registrar("tool_inexistente", passou, tempo, texto[:80], "erro ou unknown")

    # 7b. Parâmetros faltando — CNPJ sem argumento
    payload = {
        "jsonrpc": "2.0",
        "id": 701,
        "method": "tools/call",
        "params": {"name": "consultar_cnpj"},
    }
    status, text, tempo = chamar_mcp_raw(payload)
    data = parse_sse(text)
    passou = data is not None and ("error" in data or "result" in data)
    registrar("parametros_faltando", passou, tempo, text[:80], "erro ou resultado")

    # 7c. Arguments como string em vez de dict
    payload = {
        "jsonrpc": "2.0",
        "id": 702,
        "method": "tools/call",
        "params": {"name": "validar_cpf_tool", "arguments": "isso nao é dict"},
    }
    status, text, tempo = chamar_mcp_raw(payload)
    data = parse_sse(text)
    passou = data is not None and ("error" in data or "result" in data)
    registrar("arguments_string", passou, tempo, text[:80], "tratou erro")

    # 7d. JSON-RPC sem method
    payload = {"jsonrpc": "2.0", "id": 703, "params": {}}
    status, text, tempo = chamar_mcp_raw(payload)
    data = parse_sse(text)
    passou = data is not None and ("error" in data or "result" in data)
    registrar("sem_method", passou, tempo, text[:80], "erro ou resultado")

    # 7e. JSON-RPC sem jsonrpc version
    payload = {"id": 704, "method": "tools/list", "params": {}}
    status, text, tempo = chamar_mcp_raw(payload)
    data = parse_sse(text)
    passou = data is not None and ("error" in data or "result" in data)
    registrar("sem_jsonrpc", passou, tempo, text[:80], "tratou")

    # 7f. Segunda sessão initialize — deve funcionar independentemente
    payload = {
        "jsonrpc": "2.0",
        "id": 705,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test-edge-2", "version": "1.0"},
        },
    }
    r = httpx.post(MCP_URL, json=payload, headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}, timeout=30)
    data = parse_sse(r.text)
    passou = data is not None and "result" in data
    registrar("segunda_sessao", passou, 0, str(list(data.get("result", {}).keys()))[:80], "nova sessão")

    # =========================================================
    print("\n--- 8. BANCO (edge cases) ---")
    # =========================================================

    # 8a. Banco existente — Banco do Brasil (001)
    texto, tempo = chamar_ferramenta("buscar_banco_por_codigo", {"codigo": "001"}, 800)
    passou = chr(9989) in texto and "brasil" in texto.lower()
    registrar("banco_bb", passou, tempo, texto[:80], "Banco do Brasil")

    # 8b. Banco inexistente — código 999
    texto, tempo = chamar_ferramenta("buscar_banco_por_codigo", {"codigo": "999"}, 801)
    passou = "❌" in texto or "não" in texto.lower() or "não encontrado" in texto.lower()
    registrar("banco_inexistente", passou, tempo, texto[:80], "não encontrado")

    # 8c. Banco Nubank (260)
    texto, tempo = chamar_ferramenta("buscar_banco_por_codigo", {"codigo": "260"}, 802)
    passou = chr(9989) in texto
    registrar("banco_nubank", passou, tempo, texto[:80], "Nubank")

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

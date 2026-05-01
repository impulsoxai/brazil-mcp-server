# Guia de Integração — Brazil MCP Server

Endpoint MCP: `POST https://mcp.impulsoxai.com.br/mcp`

O servidor usa o protocolo **MCP Streamable HTTP** com JSON-RPC 2.0. Não é necessário session ID (stateless).

---

## 1. Claude Code

```bash
claude mcp add --transport http brazil-tools https://mcp.impulsoxai.com.br/mcp
```

Ou manualmente na configuração:

```json
{
  "mcpServers": {
    "brazil-tools": {
      "url": "https://mcp.impulsoxai.com.br/mcp"
    }
  }
}
```

Para uso local (desenvolvimento):

```json
{
  "mcpServers": {
    "brazil-tools": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

---

## 2. Claude Desktop

No arquivo `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "brazil-tools": {
      "type": "streamableHttp",
      "url": "https://mcp.impulsoxai.com.br/mcp"
    }
  }
}
```

---

## 3. Cursor / Windsurf

Settings → MCP Servers → Adicionar:

- **Name:** brazil-tools
- **Type:** Streamable HTTP
- **URL:** `https://mcp.impulsoxai.com.br/mcp`

---

## 4. OpenClaw

```yaml
mcp_servers:
  brazil-tools:
    url: https://mcp.impulsoxai.com.br/mcp
    transport: streamable-http
```

---

## 5. Cliente HTTP Direto (curl / Python / Node.js)

O protocolo MCP usa JSON-RPC 2.0. Todas as chamadas são `POST /mcp`.

### Listar ferramentas disponíveis

```bash
curl -X POST https://mcp.impulsoxai.com.br/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/list",
    "params": {}
  }'
```

### Chamar uma ferramenta

```bash
curl -X POST https://mcp.impulsoxai.com.br/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "tools/call",
    "params": {
      "name": "consultar_cnpj",
      "arguments": {"cnpj": "11222333000181"}
    }
  }'
```

### Exemplos prontos

**Consultar CNPJ:**
```bash
curl -X POST https://mcp.impulsoxai.com.br/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"consultar_cnpj","arguments":{"cnpj":"11222333000181"}}}'
```

**Validar CPF:**
```bash
curl -X POST https://mcp.impulsoxai.com.br/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"validar_cpf_tool","arguments":{"cpf":"52998224725"}}}'
```

**Buscar endereço por CEP:**
```bash
curl -X POST https://mcp.impulsoxai.com.br/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"buscar_endereco_por_cep","arguments":{"cep":"01310100"}}}'
```

**Gerar PIX:**
```bash
curl -X POST https://mcp.impulsoxai.com.br/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"gerar_pix_copia_cola","arguments":{"chave":"12345678901","valor":150.00,"nome":"Joao Silva","cidade":"Sao Paulo"}}}'
```

**Converter moeda:**
```bash
curl -X POST https://mcp.impulsoxai.com.br/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"converter_moeda","arguments":{"valor":100,"de":"USD","para":"BRL"}}}'
```

---

### Python (httpx)

```python
import httpx

MCP_URL = "https://mcp.impulsoxai.com.br/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

async def list_tools():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MCP_URL,
            json={"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}},
            headers=HEADERS,
        )
        return response.json()

async def call_tool(name: str, arguments: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MCP_URL,
            json={
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
            headers=HEADERS,
        )
        return response.json()

# Exemplo de uso
result = await call_tool("consultar_cnpj", {"cnpj": "11222333000181"})
print(result)
```

### Node.js (fetch)

```javascript
const MCP_URL = "https://mcp.impulsoxai.com.br/mcp";
const HEADERS = {
  "Content-Type": "application/json",
  Accept: "application/json, text/event-stream",
};

async function callTool(name, arguments) {
  const response = await fetch(MCP_URL, {
    method: "POST",
    headers: HEADERS,
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: "1",
      method: "tools/call",
      params: { name, arguments },
    }),
  });
  return response.json();
}

// Exemplo
const result = await callTool("buscar_endereco_por_cep", { cep: "01310100" });
console.log(result);
```

---

## 6. n8n (HTTP Request Node)

Configure um nó HTTP Request:

- **Method:** `POST`
- **URL:** `https://mcp.impulsoxai.com.br/mcp`
- **Headers:** `Content-Type: application/json`, `Accept: application/json, text/event-stream`
- **Body (JSON):**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": {
    "name": "consultar_cnpj",
    "arguments": {"cnpj": "11222333000181"}
  }
}
```

---

## Ferramentas Disponíveis (22)

### Identidade
| Ferramenta | Descrição |
|---|---|
| `consultar_cnpj` | Dados completos da empresa pelo CNPJ |
| `validar_cnpj_tool` | Valida CNPJ matematicamente |
| `validar_cpf_tool` | Valida CPF matematicamente |
| `formatar_cpf_tool` | Formata CPF com máscara (123.456.789-01) |
| `formatar_cnpj_tool` | Formata CNPJ com máscara (12.345.678/0001-99) |

### Endereço
| Ferramenta | Descrição |
|---|---|
| `buscar_endereco_por_cep` | Endereço completo pelo CEP (BrasilAPI) |
| `buscar_ceps_por_logradouro` | Lista de CEPs por rua/cidade (ViaCEP) |
| `formatar_endereco_completo` | Formata endereço em string legível |

### Pagamentos
| Ferramenta | Descrição |
|---|---|
| `gerar_pix_copia_cola` | Gera payload PIX Copia e Cola (EMV) |
| `validar_chave_pix` | Valida tipo de chave PIX |
| `calcular_juros_simples` | Calcula juros simples (J = P × i × t) |
| `calcular_juros_compostos` | Calcula juros compostos (M = P × (1+i)^t) |
| `calcular_multa_atraso` | Calcula multa e juros de atraso |

### Calendário
| Ferramenta | Descrição |
|---|---|
| `listar_feriados_nacionais` | Feriados nacionais do Brasil por ano |
| `verificar_dia_util` | Verifica se uma data é dia útil |
| `calcular_prazo_util` | Calcula data final com N dias úteis |
| `proximo_dia_util` | Próximo dia útil a partir de uma data |

### Utilidades
| Ferramenta | Descrição |
|---|---|
| `converter_moeda` | Conversão entre moedas em tempo real |
| `validar_telefone_br` | Valida telefone brasileiro |
| `formatar_telefone_br_tool` | Formata telefone com máscara |
| `buscar_banco_por_codigo` | Busca banco pelo código COMPE |
| `listar_ddd_estados` | Mapa completo de DDDs (67 DDDs) |

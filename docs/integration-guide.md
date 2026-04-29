# Guia de Integração — Brazil MCP Server

## 1. Claude Code

Adicione o servidor MCP na configuração do Claude Code:

```json
{
  "mcpServers": {
    "brazil-tools": {
      "url": "https://mcp.impulsoxai.com.br"
    }
  }
}
```

Para uso local (desenvolvimento):

```json
{
  "mcpServers": {
    "brazil-tools": {
      "url": "http://localhost:8000"
    }
  }
}
```

---

## 2. OpenClaw

No OpenClaw, adicione o servidor via configuração de MCP:

```yaml
mcp_servers:
  brazil-tools:
    url: https://mcp.impulsoxai.com.br
    transport: streamable-http
```

---

## 3. n8n (HTTP Request Node)

Para usar as ferramentas via n8n, configure um nó HTTP Request:

**Consultar CNPJ:**
- Method: `POST`
- URL: `https://mcp.impulsoxai.com.br/tools/call`
- Headers: `Content-Type: application/json`
- Body:
```json
{
  "name": "consultar_cnpj",
  "arguments": {
    "cnpj": "11222333000181"
  }
}
```

**Listar ferramentas disponíveis:**
- Method: `GET`
- URL: `https://mcp.impulsoxai.com.br/tools/list`

---

## 4. Cliente HTTP Direto (curl / Python / Node.js)

### curl

```bash
# Listar ferramentas
curl https://mcp.impulsoxai.com.br/tools/list

# Consultar CNPJ
curl -X POST https://mcp.impulsoxai.com.br/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "consultar_cnpj", "arguments": {"cnpj": "11222333000181"}}'

# Buscar endereço por CEP
curl -X POST https://mcp.impulsoxai.com.br/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "buscar_endereco_por_cep", "arguments": {"cep": "01310100"}}'
```

### Python (httpx)

```python
import httpx

async def consultar_cnpj(cnpj: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://mcp.impulsoxai.com.br/tools/call",
            json={"name": "consultar_cnpj", "arguments": {"cnpj": cnpj}},
        )
        return response.json()
```

### Node.js (fetch)

```javascript
async function consultarCNPJ(cnpj) {
  const response = await fetch("https://mcp.impulsoxai.com.br/tools/call", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: "consultar_cnpj",
      arguments: { cnpj },
    }),
  });
  return response.json();
}
```

---

## Ferramentas Disponíveis

| Ferramenta | Descrição |
|---|---|
| `consultar_cnpj` | Dados completos da empresa pelo CNPJ |
| `validar_cnpj_tool` | Valida CNPJ matematicamente |
| `validar_cpf_tool` | Valida CPF matematicamente |
| `formatar_cpf_tool` | Formata CPF com máscara |
| `formatar_cnpj_tool` | Formata CNPJ com máscara |
| `buscar_endereco_por_cep` | Endereço completo pelo CEP |
| `buscar_ceps_por_logradouro` | Lista de CEPs por rua/cidade |
| `formatar_endereco_completo` | Formata endereço em string legível |

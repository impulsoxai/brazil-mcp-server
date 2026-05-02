# 🇧🇷 Brazil MCP Server

![version](https://img.shields.io/badge/version-0.1.0-blue)
![tools](https://img.shields.io/badge/tools-22-green)
![tests](https://img.shields.io/badge/tests-22%2F22-brightgreen)
![license](https://img.shields.io/badge/license-MIT-brightgreen)
![python](https://img.shields.io/badge/python-3.11+-3776AB)

**English** | [Português](#português)

MCP Server with 22 native Brazilian tools for AI agents. Connect any MCP-compatible agent to Brazilian data sources — CNPJ, CPF, CEP, PIX, currency, holidays, and more.

Built by [ImpulsoX AI](https://impulsoxai.com.br) — the Brazilian AI agents company.

---

## Quick Start

Add to your Claude Code or MCP client config:

```json
{
  "mcpServers": {
    "brazil-tools": {
      "url": "https://mcp.impulsoxai.com.br/mcp"
    }
  }
}
```

That's it. Your agent now has access to all 22 Brazilian tools.

---

## Available Tools

### Identity (`identidade`) — 5 tools
| Tool | Description |
|---|---|
| `consultar_cnpj` | Full company data from Brazilian tax registry (CNPJ) |
| `validar_cnpj_tool` | Mathematically validate a CNPJ |
| `validar_cpf_tool` | Mathematically validate a CPF |
| `formatar_cpf_tool` | Format CPF with Brazilian mask (123.456.789-01) |
| `formatar_cnpj_tool` | Format CNPJ with Brazilian mask (12.345.678/0001-99) |

### Address (`endereco`) — 3 tools
| Tool | Description |
|---|---|
| `buscar_endereco_por_cep` | Full address from ZIP code (CEP) via BrasilAPI |
| `buscar_ceps_por_logradouro` | Find ZIP codes by street name and city via ViaCEP |
| `formatar_endereco_completo` | Format complete Brazilian address as readable string |

### Payments (`pagamentos`) — 5 tools
| Tool | Description |
|---|---|
| `gerar_pix_copia_cola` | Generate PIX Copia e Cola payload (EMV standard) |
| `validar_chave_pix` | Validate PIX key type (CPF, CNPJ, email, phone, UUID) |
| `calcular_juros_simples` | Simple interest calculation (J = P × i × t) |
| `calcular_juros_compostos` | Compound interest calculation (M = P × (1+i)^t) |
| `calcular_multa_atraso` | Late payment fine calculator (2% fine + 1%/month pro rata) |

### Calendar (`calendario`) — 4 tools
| Tool | Description |
|---|---|
| `listar_feriados_nacionais` | List Brazilian national holidays for a given year |
| `verificar_dia_util` | Check if a date is a business day in Brazil |
| `calcular_prazo_util` | Calculate deadline by adding N business days |
| `proximo_dia_util` | Get next business day from a given date |

### Utilities (`utilidades`) — 5 tools
| Tool | Description |
|---|---|
| `converter_moeda` | Convert between currencies using real-time exchange rates |
| `validar_telefone_br` | Validate Brazilian phone number (DDD, length, mobile digit) |
| `formatar_telefone_br_tool` | Format Brazilian phone with mask ((11) 99999-8888) |
| `buscar_banco_por_codigo` | Look up Brazilian bank by COMPE code via BrasilAPI |
| `listar_ddd_estados` | Complete DDD-to-state mapping (67 DDDs) |

---

## Usage Examples

### Validate a CPF
```json
{"name": "validar_cpf_tool", "arguments": {"cpf": "529.982.247-25"}}
```
Response: `✅ CPF 529.982.247-25 é válido.`

### Look up an address by CEP
```json
{"name": "buscar_endereco_por_cep", "arguments": {"cep": "01310-100"}}
```
Response: `✅ Endereço encontrado: Avenida Paulista, 1578 — Bela Vista, São Paulo/SP`

### Generate a PIX QR code
```json
{"name": "gerar_pix_copia_cola", "arguments": {
  "chave": "11222333000181",
  "valor": 150.00,
  "nome": "Empresa LTDA",
  "cidade": "Sao Paulo"
}}
```
Response: `✅ PIX Copia e Cola gerado: 00020126580014br.gov.bcb.pix...`

### Check if a date is a business day
```json
{"name": "verificar_dia_util", "arguments": {"data": "2026-01-01"}}
```
Response: `❌ 01/01/2026 não é dia útil (Confraternização Universal).`

### Convert currency
```json
{"name": "converter_moeda", "arguments": {"valor": 100, "de": "BRL", "para": "USD"}}
```
Response: `✅ R$ 100.00 = USD 19.52 (taxa: 0.1952)`

---

## Connecting from Code

The server uses the MCP Streamable HTTP protocol. Endpoint: `POST /mcp`

### curl

```bash
# List all tools
curl -X POST https://mcp.impulsoxai.com.br/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}'

# Call a tool
curl -X POST https://mcp.impulsoxai.com.br/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"validar_cpf_tool","arguments":{"cpf":"52998224725"}}}'
```

### Python

```python
import httpx

async def call_tool(name: str, arguments: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://mcp.impulsoxai.com.br/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
            headers={"Accept": "application/json, text/event-stream"},
        )
        return response.json()
```

### Claude Code CLI

```bash
claude mcp add --transport http brazil-tools https://mcp.impulsoxai.com.br/mcp
```

---

## Self Hosting

```bash
git clone https://github.com/impulsoxai/brazil-mcp-server
cd brazil-mcp-server
cp .env.example .env
pip install -e .
python -m src.main
```

The server starts on `http://localhost:8000/mcp` by default.

---

## License

MIT — free to use, modify, and distribute.

---

---

## Português

![version](https://img.shields.io/badge/versão-0.1.0-blue)
![tools](https://img.shields.io/badge/ferramentas-22-green)
![tests](https://img.shields.io/badge/testes-22%2F22-brightgreen)

Servidor MCP com 22 ferramentas brasileiras nativas para agentes de IA. Conecte qualquer agente compatível com MCP a dados brasileiros — CNPJ, CPF, CEP, PIX, moedas, feriados e muito mais.

Construído pela [ImpulsoX AI](https://impulsoxai.com.br).

### Início Rápido

Adicione na configuração do Claude Code ou do seu cliente MCP:

```json
{
  "mcpServers": {
    "brazil-tools": {
      "url": "https://mcp.impulsoxai.com.br/mcp"
    }
  }
}
```

Pronto. Seu agente já tem acesso a todas as 22 ferramentas brasileiras.

### Ferramentas Disponíveis

**Identidade** — `consultar_cnpj`, `validar_cnpj_tool`, `validar_cpf_tool`, `formatar_cpf_tool`, `formatar_cnpj_tool`

**Endereço** — `buscar_endereco_por_cep`, `buscar_ceps_por_logradouro`, `formatar_endereco_completo`

**Pagamentos** — `gerar_pix_copia_cola`, `validar_chave_pix`, `calcular_juros_simples`, `calcular_juros_compostos`, `calcular_multa_atraso`

**Calendário** — `listar_feriados_nacionais`, `verificar_dia_util`, `calcular_prazo_util`, `proximo_dia_util`

**Utilidades** — `converter_moeda`, `validar_telefone_br`, `formatar_telefone_br_tool`, `buscar_banco_por_codigo`, `listar_ddd_estados`

### Conectando via Código

O servidor usa o protocolo MCP Streamable HTTP. Endpoint: `POST /mcp`

```bash
# Listar ferramentas
curl -X POST https://mcp.impulsoxai.com.br/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}'

# Chamar uma ferramenta
curl -X POST https://mcp.impulsoxai.com.br/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"consultar_cnpj","arguments":{"cnpj":"11222333000181"}}}'
```

### Por que isso existe?

Agentes de IA como Claude, ChatGPT e outros não conseguem, por padrão, acessar dados brasileiros em tempo real. Sem um MCP Server especializado, um agente não consegue:

- Verificar se um CNPJ é válido e ativo
- Buscar o endereço de um CEP
- Gerar um PIX Copia e Cola
- Calcular juros ou multa de atraso
- Converter moedas em tempo real
- Saber se amanhã é feriado

O Brazil MCP Server resolve isso em uma linha de configuração.

### Contato

- Site: [impulsoxai.com.br](https://impulsoxai.com.br)
- Email: impulsoxai@gmail.com
- GitHub: [@impulsoxai](https://github.com/impulsoxai)

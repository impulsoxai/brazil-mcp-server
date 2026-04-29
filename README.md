# 🇧🇷 Brazil MCP Server

**English** | [Português](#português)

MCP Server with native Brazilian APIs for AI agents. Connect any MCP-compatible agent to Brazilian data sources — CNPJ, CPF, CEP, PIX, holidays, and more.

Built by [ImpulsoX AI](https://impulsoxai.com.br) — the Brazilian AI agents company.

---

## Quick Start

Add to your Claude Code or MCP client config:

```json
{
  "mcpServers": {
    "brazil-tools": {
      "url": "https://mcp.impulsoxai.com.br"
    }
  }
}
```

That's it. Your agent now has access to all Brazilian tools.

---

## Available Tools

### Identity (`identidade`)
| Tool | Description |
|---|---|
| `consultar_cnpj` | Full company data from Brazilian tax registry |
| `validar_cnpj_tool` | Mathematically validate a CNPJ |
| `validar_cpf_tool` | Mathematically validate a CPF |
| `formatar_cpf_tool` | Format CPF with Brazilian mask |
| `formatar_cnpj_tool` | Format CNPJ with Brazilian mask |

### Address (`endereco`)
| Tool | Description |
|---|---|
| `buscar_endereco_por_cep` | Full address from ZIP code (CEP) |
| `buscar_ceps_por_logradouro` | Find ZIP codes by street name and city |
| `formatar_endereco_completo` | Format complete Brazilian address |

*More tools coming in Sprint 2 (PIX, holidays) and Sprint 3 (currency, phone)*

---

## Self Hosting

```bash
git clone https://github.com/impulsoxai/brazil-mcp-server
cd brazil-mcp-server
cp .env.example .env
pip install -e .
python -m src.main
```

See [docs/self-hosting.md](docs/self-hosting.md) for full instructions.

---

## License

MIT — free to use, modify, and distribute.

---

---

## Português

Servidor MCP com APIs brasileiras nativas para agentes de IA. Conecte qualquer agente compatível com MCP a dados brasileiros — CNPJ, CPF, CEP, PIX, feriados e muito mais.

Construído pela [ImpulsoX AI](https://impulsoxai.com.br).

### Início Rápido

Adicione na configuração do Claude Code ou do seu cliente MCP:

```json
{
  "mcpServers": {
    "brazil-tools": {
      "url": "https://mcp.impulsoxai.com.br"
    }
  }
}
```

Pronto. Seu agente já tem acesso a todas as ferramentas brasileiras.

### Por que isso existe?

Agentes de IA como Claude, ChatGPT e outros não conseguem, por padrão, acessar dados brasileiros em tempo real. Sem um MCP Server especializado, um agente não consegue:

- Verificar se um CNPJ é válido e ativo
- Buscar o endereço de um CEP
- Gerar um PIX Copia e Cola
- Saber se amanhã é feriado

O Brazil MCP Server resolve isso em uma linha de configuração.

### Contribuindo

PRs são bem-vindos! Veja [CONTRIBUTING.md](CONTRIBUTING.md) para o guia de contribuição.

### Contato

- Site: [impulsoxai.com.br](https://impulsoxai.com.br)
- Email: (impulsoxai@gmail.com)
- GitHub: [@impulsoxai](https://github.com/impulsoxai)

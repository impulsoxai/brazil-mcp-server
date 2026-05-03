# CLAUDE.md — Brazil MCP Server

## Visão Geral do Projeto

**Brazil MCP Server** é um servidor MCP (Model Context Protocol) especializado em APIs e dados brasileiros.
Permite que qualquer agente de IA (Claude, ChatGPT, OpenClaw, n8n, etc.) acesse ferramentas brasileiras
nativas — CNPJ, CPF, CEP, PIX, feriados, impostos — via protocolo padronizado.

**Repositório:** https://github.com/impulsoxai/brazil-mcp-server  
**Produção:** https://mcp.impulsoxai.com.br  
**Mantido por:** ImpulsoX AI

---

## Stack Técnico

| Componente | Tecnologia | Motivo |
|---|---|---|
| Linguagem | Python 3.11+ | Suporte oficial MCP, mais legível |
| Framework MCP | FastMCP (via `mcp` SDK) | Menos boilerplate, decoradores limpos |
| HTTP Client | `httpx` | Async nativo, melhor que requests |
| Validação | `pydantic` | Tipagem forte, erros claros |
| Servidor HTTP | `uvicorn` | ASGI, produção-ready |
| Deploy | Railway | CI/CD automático, domínio customizado |
| Testes | `pytest` + `pytest-asyncio` | Padrão Python async |

---

## Arquitetura de Pastas

```
brazil-mcp-server/
│
├── CLAUDE.md                    ← VOCÊ ESTÁ AQUI — leia antes de qualquer coisa
├── README.md                    ← Documentação pública (inglês + português)
├── ROADMAP.md                   ← Módulos planejados e status
├── CONTRIBUTING.md              ← Guia para contribuidores externos
├── LICENSE                      ← MIT License
│
├── pyproject.toml               ← Dependências e configuração do projeto
├── railway.json                 ← Configuração de deploy Railway
├── Procfile                     ← Comando de start para Railway
├── .env.example                 ← Variáveis de ambiente necessárias
├── .gitignore                   ← Arquivos ignorados pelo git
│
├── src/
│   ├── main.py                  ← Entry point — inicializa o servidor MCP
│   ├── config.py                ← Configurações globais (env vars, constantes)
│   │
│   ├── tools/                   ← Cada arquivo = um módulo de ferramentas
│   │   ├── __init__.py
│   │   ├── identidade.py        ← CNPJ, CPF, validações de identidade
│   │   ├── endereco.py          ← CEP, endereço, coordenadas
│   │   ├── pagamentos.py        ← PIX, cálculos financeiros
│   │   ├── calendario.py        ← Feriados, datas úteis, prazo bancário
│   │   └── utilidades.py        ← Moeda, telefone, formatações BR
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py              ← Validação de API key (tier free vs pago)
│   │   ├── rate_limit.py        ← Rate limiting por API key
│   │   └── logging.py           ← Logs estruturados (não usa stdout em STDIO)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── http_client.py       ← Cliente HTTP compartilhado com retry/timeout
│       ├── formatters.py        ← Formatação de CPF, CNPJ, telefone, CEP
│       └── validators.py        ← Validação matemática de CPF, CNPJ
│
├── tests/
│   ├── conftest.py              ← Fixtures compartilhadas
│   ├── tools/
│   │   ├── test_identidade.py
│   │   ├── test_endereco.py
│   │   ├── test_pagamentos.py
│   │   └── test_calendario.py
│   └── integration/
│       └── test_server.py       ← Testa o servidor MCP completo
│
├── docs/
│   ├── tools-reference.md       ← Referência de todas as ferramentas disponíveis
│   ├── integration-guide.md     ← Como integrar em Claude Code, n8n, OpenClaw
│   └── self-hosting.md          ← Como hospedar você mesmo
│
└── .github/
    └── workflows/
        └── deploy.yml           ← CI/CD: testa e faz deploy no Railway no push
```

---

## Módulos e Ferramentas

### Módulo 1 — `identidade.py` (Sprint 1 — CONSTRUIR PRIMEIRO)
| Ferramenta | O que faz | API |
|---|---|---|
| `consultar_cnpj` | Dados completos da empresa | BrasilAPI |
| `validar_cnpj` | Valida matematicamente o CNPJ | Local (sem API) |
| `validar_cpf` | Valida matematicamente o CPF | Local (sem API) |
| `formatar_cpf` | Formata CPF com máscara | Local |
| `formatar_cnpj` | Formata CNPJ com máscara | Local |

### Módulo 2 — `endereco.py` (Sprint 1)
| Ferramenta | O que faz | API |
|---|---|---|
| `buscar_endereco_por_cep` | Endereço completo pelo CEP | BrasilAPI |
| `buscar_ceps_por_logradouro` | Lista de CEPs por rua/cidade | BrasilAPI |
| `formatar_endereco` | Formata endereço em string legível | Local |

### Módulo 3 — `pagamentos.py` (Sprint 2)
| Ferramenta | O que faz | API |
|---|---|---|
| `gerar_pix_copia_cola` | Gera payload PIX estático | Local (spec PIX) |
| `validar_chave_pix` | Valida tipo e formato de chave PIX | Local |
| `calcular_juros_simples` | Juros simples com prazo | Local |
| `calcular_juros_compostos` | Juros compostos com prazo | Local |
| `calcular_multa_atraso` | Multa + juros padrão BR | Local |

### Módulo 4 — `calendario.py` (Sprint 2)
| Ferramenta | O que faz | API |
|---|---|---|
| `listar_feriados_nacionais` | Feriados nacionais por ano | BrasilAPI |
| `verificar_dia_util` | Verifica se data é dia útil | BrasilAPI + local |
| `calcular_prazo_util` | Soma N dias úteis a uma data | Local |
| `proximo_dia_util` | Próximo dia útil de uma data | Local |

### Módulo 5 — `utilidades.py` (Sprint 3)
| Ferramenta | O que faz | API |
|---|---|---|
| `converter_moeda` | Converte BRL para qualquer moeda | AwesomeAPI |
| `validar_telefone_br` | Valida número brasileiro | Local |
| `formatar_telefone_br` | Formata com DDD e máscara | Local |
| `buscar_banco_por_codigo` | Nome do banco pelo código COMPE | BrasilAPI |
| `listar_ddd_estados` | Estado e região por DDD | Local |

---

## Regras de Desenvolvimento

### 1. Docstrings são obrigatórias e críticas
O agente de IA lê a docstring para decidir QUANDO e COMO usar a ferramenta.
Escreva sempre em português, claro e específico.

```python
# ❌ RUIM — genérico demais
async def consultar_cnpj(cnpj: str) -> str:
    """Consulta CNPJ."""

# ✅ BOM — o agente sabe exatamente o que esperar
async def consultar_cnpj(cnpj: str) -> str:
    """
    Consulta dados cadastrais completos de uma empresa brasileira pelo CNPJ.
    
    Use quando precisar verificar: razão social, nome fantasia, situação cadastral
    (ativa/inativa/suspensa), endereço completo, CNAE principal, porte da empresa,
    data de abertura e QSA (quadro de sócios).
    
    O CNPJ pode ser enviado com ou sem formatação (14 dígitos ou XX.XXX.XXX/XXXX-XX).
    Retorna erro descritivo se o CNPJ for inválido ou a empresa não for encontrada.
    """
```

### 2. Nunca use `print()` ou `console.log()` em modo STDIO
Use sempre `sys.stderr` ou o logger configurado em `src/middleware/logging.py`.

```python
# ❌ NUNCA — quebra o protocolo MCP em modo STDIO
print("Consultando CNPJ...")

# ✅ SEMPRE
import sys
print("Consultando CNPJ...", file=sys.stderr)
```

### 3. Tratamento de erro em português
Erros devem ser informativos para o agente agir corretamente.

```python
# ❌ RUIM
return "Error 404"

# ✅ BOM
return "CNPJ não encontrado na base da Receita Federal. Verifique se o número está correto e tente novamente."
```

### 4. Sempre limpe os inputs antes de processar
CPF, CNPJ, CEP e telefone chegam em formatos variados. Normalize primeiro.

```python
def limpar_numeros(valor: str) -> str:
    """Remove tudo que não for dígito."""
    return ''.join(filter(str.isdigit, valor))
```

### 5. Timeout em todas as chamadas de API externa
Nunca deixe uma chamada HTTP sem timeout — o agente vai travar.

```python
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.get(url)
```

---

## Variáveis de Ambiente

Todas definidas em `.env` (nunca commitar) e documentadas em `.env.example`:

```
# Obrigatórias
MCP_ENV=production                    # production | development
MCP_PORT=8000                         # porta do servidor

# APIs externas (todas gratuitas no tier básico)
BRASIL_API_BASE=https://brasilapi.com.br/api
AWESOME_API_BASE=https://economia.awesomeapi.com.br

# Monitoramento (opcional)
SENTRY_DSN=                           # deixar vazio em development
```

---

## Fluxo de Deploy

```
Push para main no GitHub
        ↓
GitHub Actions roda os testes (pytest)
        ↓
Se testes passam → Railway faz deploy automático
        ↓
https://mcp.impulsoxai.com.br atualizado em ~2 minutos
```

---

## Ordem de Construção (Sprints)

### Sprint 1 — MVP (Construir agora)
- [ ] `pyproject.toml` com todas as dependências
- [ ] `src/config.py` com variáveis de ambiente
- [ ] `src/utils/formatters.py` e `validators.py`
- [ ] `src/utils/http_client.py`
- [ ] `src/tools/identidade.py` (5 ferramentas)
- [ ] `src/tools/endereco.py` (3 ferramentas)
- [ ] `src/main.py` conectando tudo
- [ ] `tests/tools/test_identidade.py`
- [ ] `tests/tools/test_endereco.py`
- [ ] `railway.json` + `Procfile`
- [ ] `.env.example`
- [ ] `README.md` bilíngue

### Sprint 2 — Pagamentos e Calendário
- [ ] `src/tools/pagamentos.py` (5 ferramentas)
- [ ] `src/tools/calendario.py` (4 ferramentas)
- [ ] Testes correspondentes

### Sprint 3 — Utilidades + Monetização
- [ ] `src/tools/utilidades.py` (5 ferramentas)
- [ ] `src/middleware/auth.py` (API keys)
- [ ] `src/middleware/rate_limit.py`
- [ ] `docs/integration-guide.md`
- [ ] `.github/workflows/deploy.yml`

---

## APIs Utilizadas

| API | URL Base | Limite Gratuito | Documentação |
|---|---|---|---|
| BrasilAPI | `https://brasilapi.com.br/api` | Sem limite | brasilapi.com.br/docs |
| AwesomeAPI | `https://economia.awesomeapi.com.br` | Sem limite | docs.awesomeapi.com.br |
| ReceitaWS | `https://www.receitaws.com.br/v1` | 3 req/min grátis | receitaws.com.br |

**Prioridade:** usar BrasilAPI sempre que possível — é open source brasileira,
sem limite, e agrega CEP, CNPJ, bancos, feriados e DDD em uma API só.

---

## Padrão de Resposta das Ferramentas

Todas as ferramentas retornam `str`. O formato segue este padrão:

**Sucesso:**
```
✅ CNPJ 12.345.678/0001-99 encontrado:
Razão Social: ACME COMÉRCIO LTDA
Nome Fantasia: ACME
Situação: ATIVA
CNAE: 4712-1/00 — Comércio varejista de mercadorias em geral
Abertura: 15/03/2010
Endereço: Rua das Flores, 123 — Centro — São Paulo/SP — 01310-100
```

**Erro:**
```
❌ CNPJ inválido: o número informado não passa na validação matemática.
Dica: verifique se digitou todos os 14 dígitos corretamente.
```

---

## Contato e Links

- **GitHub:** https://github.com/impulsoxai/brazil-mcp-server
- **Site:** https://impulsoxai.com.br
- **MCP Server:** https://mcp.impulsoxai.com.br
- **Email:** contato@impulsoxai.com.br

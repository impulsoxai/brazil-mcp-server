# PRD — Brazil MCP Server
## ImpulsoX AI — Infraestrutura de Ferramentas para Agentes

**Versão:** 2.1 — Stack Real + PostgreSQL Migration Completa  
**Data:** Maio 2026  
**Endpoint atual:** mcp.impulsoxai.com.br (Railway + Cloudflare)  
**Migração planejada:** VPS próprio via Tailscale (nas próximas semanas)  
**Testes atuais:** 117/122 unitários + 13/13 TestPilot em produção  
**Ferramentas atuais:** 22 ferramentas free + 3 premium  
**Meta v2.0:** 39 ferramentas (ver seção 2)

**Stack real (confirmada pelo Claude Code):**
- Linguagem: **Python** (não Node.js)
- Framework MCP: **FastMCP**
- Banco de dados: **PostgreSQL** (migrado de JSON+memória em 08/05/2026)
- ORM: **SQLAlchemy async** + **asyncpg**
- Migrations: **Alembic**
- Deploy: **Railway** (auto-deploy via push para main)
- Auth: middleware próprio com `secrets.compare_digest`
- Rate limit por minuto: in-memory (tolerante a restart — janela 60s)
- Rate limit mensal: PostgreSQL (persistente)

**Changelog v2.0:** Expansão para 39 ferramentas + Agente Cripto + modelo freemium + acesso dual público/privado.

**Changelog v2.1:**
- ✅ Migração JSON → PostgreSQL completa (08/05/2026)
- ✅ TestPilot 13/13 em produção (mcp.impulsoxai.com.br)
- ✅ SQLAlchemy async + asyncpg + Alembic configurados
- ✅ Security review: X-Forwarded-For fixado, input truncation, sem stack traces
- ✅ 3 keys existentes migradas do JSON para PostgreSQL
- ✅ usage.py e JSON files removidos (legacy eliminado)
- ✅ Cache funcional: 1309ms → 731ms (cache hit confirmado em produção)
- Pendente: scope filtering (ferramentas premium visíveis para todos — lessons.md:41)
- Pendente: Stripe + fluxo de upgrade para planos pagos
- Pendente: última página do site (resultado após GERAR API KEY)

---

## 1. Visão Geral

O Brazil MCP Server é a infraestrutura central de ferramentas da ImpulsoX AI. Serve como backend de capacidades para todos os agentes da plataforma — agente de atendimento PME, agente agrícola, agente de cripto, e qualquer agente futuro.

**Modelo de acesso:**
- **Free (sem chave especial):** 22 ferramentas existentes + 10 novas = 32 ferramentas totais. Qualquer agente conectado ao MCP acessa automaticamente.
- **Premium Tier 1 (chave de cliente):** Google Calendar + ferramentas de comunicação ativa. Setup por cliente, valor agregado ao pacote.
- **Premium Tier 2 (chave especializada):** Agente Cripto (BTC/ETH/XRP alerts + whale tracking), commodities agrícolas, clima avançado. Cobrança separada por agente especializado.

**Arquitetura de acesso:**
```
Agente (Claude API)
      │
      │ mcp_servers: [{ url: "https://mcp.impulsoxai.com.br/sse" }]
      ↓
Brazil MCP Server
      │
      ├── Free: qualquer agente acessa (sem authorization_token)
      ├── Premium T1: authorization_token do cliente (Google Calendar etc)
      └── Premium T2: authorization_token especializado (Cripto, Agro)
```

---

## 2. Inventário Completo de Ferramentas

### CATEGORIA: IDENTIDADE (5 ferramentas — FREE existentes)

| Ferramenta | Descrição | API externa |
|---|---|---|
| `consultar_cnpj` | Dados cadastrais completos na Receita Federal | ReceitaWS (free) |
| `validar_cnpj_tool` | Valida formato e dígitos verificadores | Nenhuma |
| `validar_cpf_tool` | Valida formato e dígitos verificadores | Nenhuma |
| `formatar_cpf_tool` | Formata CPF com pontos e traço | Nenhuma |
| `formatar_cnpj_tool` | Formata CNPJ com pontos, barra e traço | Nenhuma |

---

### CATEGORIA: ENDEREÇO (3 ferramentas — FREE existentes)

| Ferramenta | Descrição | API externa |
|---|---|---|
| `buscar_endereco_por_cep` | Endereço completo por CEP | ViaCEP (free) |
| `buscar_ceps_por_logradouro` | Lista de CEPs por rua e cidade | ViaCEP (free) |
| `formatar_endereco_completo` | Formata endereço em linha única padronizada | Nenhuma |

---

### CATEGORIA: PAGAMENTOS (5 ferramentas — FREE existentes)

| Ferramenta | Descrição | API externa |
|---|---|---|
| `gerar_pix_copia_cola` | Gera código Pix copia-e-cola válido | Nenhuma (spec oficial) |
| `validar_chave_pix` | Valida formato de chave Pix (CPF/CNPJ/email/tel/aleatória) | Nenhuma |
| `calcular_juros_simples` | Juros simples sobre valor e período | Nenhuma |
| `calcular_juros_compostos` | Juros compostos com taxa e período | Nenhuma |
| `calcular_multa_atraso` | Multa percentual + juros sobre valor em atraso | Nenhuma |

---

### CATEGORIA: CALENDÁRIO (4 ferramentas — FREE existentes)

| Ferramenta | Descrição | API externa |
|---|---|---|
| `listar_feriados_nacionais` | Feriados nacionais por ano | Nenhuma (hardcoded + lógica) |
| `verificar_dia_util` | Verifica se data é dia útil no Brasil | Nenhuma |
| `calcular_prazo_util` | Adiciona N dias úteis a uma data | Nenhuma |
| `proximo_dia_util` | Retorna próximo dia útil após uma data | Nenhuma |

---

### CATEGORIA: UTILIDADES (5 ferramentas — FREE existentes)

| Ferramenta | Descrição | API externa |
|---|---|---|
| `converter_moeda` | Converte entre moedas com taxa do dia | AwesomeAPI (free) |
| `validar_telefone_br` | Valida formato de telefone brasileiro | Nenhuma |
| `formatar_telefone_br_tool` | Formata telefone com DDD e separadores | Nenhuma |
| `buscar_banco_por_codigo` | Retorna nome do banco pelo código BACEN | Nenhuma (lista hardcoded) |
| `listar_ddd_estados` | Retorna estado/região por DDD | Nenhuma (hardcoded) |

---

### CATEGORIA: PREMIUM EXISTENTE (3 ferramentas — PREMIUM T2)

| Ferramenta | Descrição | API externa | Status |
|---|---|---|---|
| `get_commodity_price` | Preço de commodities agrícolas (soja, milho, boi gordo, café) | API externa paga | ✅ Produção |
| `get_weather_forecast` | Previsão meteorológica agrícola avançada por coordenadas | API externa paga | ✅ Produção |
| `get_weather_alert` | Alertas de clima severo para região agrícola | API externa paga | ✅ Produção |

---

### ONDA 1 — NOVAS FREE: Lógica Pura (8 ferramentas — sem API externa)

**Implementar esta semana. Zero dependência externa, zero custo, zero risco.**

#### `formatar_mensagem_whatsapp`
Formata texto para WhatsApp com markdown correto.
- Input: `{ text: string, bold?: boolean, italic?: boolean, list_items?: string[] }`
- Output: texto formatado com `*bold*`, `_italic_`, `- item`
- Uso: agente formata respostas automaticamente antes de enviar

#### `gerar_link_whatsapp`
Gera link de WhatsApp com mensagem pré-preenchida.
- Input: `{ phone: string, message?: string }`
- Output: `https://wa.me/5548999...?text=Ol%C3%A1`
- Uso: agente gera links de contato quando precisa indicar outro número

#### `calcular_desconto`
Calcula valor final após desconto.
- Input: `{ valor: number, desconto_percentual: number }`
- Output: `{ valor_original, desconto_valor, valor_final, economia }`
- Uso: "10% de desconto em R$350" → agente calcula corretamente

#### `calcular_comissao`
Calcula comissão percentual sobre valor.
- Input: `{ valor: number, percentual: number }`
- Output: `{ valor_base, comissao, total }`
- Uso: representantes comerciais, prestadores com taxa de comissão

#### `calcular_idade`
Calcula idade exata a partir de data de nascimento.
- Input: `{ data_nascimento: string }` (dd/mm/aaaa ou ISO)
- Output: `{ anos, meses, dias, data_aniversario_proximo }`
- Uso: clínicas, academias, qualquer atendimento que exija faixa etária

#### `formatar_data_br`
Converte qualquer formato de data para dd/mm/aaaa.
- Input: `{ data: string }` (aceita ISO, americano, texto)
- Output: `{ data_formatada, dia_semana, extenso }`
- Uso: garante que o agente nunca manda data em formato americano

#### `calcular_diferenca_datas`
Calcula diferença entre duas datas.
- Input: `{ data_inicio: string, data_fim: string }`
- Output: `{ dias, semanas, meses, anos, dias_uteis }`
- Uso: prazo de garantia, tempo desde último atendimento, vencimento

#### `validar_email_br`
Valida formato de email e domínios comuns brasileiros.
- Input: `{ email: string }`
- Output: `{ valido: boolean, dominio, sugestao? }`
- Sugestão: se `gmai.com` → sugere `gmail.com`
- Uso: validação antes de salvar contato do cliente

---

### ONDA 2 — NOVAS FREE: Clima via Open-Meteo (2 ferramentas)

**Open-Meteo: open-source, sem API key, sem limite para uso comercial.**

#### `previsao_tempo_por_cep`
Previsão dos próximos 7 dias por CEP.
- Input: `{ cep: string, dias?: number }` (padrão 3 dias)
- Fluxo: CEP → `buscar_endereco_por_cep` → coordenadas → Open-Meteo
- Output: `{ cidade, previsao: [{ data, temp_min, temp_max, chuva_mm, descricao }] }`
- Uso: eletricistas, jardineiros, prestadores de serviço externo

#### `condicao_tempo_atual`
Condição climática atual por CEP ou município.
- Input: `{ cep?: string, cidade?: string, estado?: string }`
- Output: `{ temperatura, sensacao_termica, umidade, vento_kmh, chuva, descricao }`
- Uso: agente agrícola, logística, qualquer serviço ao ar livre

---

### ONDA 3 — NOVAS FREE: Financeiro via brapi.dev + CoinGecko (3 ferramentas)

**brapi.dev: tier gratuito para ações B3. CoinGecko Demo: 30 calls/min, 10k/mês grátis.**

#### `cotacao_acao_b3`
Cotação em tempo real de ação da B3.
- Input: `{ ticker: string }` (ex: "PETR4", "VALE3", "ITUB4")
- API: brapi.dev (free tier, sem limite documentado para tickers populares)
- Output: `{ ticker, nome, preco, variacao_pct, variacao_valor, volume, abertura, minima, maxima, atualizacao }`
- Uso: dashboards de investimento, agente financeiro, consultas pontuais

#### `cotacao_indices_br`
Cotação de índices e câmbio brasileiros.
- Input: `{ indices: string[] }` (ex: ["IBOVESPA", "USDBRL", "SELIC", "CDI"])
- API: brapi.dev + HG Brasil (ambos free)
- Output: `{ [indice]: { valor, variacao_pct, atualizacao } }`
- Uso: contexto econômico para qualquer agente financeiro ou de negócios

#### `cotacao_cripto_simples`
Cotação de cripto em BRL (consulta pontual, não monitoramento).
- Input: `{ moedas: string[] }` (ex: ["bitcoin", "ethereum", "ripple"])
- API: CoinGecko Demo (30 calls/min, 10k/mês — suficiente para consultas)
- Output: `{ [moeda]: { preco_brl, variacao_24h_pct, market_cap, volume_24h } }`
- Uso: consultas rápidas — o monitoramento contínuo vai no Agente Cripto (T2)

---

### ONDA 4 — PREMIUM TIER 1: Google Calendar (3 ferramentas — OAuth por cliente)

**Gratuito pela API do Google. Setup exige OAuth 2.0 por cliente — justifica cobrança de configuração.**

#### `google_calendar_listar_horarios_livres`
Lista horários disponíveis na agenda do cliente.
- Input: `{ calendar_id: string, data_inicio: string, data_fim: string, duracao_minutos: number }`
- Auth: OAuth token do cliente (armazenado no banco, refresh automático)
- Output: `{ horarios_livres: [{ inicio, fim, duracao }] }`
- Uso: agente de agendamento — "quais horários você tem disponível sexta?"

#### `google_calendar_criar_evento`
Cria evento na agenda com notificação ao convidado.
- Input: `{ titulo, inicio, fim, descricao?, email_convidado?, lembrete_minutos? }`
- Auth: OAuth token do cliente
- Output: `{ evento_id, link, confirmado: boolean }`
- Uso: agente confirma agendamento diretamente na agenda real do negócio

#### `google_calendar_cancelar_evento`
Cancela evento e notifica convidado.
- Input: `{ evento_id: string, motivo?: string }`
- Auth: OAuth token do cliente
- Output: `{ cancelado: boolean, notificado: boolean }`
- Uso: cliente cancela via WhatsApp → agente cancela direto no Calendar

---

### AGENTE CRIPTO — PREMIUM TIER 2: Monitoramento + Whale Tracking (4 ferramentas)

**Este é o diferencial da ImpulsoX no segmento cripto. Produto separado com precificação própria.**

#### `monitorar_preco_cripto`
Monitora BTC, ETH e XRP e dispara alerta quando variação ≥ 3%.
- Input: `{ moedas: ["bitcoin", "ethereum", "ripple"], threshold_pct: 3.0, intervalo_segundos: 300 }`
- Lógica:
  1. Busca preço atual via CoinGecko
  2. Compara com preço de referência salvo no banco
  3. Se variação ≥ threshold: dispara alerta via WhatsApp ou Telegram
  4. Atualiza preço de referência após alerta
- Output: `{ moeda, preco_atual, preco_referencia, variacao_pct, alerta_disparado, direcao: "alta"|"queda" }`
- Diferenciais:
  - Alerta bilíngue PT-BR formatado para WhatsApp
  - Inclui contexto: "BTC subiu 3,2% nas últimas 4h — agora em R$ 487.320"
  - Histórico de alertas por usuário no banco

#### `rastrear_carteira_whale`
Monitora endereços de whales conhecidos em BTC, ETH e XRP.
- Input: `{ enderecos: string[], blockchain: "bitcoin"|"ethereum"|"xrp", min_valor_usd: number }`
- APIs:
  - Bitcoin: Blockchain.info API (free, sem limite documentado)
  - Ethereum: Etherscan API (free tier: 5 calls/seg, 100k/dia)
  - XRP: XRPL WebSocket (gratuito, oficial da Ripple)
- Output: `{ endereco, ultima_transacao: { hash, valor_usd, valor_btc, tipo: "entrada"|"saida", timestamp }, saldo_atual }`
- Uso: "A whale 0x1234... movimentou $2,3M em ETH há 15 minutos"

#### `listar_whales_conhecidas`
Retorna lista curada de endereços de whales conhecidos públicos.
- Input: `{ blockchain: "bitcoin"|"ethereum"|"xrp", categoria?: "exchange"|"fundo"|"minerador"|"desconhecido" }`
- Fonte: lista hardcoded + atualizada manualmente com endereços públicos conhecidos
  - MicroStrategy, Grayscale, Binance cold wallet, Coinbase reserve, etc.
- Output: `{ whales: [{ endereco, nome, categoria, blockchain, saldo_estimado_usd }] }`
- Curadoria: ImpulsoX mantém e atualiza a lista — isso é o diferencial de produto

#### `historico_movimentacao_cripto`
Histórico de transações de um endereço nos últimos N dias.
- Input: `{ endereco: string, blockchain: string, dias: number }`
- APIs: Blockchain.info / Etherscan / XRPL (todos com free tier suficiente)
- Output: `{ transacoes: [{ data, valor_usd, tipo, hash, confirmacoes }], volume_total_usd, maior_transacao }`
- Uso: análise de comportamento de whale antes de recomendar posição

---

## 3. Arquitetura do Agente Cripto

O Agente Cripto é um produto separado da ImpulsoX — não é o agente de atendimento PME. É um agente autônomo que roda em background, monitora preços e carteiras, e dispara alertas proativos.

```
[Cron Job — a cada 5 minutos]
          │
          ↓
[Agente Cripto — Claude Haiku]
          │
          ├── monitorar_preco_cripto (BTC, ETH, XRP)
          ├── rastrear_carteira_whale (endereços monitorados)
          │
          ├── Variação ≥ 3%? → Dispara alerta WhatsApp/Telegram
          ├── Whale movimentou > $1M? → Dispara alerta com análise
          │
          └── Salva histórico no banco PostgreSQL
```

**Por que Claude Haiku para o Agente Cripto:**
O monitoramento é uma tarefa de classificação e formatação — não precisa de Sonnet. Haiku roda a cada 5 minutos por usuário com custo mínimo (~US$0,001 por ciclo). Para 100 usuários monitorando, o custo mensal é ~US$8,64 — margem absurda.

**SOUL.md do Agente Cripto:**
```markdown
# Identidade
Você é CryptoWatch, agente de monitoramento cripto da ImpulsoX AI.

# Missão
Monitorar preços de BTC, ETH e XRP e movimentações de whales conhecidas.
Alertar o usuário quando algo relevante acontecer — sem spam, sem ruído.

# Regras de alerta
- Só alerta variação ≥ 3% (configurável por usuário)
- Máximo 1 alerta por moeda por hora (evita spam)
- Whale: só alerta movimentações > $500k USD
- Tom: direto, com números, sem euforia ou medo

# Formato de alerta WhatsApp
🔴 *QUEDA — Bitcoin* (-3,4%)
💰 Preço atual: R$ 487.320
📉 Referência: R$ 504.580
⏰ 14h23 — 08/05/2026

Whale alert: Binance cold wallet movimentou 2.847 BTC ($1,38B) — saída

# O que NÃO fazer
- Não dar recomendação de compra ou venda
- Não prever preços
- Não comentar sobre projetos específicos além dos monitorados
```

---

## 4. Schema do Banco — PostgreSQL + SQLAlchemy (v2.1)

**Database:** `impulsox_mcp` (separado do `impulsox_agents` do agente WhatsApp)

```python
# src/models/api_key.py — SQLAlchemy ORM real
class ApiKey(Base):
    __tablename__ = "api_keys"

    id                     = Column(Integer, primary_key=True, autoincrement=True)
    api_key                = Column(Text, unique=True, nullable=False)
    plan                   = Column(Text, nullable=False, default="free")
    monthly_usage          = Column(Integer, nullable=False, default=0)
    reset_date             = Column(Text, nullable=False)
    status                 = Column(Text, nullable=False, default="active")
    email                  = Column(Text)
    stripe_customer_id     = Column(Text)        # pronto para Stripe
    stripe_subscription_id = Column(Text)        # pronto para Stripe
    ip_created             = Column(Text)
    created_at             = Column(Text, nullable=False)
    updated_at             = Column(Text, nullable=False)

    Index("ix_api_keys_api_key", "api_key")
    Index("ix_api_keys_email", "email")
    Index("ix_api_keys_stripe_customer_id", "stripe_customer_id")

# src/models/ip_fingerprint.py
class IpFingerprint(Base):
    __tablename__ = "ip_fingerprints"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(Text, nullable=False)
    api_key    = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)

    Index("ix_ip_fingerprints_ip_address", "ip_address")
    Index("ix_ip_fingerprints_ip_created", "ip_address", "created_at")

# src/models/usage_log.py
class UsageLog(Base):
    __tablename__ = "usage_logs"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    api_key         = Column(Text, nullable=False)
    tool_name       = Column(Text)
    ip_address      = Column(Text)
    response_status = Column(Integer)
    duration_ms     = Column(Float)
    created_at      = Column(Text, nullable=False)

    Index("ix_usage_logs_api_key", "api_key")
    Index("ix_usage_logs_created_at", "created_at")
```

**Planos definidos em `plans.py`:**

| Plano | req/mês | req/min | Stripe | Status |
|---|---|---|---|---|
| Free | 1.000 | 20 | Não | ✅ Ativo |
| Starter | 10.000 | 60 | Sim | ⏳ Sem fluxo de compra |
| Pro | 50.000 | 120 | Sim | ⏳ Sem fluxo de compra |

**Rate limit por minuto:** in-memory com `deque` por key (tolerante a restart — janela 60s se reconstrói naturalmente).

---

## 5. Variáveis de Ambiente — MCP Server v2.1 (Real)

```env
# PostgreSQL (migrado de JSON em 08/05/2026)
DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/impulsox_mcp"

# Auth
IMPULSOX_MASTER_KEY="..."    # master key — acesso total (timing-safe compare)

# Geração de API keys free
# Formato: free-{secrets.token_hex(16)}
# Limite: 3 keys por IP por dia (janela início do dia UTC)
# Plano free: 1.000 req/mês, 20 req/min

# APIs Premium existentes (T2)
COMMODITY_API_KEY="..."      # get_commodity_price
WEATHER_API_KEY="..."        # get_weather_forecast / get_weather_alert

# APIs novas — Ondas 2 e 3 (pendente implementação)
# Open-Meteo: sem API key necessária
BRAPI_TOKEN="..."            # brapi.dev — cotação B3
COINGECKO_API_KEY="..."      # CoinGecko Demo — cotação cripto

# Google Calendar OAuth (Onda 4 — pendente)
GOOGLE_CLIENT_ID="..."
GOOGLE_CLIENT_SECRET="..."
GOOGLE_REDIRECT_URI="https://mcp.impulsoxai.com.br/auth/google/callback"

# Stripe (pendente — campos prontos no banco)
STRIPE_SECRET_KEY="sk_live_..."
STRIPE_WEBHOOK_SECRET="whsec_..."

# Servidor
PORT=8000                    # FastMCP padrão
NODE_ENV=production          # Railway define automaticamente

# Telegram Monitor
TELEGRAM_BOT_TOKEN="..."
TELEGRAM_CHAT_ID="750386388"
```

---

## 6. Estrutura de Pastas — MCP Server v2.1 (Stack Real)

```
brazil-mcp-server/
├── src/
│   ├── main.py                    # FastMCP server + endpoints /keys/create, /usage
│   ├── config.py                  # DATABASE_URL, IMPULSOX_MASTER_KEY, planos
│   ├── models/                    # ← NOVO v2.1 — SQLAlchemy ORM
│   │   ├── api_key.py             # ApiKey model
│   │   ├── ip_fingerprint.py      # IpFingerprint model
│   │   └── usage_log.py           # UsageLog model
│   ├── middleware/
│   │   ├── auth.py                # validate_key() — master ou public scope
│   │   └── rate_limit.py          # check_rate_limit(), check_monthly_limit()
│   ├── services/
│   │   ├── database.py            # ← MIGRADO v2.1 — SQLAlchemy async (era JSON)
│   │   │                          # 11 funções públicas: init, create_key, validate_key,
│   │   │                          # get_usage, increment_usage, check_rate_limit,
│   │   │                          # check_monthly_limit, check_ip_limit,
│   │   │                          # record_key_creation, list_keys, flush
│   │   └── plans.py               # Free, Starter, Pro — limites e rate limits
│   ├── tools/
│   │   ├── identidade/            # 5 ferramentas (existentes)
│   │   ├── endereco/              # 3 ferramentas (existentes)
│   │   ├── pagamentos/            # 5 ferramentas (existentes)
│   │   ├── calendario/            # 4 ferramentas (existentes)
│   │   ├── utilidades/            # 5 ferramentas (existentes)
│   │   ├── premium/
│   │   │   ├── commodities.py     # get_commodity_price (T2)
│   │   │   ├── weather.py         # get_weather_forecast/alert (T2)
│   │   │   └── google_calendar.py # 3 ferramentas (Onda 4 — pendente)
│   │   ├── onda1/                 # pendente — 8 ferramentas lógica pura
│   │   ├── onda2/                 # pendente — 2 ferramentas clima Open-Meteo
│   │   ├── onda3/                 # pendente — 3 ferramentas financeiro
│   │   └── cripto/                # pendente — 4 ferramentas Premium T2
│   └── landing/
│       └── index.html             # site mcp.impulsoxai.com.br
├── scripts/
│   └── migrate_json_to_pg.py      # ← NOVO v2.1 — migração one-shot (já executado)
├── alembic/                       # ← NOVO v2.1 — migrations futuras
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
├── tests/
│   ├── test_auth.py
│   ├── test_usage_scope.py        # atualizado v2.1 — mocks em vez de live DB
│   └── test_final.py
├── data/                          # ← REMOVIDO v2.1 (era api_keys.json, ip_keys.json)
├── pyproject.toml                 # sqlalchemy[asyncio], asyncpg, alembic adicionados
├── .env                           # DATABASE_URL, IMPULSOX_MASTER_KEY
├── .env.example
├── CLAUDE.md
├── lessons.md
├── Backlog.md
└── alembic.ini
```

---

## 7. Matriz de Ferramentas por Agente

Qual agente usa quais ferramentas do MCP:

| Ferramenta | Agente PME | Agente Agrícola | Agente Cripto |
|---|:---:|:---:|:---:|
| Identidade (5) | ✓ | ✓ | — |
| Endereço (3) | ✓ | ✓ | — |
| Pagamentos (5) | ✓ | ✓ | — |
| Calendário BR (4) | ✓ | ✓ | — |
| Utilidades (5) | ✓ | ✓ | ✓ |
| WhatsApp format (2) | ✓ | ✓ | ✓ |
| Financeiro puro (3) | ✓ | ✓ | — |
| Datas (3) | ✓ | ✓ | ✓ |
| Clima Open-Meteo (2) | — | ✓ | — |
| Cotação B3/índices (2) | — | — | ✓ |
| Cotação cripto simples (1) | — | — | ✓ |
| Commodities (1) | — | ✓ | — |
| Clima avançado (2) | — | ✓ | — |
| Google Calendar (3) | ✓ Premium | — | — |
| Monitor cripto (4) | — | — | ✓ Premium |

---

## 8. Precificação por Tier de Ferramenta

| Tier | Ferramentas | Acesso | Cobrança |
|---|---|---|---|
| Free | 32 ferramentas (22 existentes + 10 novas) | Qualquer agente ImpulsoX | Incluso no pacote do agente |
| Premium T1 | Google Calendar (3) | Chave por cliente | +R$200/mês no pacote ou setup R$500 |
| Premium T2 Agro | Commodities + Clima avançado (3) | Chave especializada | Incluído no Agente Agrícola |
| Premium T2 Cripto | Monitor BTC/ETH/XRP + Whale (4) | Chave especializada | R$97–297/mês (Agente Cripto standalone) |

**Precificação do Agente Cripto standalone:**
- Essencial: R$97/mês — alertas BTC/ETH/XRP + threshold configurável
- Pro: R$197/mês — essencial + whale tracking top 20 endereços
- Institucional: R$297/mês — pro + carteiras personalizadas ilimitadas + relatório diário

---

## 9. Ordem de Implementação — Próximas Sessões

**✅ CONCLUÍDO — Migração PostgreSQL (08/05/2026)**
- JSON → PostgreSQL com SQLAlchemy async
- Alembic configurado para migrations futuras
- TestPilot 13/13 em produção
- 3 keys migradas, usage.py removido

**PENDENTE 1 — Scope Filtering (lessons.md:41)**
Ferramentas premium atualmente visíveis para todos no registry do FastMCP.
Precisar conectar o scope do auth middleware ao FastMCP tool discovery.
Bloqueia: ferramentas T2 acessíveis com key free — risco de uso não autorizado.
Prioridade: ALTA — resolver antes de adicionar mais ferramentas premium.

**PENDENTE 2 — Onda 1: 8 ferramentas de lógica pura**
Sem API externa. Implementar em Python puro:
`formatar_mensagem_whatsapp`, `gerar_link_whatsapp`, `calcular_desconto`,
`calcular_comissao`, `calcular_idade`, `formatar_data_br`,
`calcular_diferenca_datas`, `validar_email_br`

**PENDENTE 3 — Onda 2 + 3: 5 ferramentas com APIs free**
Open-Meteo (clima), brapi.dev (B3), CoinGecko (cripto simples)

**PENDENTE 4 — Última página do site**
Tela após "GERAR API KEY": chave gerada + snippet de conexão
para Claude Code, OpenClaw e API REST direta.

**PENDENTE 5 — Stripe + planos pagos**
Campos prontos no banco (stripe_customer_id, stripe_subscription_id).
Falta: conta Stripe, webhook, payment links, criação de key paga.

**PENDENTE 6 — Google Calendar (Onda 4 — Premium T1)**
OAuth 2.0 por cliente: listar horários, criar e cancelar eventos.

**PENDENTE 7 — Agente Cripto (Premium T2)**
Monitor BTC/ETH/XRP + whale tracking.
Ver seção de Agente Cripto para detalhes completos.

---

## 10. TestPilot — Casos Críticos por Onda

**Onda 1:**
- `formatar_mensagem_whatsapp`: texto com caracteres especiais, emojis, listas vazias
- `calcular_desconto`: desconto 0%, 100%, valores negativos
- `calcular_idade`: aniversário hoje, datas futuras (erro esperado), bissexto
- `validar_email_br`: typo em domínio famoso → sugestão correta

**Onda 2 (clima):**
- CEP inválido → erro amigável (não crasha)
- Open-Meteo fora do ar → fallback com mensagem de indisponibilidade
- CEP sem coordenadas → erro informativo

**Onda 3 (financeiro):**
- Ticker inexistente na B3 → erro claro ("XPTO4 não encontrado na B3")
- CoinGecko rate limit atingido → cache do último valor + aviso
- brapi.dev offline → fallback gracioso

**Agente Cripto:**
- Variação exatamente em 3,0% → alerta disparado (edge case)
- Variação de 2,99% → sem alerta
- Alerta dentro de 1h após outro alerta da mesma moeda → dedup, não envia
- Whale com transação abaixo do `min_whale_usd` → sem alerta
- Etherscan rate limit → retry com backoff exponencial
- XRPL WebSocket desconectado → reconecta automaticamente

---

## 11. Migração Railway → VPS (Tailscale)

**Stack no VPS:** Python + FastMCP + PostgreSQL + SQLAlchemy + Alembic + PM2 (ou systemd)

**O que muda e o que NÃO muda:**

O endpoint público `https://mcp.impulsoxai.com.br` continua funcionando via Cloudflare Tunnel — nenhum dev externo percebe a migração.

Os agentes ImpulsoX passam a usar IP Tailscale internamente — latência menor, zero custo de requisição externa.

**Checklist de migração:**
1. Provisionar PostgreSQL no VPS — criar database `impulsox_mcp`
2. Rodar `alembic upgrade head` no VPS — cria schema
3. Exportar dados do Railway PostgreSQL → importar no VPS
4. Subir FastMCP server no VPS com PM2 ou systemd
5. Configurar Cloudflare Tunnel: `mcp.impulsoxai.com.br` → porta 8000 VPS
6. Testar acesso público: 25 ferramentas respondendo + auth funcionando
7. Atualizar `MCP_SERVER_URL` no `.env` do agente WhatsApp para IP Tailscale
8. Testar acesso interno via Tailscale
9. Desativar Railway após 7 dias de estabilidade
10. DNS permanece no Cloudflare — sem mudança visível externamente

**Variável no agente WhatsApp:**
```env
# Antes (Railway)
MCP_SERVER_URL="https://mcp.impulsoxai.com.br/sse"

# Depois (VPS via Tailscale — mais rápido e seguro)
MCP_SERVER_URL="http://100.x.x.x:8000/sse"
```

---

## 12. Fluxo de Desenvolvimento — ImpulsoX v2

Este projeto segue o **Fluxo ImpulsoX v2** obrigatoriamente:

```
Sessão → Idear (PRD já feito) → Planejar → Isolar (worktree por onda)
→ Executar (TDD) → Revisar → Finalizar → Simplify → Security
→ TestPilot (13 fases gate obrigatório) → lessons.md → Deploy
```

**Regras críticas para este projeto:**
- Cada onda é uma branch separada via git worktree
- Testes de integração com APIs externas usam mocks — não consomem quota real
- Toda falha de API externa vira graceful error, nunca crash
- Toda nova ferramenta: mínimo 5 casos de teste antes de PR
- Security review obrigatório antes de expor qualquer ferramenta Premium

---

*Documento gerado pela ImpulsoX AI para uso exclusivo no Claude Code.*  
*Versão 2.0 — 39 ferramentas + Agente Cripto*  
*Fluxo: ImpulsoX v2 — Sessão → Idear → Planejar → Isolar → Executar → Revisar → Finalizar → Simplify → Security → TestPilot → Aprender → Deploy*

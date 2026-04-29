# Roadmap — Brazil MCP Server

## Status Atual

| Sprint | Status | Ferramentas |
|---|---|---|
| Sprint 1 — Identidade + Endereço | ✅ Completo | consultar_cnpj, validar_cpf, buscar_cep |
| Sprint 2 — Pagamentos + Calendário | ⬜ Planejado | PIX, feriados, dias úteis |
| Sprint 3 — Utilidades + Monetização | ⬜ Planejado | Moeda, telefone, API keys |

---

## Sprint 1 — MVP (Identidade + Endereço)
**Objetivo:** ter as ferramentas mais usadas por agentes de atendimento funcionando.

- [x] Estrutura do projeto
- [x] CLAUDE.md com instruções para o agente construtor
- [x] `src/utils/validators.py` — validação matemática CPF/CNPJ
- [x] `src/utils/formatters.py` — formatação de dados brasileiros
- [x] `src/utils/http_client.py` — cliente HTTP compartilhado
- [x] `src/tools/identidade.py` — 5 ferramentas
- [x] `src/tools/endereco.py` — 3 ferramentas
- [x] `src/main.py` — entry point
- [x] `tests/tools/test_identidade.py`
- [x] `tests/tools/test_endereco.py`
- [x] `railway.json` configurado e testado
- [x] `tests/integration/test_server.py`
- [x] `docs/integration-guide.md`
- [x] `LICENSE` (MIT)
- [x] `.env.example` + `.gitignore`
- [ ] Deploy no Railway funcionando
- [ ] Domínio `mcp.impulsoxai.com.br` apontando

---

## Sprint 2 — Pagamentos + Calendário
**Objetivo:** ferramentas financeiras e de datas para agentes de vendas e cobrança.

### `src/tools/pagamentos.py` (placeholder criado)
- [ ] `gerar_pix_copia_cola(chave, valor, nome, cidade)` — payload PIX estático
- [ ] `validar_chave_pix(chave)` — valida tipo e formato da chave
- [ ] `calcular_juros_simples(principal, taxa, dias)` — juros simples
- [ ] `calcular_juros_compostos(principal, taxa, periodos)` — juros compostos
- [ ] `calcular_multa_atraso(valor, dias_atraso)` — multa 2% + juros 1%/mês padrão BR

### `src/tools/calendario.py` (placeholder criado)
- [ ] `listar_feriados_nacionais(ano)` — feriados nacionais via BrasilAPI
- [ ] `verificar_dia_util(data)` — verifica se é dia útil
- [ ] `calcular_prazo_util(data_inicio, dias_uteis)` — soma dias úteis
- [ ] `proximo_dia_util(data)` — próximo dia útil

---

## Sprint 3 — Utilidades + Monetização
**Objetivo:** ferramentas complementares e sistema de API keys para monetizar.

### `src/tools/utilidades.py` (placeholder criado)
- [ ] `converter_moeda(valor, de, para)` — cotação via AwesomeAPI
- [ ] `validar_telefone_br(telefone)` — valida número brasileiro
- [ ] `formatar_telefone_br(telefone)` — formata com DDD
- [ ] `buscar_banco_por_codigo(codigo)` — nome do banco via BrasilAPI
- [ ] `listar_ddd_estados()` — mapa DDD → estado

### Monetização
- [x] `src/middleware/auth.py` — placeholder (sempre retorna True)
- [x] `src/middleware/rate_limit.py` — placeholder (sempre retorna True)
- [ ] Implementar autenticação real por API key
- [ ] Implementar rate limiting real por tier
- [ ] Página de cadastro para API key paga
- [ ] Documentação de preços e tiers

---

## Backlog Futuro (v2.0)

- [ ] Consulta de processos no TJSP/TJRJ por CPF/CNPJ
- [ ] Verificação de inadimplência (SPC/Serasa API)
- [ ] Geração de boleto bancário
- [ ] Consulta de veículos por placa (DETRAN)
- [ ] Nota fiscal eletrônica (NF-e) básica
- [ ] SDK Python para facilitar integração
- [ ] SDK TypeScript para devs Node.js

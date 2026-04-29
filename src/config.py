"""Configurações globais do Brazil MCP Server."""

import os
from dotenv import load_dotenv

load_dotenv()

# Ambiente
MCP_ENV = os.getenv("MCP_ENV", "development")
MCP_PORT = int(os.getenv("MCP_PORT", "8000"))

# Rate limiting
FREE_TIER_DAILY_LIMIT = int(os.getenv("FREE_TIER_DAILY_LIMIT", "100"))
PAID_TIER_DAILY_LIMIT = int(os.getenv("PAID_TIER_DAILY_LIMIT", "10000"))

# APIs externas
BRASIL_API_BASE = os.getenv("BRASIL_API_BASE", "https://brasilapi.com.br/api")
AWESOME_API_BASE = os.getenv("AWESOME_API_BASE", "https://economia.awesomeapi.com.br")

# Timeout padrão para chamadas HTTP (segundos)
HTTP_TIMEOUT = 10.0

# Monitoramento
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

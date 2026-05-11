"""Scope management — ContextVar + tool scope registry.

Tiers hierarchy (higher inherits lower):
  public → premium_t1 → premium_t2 → master

Access rules:
  public:       any key
  premium_t1:   key with tier >= premium_t1, or master
  premium_t2:   key with tier >= premium_t2, or master
  master:       master key only
"""

from contextvars import ContextVar
from typing import Literal

# Request-scoped: set by middleware, read by FastMCP
request_scope: ContextVar[str] = ContextVar("request_scope", default="public")

# Tier hierarchy — higher number = more access
TIER_ORDER: dict[str, int] = {
    "public": 0,
    "premium_t1": 1,
    "premium_t2": 2,
    "master": 3,
}

ToolScope = Literal["public", "premium_t1", "premium_t2", "master"]

# Tool → scope mapping
_TOOL_SCOPES: dict[str, str] = {}


def register_tool_scope(name: str, scope: ToolScope) -> None:
    """Register a tool's required scope tier."""
    _TOOL_SCOPES[name] = scope


def get_tool_scope(name: str) -> str:
    """Get the required scope for a tool. Defaults to public."""
    return _TOOL_SCOPES.get(name, "public")


def is_tool_allowed(tool_name: str, current_scope: str) -> bool:
    """Check if current scope can access the tool.

    Args:
        tool_name: name of the tool to check
        current_scope: scope from the current request (public, premium_t1, premium_t2, master)

    Returns:
        True if access allowed, False otherwise
    """
    tool_scope = get_tool_scope(tool_name)
    current_level = TIER_ORDER.get(current_scope, 0)
    required_level = TIER_ORDER.get(tool_scope, 0)
    return current_level >= required_level


def get_all_scopes() -> dict[str, str]:
    """Return all registered tool scopes (for testing)."""
    return dict(_TOOL_SCOPES)


def clear_scopes() -> None:
    """Clear all registered scopes. For testing only."""
    _TOOL_SCOPES.clear()


# Onda 1 — Lógica Pura (12 ferramentas, scope public)
register_tool_scope("formatar_mensagem_whatsapp", "public")
register_tool_scope("gerar_link_whatsapp", "public")
register_tool_scope("calcular_desconto", "public")
register_tool_scope("calcular_comissao", "public")
register_tool_scope("calcular_idade", "public")
register_tool_scope("formatar_data_br", "public")
register_tool_scope("calcular_diferenca_datas", "public")
register_tool_scope("validar_email_br", "public")
register_tool_scope("calcular_imc", "public")
register_tool_scope("calcular_reajuste_inflacao", "public")
register_tool_scope("gerar_senha_segura", "public")
register_tool_scope("converter_numero_extenso", "public")

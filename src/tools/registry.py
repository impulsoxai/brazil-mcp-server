"""Tool registry with scope metadata for access control."""

from dataclasses import dataclass
from typing import Callable


@dataclass
class ToolEntry:
    name: str
    handler: Callable
    scope: str = "public"  # "public" | "private"


_REGISTRY: dict[str, ToolEntry] = {}


def register(name: str, handler: Callable, scope: str = "public") -> None:
    """Register a tool with scope metadata."""
    _REGISTRY[name] = ToolEntry(name=name, handler=handler, scope=scope)


def list_tools(scope: str = "public") -> list[ToolEntry]:
    """Return tools visible for the given scope."""
    if scope == "master":
        return list(_REGISTRY.values())
    return [t for t in _REGISTRY.values() if t.scope == "public"]


def get_all_tools() -> dict[str, ToolEntry]:
    """Return all registered tools (for testing)."""
    return dict(_REGISTRY)


def clear_registry() -> None:
    """Clear all registered tools. For testing only."""
    _REGISTRY.clear()

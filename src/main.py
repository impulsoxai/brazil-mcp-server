"""Entry point do Brazil MCP Server."""

import sys
import asyncio
from starlette.requests import Request
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

from src.config import MCP_PORT, MCP_ENV
from src.tools import identidade, endereco, pagamentos, calendario, utilidades
from src.monitoring.alertas import enviar_alerta

mcp = FastMCP(
    "Brazil MCP Server",
    host="0.0.0.0",
    port=MCP_PORT,
)

# Registrar módulos de ferramentas
identidade.register_tools(mcp)
endereco.register_tools(mcp)
pagamentos.register_tools(mcp)
calendario.register_tools(mcp)
utilidades.register_tools(mcp)


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    """Health check endpoint para o Railway."""
    return JSONResponse({"status": "ok", "version": "0.1.0"})


if __name__ == "__main__":
    print(f"Iniciando Brazil MCP Server (env={MCP_ENV}, port={MCP_PORT})", file=sys.stderr)
    try:
        asyncio.get_event_loop().run_until_complete(
            enviar_alerta(f"Servidor iniciado — env={MCP_ENV}, port={MCP_PORT}", "info")
        )
    except Exception:
        pass
    mcp.run(transport="streamable-http")

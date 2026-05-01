"""Entry point do Brazil MCP Server."""

import sys
import asyncio
from pathlib import Path
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from mcp.server.fastmcp import FastMCP

from src.config import MCP_PORT, MCP_ENV
from src.tools import identidade, endereco, pagamentos, calendario, utilidades
from src.monitoring.alertas import enviar_alerta

mcp = FastMCP(
    "Brazil MCP Server",
    host="0.0.0.0",
    port=MCP_PORT,
    stateless_http=True,
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


_LANDING_HTML = (Path(__file__).parent / "landing" / "index.html").read_text(encoding="utf-8")


@mcp.custom_route("/", methods=["GET"])
async def landing(request: Request) -> HTMLResponse:
    """Serve a landing page do Brazil MCP Playground."""
    return HTMLResponse(_LANDING_HTML)


if __name__ == "__main__":
    print(f"Iniciando Brazil MCP Server (env={MCP_ENV}, port={MCP_PORT})", file=sys.stderr)

    # Alerta de startup via Telegram (não bloqueia se falhar)
    async def _startup_alert():
        """Envia alerta de startup via Telegram quando o servidor MCP inicializa."""
        try:
            await enviar_alerta(f"Servidor iniciado — env={MCP_ENV}, port={MCP_PORT}", "info")
        except Exception as e:
            print(f"[STARTUP] Falha ao enviar alerta Telegram: {e}", file=sys.stderr)

    try:
        asyncio.run(_startup_alert())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_startup_alert())
        loop.close()

    mcp.run(transport="streamable-http")

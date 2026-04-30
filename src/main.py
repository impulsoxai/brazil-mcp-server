"""Entry point do Brazil MCP Server."""

import os
import sys
import asyncio
import httpx
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


@mcp.custom_route("/debug/telegram", methods=["GET"])
async def debug_telegram(request: Request) -> JSONResponse:
    """Endpoint de debug para testar Telegram em produção."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    resultado = {
        "token_configurado": bool(token),
        "token_length": len(token),
        "chat_id_configurado": bool(chat_id),
        "chat_id": chat_id,
    }

    if not token or not chat_id:
        resultado["erro"] = "Variáveis não configuradas"
        return JSONResponse(resultado)

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": "🧪 Teste de debug — endpoint /debug/telegram",
            "parse_mode": "HTML",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            resultado["telegram_status"] = resp.status_code
            resultado["telegram_response"] = resp.text[:300]
    except Exception as e:
        resultado["erro"] = f"{type(e).__name__}: {e}"

    return JSONResponse(resultado)


if __name__ == "__main__":
    print(f"Iniciando Brazil MCP Server (env={MCP_ENV}, port={MCP_PORT})", file=sys.stderr)

    # Alerta de startup via Telegram (não bloqueia se falhar)
    async def _startup_alert():
        try:
            await enviar_alerta(f"Servidor iniciado — env={MCP_ENV}, port={MCP_PORT}", "info")
        except Exception as e:
            print(f"[STARTUP] Falha ao enviar alerta Telegram: {e}", file=sys.stderr)

    try:
        asyncio.run(_startup_alert())
    except RuntimeError:
        # Event loop já existe — usar create_task
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_startup_alert())
        loop.close()

    mcp.run(transport="streamable-http")

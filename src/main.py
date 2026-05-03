"""Entry point do Brazil MCP Server."""

import sys
import asyncio
import uvicorn
from pathlib import Path
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from mcp.server.fastmcp import FastMCP

from src.config import MCP_PORT, MCP_ENV
from src.tools import identidade, endereco, pagamentos, calendario, utilidades
from src.monitoring.alertas import enviar_alerta
from src.middleware.auth import verificar_autenticacao
from src.middleware.rate_limit import verificar_rate_limit, verificar_limite_mensal
from src.services import usage

mcp = FastMCP(
    "Brazil MCP Server",
    host="0.0.0.0",
    port=MCP_PORT,
    stateless_http=True,
)

# Registrar modulos de ferramentas
identidade.register_tools(mcp)
endereco.register_tools(mcp)
pagamentos.register_tools(mcp)
calendario.register_tools(mcp)
utilidades.register_tools(mcp)


# ── Auth + Rate Limit Middleware ──────────────────────────

async def _reject(scope, receive, send, msg: str, status: int):
    """Send JSON error response and return."""
    response = JSONResponse({"error": msg}, status_code=status)
    await response(scope, receive, send)


class AuthRateLimitMiddleware:
    """Enforce API key auth, rate limiting, and monthly usage on /mcp."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] == "/mcp" and scope["method"] == "POST":
            headers = dict(scope.get("headers", []))
            x_api_key = headers.get(b"x-api-key", b"").decode()

            # 1. Auth
            auth = verificar_autenticacao({"x-api-key": x_api_key})
            if not auth["valid"]:
                await _reject(scope, receive, send, "Invalid or missing API key", 401)
                return

            api_key = auth["api_key"]

            # 2. Monthly limit
            monthly = verificar_limite_mensal(api_key)
            if not monthly["allowed"]:
                await _reject(scope, receive, send, "Monthly limit exceeded", 429)
                return

            # 3. Per-minute rate limit
            rate = verificar_rate_limit(api_key)
            if not rate["allowed"]:
                await _reject(scope, receive, send, "Rate limit exceeded", 429)
                return

            # 4. Increment usage
            usage.increment_usage(api_key)

        await self.app(scope, receive, send)


# ── Custom Routes ─────────────────────────────────────────

@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "version": "0.2.0"})


@mcp.custom_route("/usage", methods=["GET"])
async def usage_endpoint(request: Request) -> JSONResponse:
    """Returns current usage for the API key."""
    x_api_key = request.headers.get("x-api-key", "").strip()

    auth = verificar_autenticacao({"x-api-key": x_api_key})
    if not auth["valid"]:
        return JSONResponse(
            {"error": "Invalid or missing API key"},
            status_code=401,
        )

    usage_data = usage.get_usage(auth["api_key"])
    return JSONResponse({
        "plan": usage_data["plan"],
        "usage": usage_data["usage"],
        "limit": usage_data["limit"],
        "remaining": usage_data["remaining"],
        "reset_date": usage_data["reset_date"],
    })


_LANDING_HTML = (Path(__file__).parent / "landing" / "index.html").read_text(encoding="utf-8")


@mcp.custom_route("/", methods=["GET"])
async def landing(request: Request) -> HTMLResponse:
    """Serve landing page."""
    return HTMLResponse(_LANDING_HTML)


# ── Build app with middleware ─────────────────────────────

def create_app():
    """Create Starlette app with auth/rate-limit middleware."""
    app = mcp.streamable_http_app()
    app.add_middleware(AuthRateLimitMiddleware)
    return app


# ── Startup ───────────────────────────────────────────────

if __name__ == "__main__":
    usage.init()
    keys = usage.list_keys()
    print(f"[STARTUP] API keys loaded: {len(keys)}", file=sys.stderr)

    print(f"Iniciando Brazil MCP Server (env={MCP_ENV}, port={MCP_PORT})", file=sys.stderr)

    async def _startup_alert():
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

    app = create_app()
    try:
        uvicorn.run(app, host="0.0.0.0", port=MCP_PORT)
    finally:
        usage.flush()

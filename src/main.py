"""Entry point do Brazil MCP Server."""

import sys
import asyncio
import ipaddress
import secrets
import uvicorn
from pathlib import Path
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from mcp.server.fastmcp import FastMCP

from src.config import MCP_PORT, MCP_ENV, IMPULSOX_MASTER_KEY
from src.tools import identidade, endereco, pagamentos, calendario, utilidades, agrinho
from src.monitoring.alertas import enviar_alerta
from src.middleware.auth import verificar_autenticacao
from src.middleware.rate_limit import verificar_rate_limit, verificar_limite_mensal
from src.services import database as usage

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
agrinho.register_tools(mcp)


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

            # 1. Auth (now returns scope)
            auth = await verificar_autenticacao({"x-api-key": x_api_key})
            if not auth["valid"]:
                await _reject(scope, receive, send, "Invalid or missing API key", 401)
                return

            api_key = auth["api_key"]
            is_master = auth.get("scope") == "master"

            # 2. Skip rate/usage for master key
            if not is_master:
                # Monthly limit
                monthly = await verificar_limite_mensal(api_key)
                if not monthly["allowed"]:
                    await _reject(scope, receive, send, "Monthly limit exceeded", 429)
                    return

                # Per-minute rate limit
                rate = verificar_rate_limit(api_key)
                if not rate["allowed"]:
                    await _reject(scope, receive, send, "Rate limit exceeded", 429)
                    return

                # Increment usage
                await usage.increment_usage(api_key)

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

    auth = await verificar_autenticacao({"x-api-key": x_api_key})
    if not auth["valid"]:
        return JSONResponse(
            {"error": "Invalid or missing API key"},
            status_code=401,
        )

    usage_data = await usage.get_usage(auth["api_key"])
    return JSONResponse({
        "plan": usage_data["plan"],
        "usage": usage_data["usage"],
        "limit": usage_data["limit"],
        "remaining": usage_data["remaining"],
        "reset_date": usage_data["reset_date"],
    })


@mcp.custom_route("/keys/create", methods=["POST"])
async def create_key_endpoint(request: Request) -> JSONResponse:
    """Create a free API key. Public endpoint — no auth required."""
    # Get client IP (Railway/proxy sets X-Forwarded-For)
    raw_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if raw_ip:
        try:
            client_ip = str(ipaddress.ip_address(raw_ip))
        except ValueError:
            client_ip = request.client.host if request.client else "unknown"
    else:
        client_ip = request.client.host if request.client else "unknown"

    # Check IP limit (3 keys per 24h)
    ip_check = await usage.check_ip_limit(client_ip)
    if not ip_check["allowed"]:
        return JSONResponse(
            {"error": f"Limite de {ip_check['limit']} keys por IP por dia atingido. Tente novamente amanhã."},
            status_code=429,
        )

    api_key = f"free-{secrets.token_hex(16)}"
    key_data = await usage.create_key(api_key, "free")
    await usage.record_key_creation(client_ip, api_key)

    from src.services.plans import get_plan
    free_plan = get_plan("free")
    return JSONResponse({
        "api_key": api_key,
        "plan": key_data["plan"],
        "limit": free_plan.monthly_limit,
        "message": f"Use this key in the x-api-key header. Free plan: {free_plan.monthly_limit} requests/month, {free_plan.rate_limit_per_minute}/min.",
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
    async def _main():
        await usage.init_db()
        keys = await usage.list_keys()
        print(f"[STARTUP] API keys loaded: {len(keys)}", file=sys.stderr)

        print(f"Iniciando Brazil MCP Server (env={MCP_ENV}, port={MCP_PORT})", file=sys.stderr)

        try:
            await enviar_alerta(f"Servidor iniciado — env={MCP_ENV}, port={MCP_PORT}", "info")
        except Exception as e:
            print(f"[STARTUP] Falha ao enviar alerta Telegram: {e}", file=sys.stderr)

        app = create_app()
        config = uvicorn.Config(app, host="0.0.0.0", port=MCP_PORT)
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(_main())

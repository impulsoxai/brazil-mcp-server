"""Entry point do Brazil MCP Server."""

import sys
import json
import uvicorn
from starlette.requests import Request
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

from src.config import MCP_PORT, MCP_ENV
from src.tools import identidade, endereco

# Placeholder imports para Sprints futuros
# from src.tools import pagamentos, calendario, utilidades

mcp = FastMCP("Brazil MCP Server")

# Registrar módulos de ferramentas
identidade.register_tools(mcp)
endereco.register_tools(mcp)

# Placeholder: registrar módulos futuros
# pagamentos.register_tools(mcp)
# calendario.register_tools(mcp)
# utilidades.register_tools(mcp)


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    """Health check endpoint para o Railway."""
    return JSONResponse({"status": "ok", "version": "0.1.0"})


if __name__ == "__main__":
    print(f"Iniciando Brazil MCP Server (env={MCP_ENV}, port={MCP_PORT})", file=sys.stderr)
    uvicorn.run(
        "src.main:mcp",
        host="0.0.0.0",
        port=MCP_PORT,
        reload=MCP_ENV == "development",
    )

"""Entry point do Brazil MCP Server."""

import sys
import uvicorn
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


if __name__ == "__main__":
    print(f"Iniciando Brazil MCP Server (env={MCP_ENV}, port={MCP_PORT})", file=sys.stderr)
    uvicorn.run(
        "src.main:mcp",
        host="0.0.0.0",
        port=MCP_PORT,
        reload=MCP_ENV == "development",
    )

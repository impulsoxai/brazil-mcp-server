"""Alertas via Telegram para monitoramento do Brazil MCP Server."""

import sys
import os
from datetime import datetime, timezone

# Contadores de falhas por ferramenta (resetam a cada chamada bem-sucedida)
_falhas_consecutivas: dict[str, int] = {}
_LIMITE_FALHAS = 3


async def enviar_alerta(mensagem: str, nivel: str = "info") -> None:
    """
    Envia alerta via Telegram. Se TELEGRAM_BOT_TOKEN não estiver
    configurado, apenas loga no stderr. NUNCA quebra o servidor.

    Níveis: info, warning, error
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    icones = {"info": "ℹ️", "warning": "⚠️", "error": "🔴"}
    icone = icones.get(nivel, "📋")
    texto_formatado = f"{icone} [{nivel.upper()}] {timestamp}\n{mensagem}"

    # Sempre loga no stderr
    print(f"[ALERTA:{nivel}] {mensagem}", file=sys.stderr)

    if not token or not chat_id:
        return

    try:
        import httpx
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": texto_formatado, "parse_mode": "HTML"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                print(f"[ALERTA] Falha ao enviar Telegram: {resp.status_code}", file=sys.stderr)
    except Exception as e:
        print(f"[ALERTA] Erro ao enviar Telegram: {e}", file=sys.stderr)


def registrar_falha(ferramenta: str) -> int:
    """Registra falha consecutiva de uma ferramenta. Retorna total de falhas."""
    _falhas_consecutivas[ferramenta] = _falhas_consecutivas.get(ferramenta, 0) + 1
    return _falhas_consecutivas[ferramenta]


def registrar_sucesso(ferramenta: str) -> None:
    """Reseta contador de falhas de uma ferramenta."""
    _falhas_consecutivas.pop(ferramenta, None)


def obter_falhas(ferramenta: str) -> int:
    """Retorna número de falhas consecutivas de uma ferramenta."""
    return _falhas_consecutivas.get(ferramenta, 0)

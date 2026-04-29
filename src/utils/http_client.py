"""Cliente HTTP compartilhado com retry e timeout."""

import httpx
from src.config import HTTP_TIMEOUT


async def get(url: str, **kwargs) -> httpx.Response:
    """
    Faz GET com timeout configurado.

    Levanta httpx.TimeoutException se exceder o limite.
    """
    kwargs.setdefault("timeout", HTTP_TIMEOUT)
    async with httpx.AsyncClient() as client:
        return await client.get(url, **kwargs)

"""Cliente HTTP compartilhado com retry, backoff exponencial e timeout."""

import asyncio
import sys
import httpx

from src.config import HTTP_TIMEOUT

# Status codes que merecem retry (erros de rede/servidor)
_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0  # segundos: 1s, 2s, 4s


async def get(url: str, **kwargs) -> httpx.Response:
    """
    Faz GET com retry automático e backoff exponencial.

    - 3 tentativas com backoff: 1s, 2s, 4s
    - Retry em erros de rede e status 429, 500, 502, 503, 504
    - NÃO faz retry em 400, 404 (erro do cliente)
    - Timeout de 10s por tentativa
    - Loga cada tentativa no stderr
    """
    kwargs.setdefault("timeout", HTTP_TIMEOUT)
    last_exception = None

    for tentativa in range(_MAX_RETRIES):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, **kwargs)

                # Status que merecem retry
                if response.status_code in _RETRY_STATUS_CODES:
                    if tentativa < _MAX_RETRIES - 1:
                        wait = _BACKOFF_BASE * (2 ** tentativa)
                        print(
                            f"[HTTP] Retry {tentativa + 1}/{_MAX_RETRIES} — "
                            f"status {response.status_code} em {url} — "
                            f"aguardando {wait:.0f}s",
                            file=sys.stderr,
                        )
                        await asyncio.sleep(wait)
                        continue

                return response

        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout,
                httpx.ConnectTimeout, httpx.PoolTimeout) as e:
            last_exception = e
            if tentativa < _MAX_RETRIES - 1:
                wait = _BACKOFF_BASE * (2 ** tentativa)
                print(
                    f"[HTTP] Retry {tentativa + 1}/{_MAX_RETRIES} — "
                    f"{type(e).__name__} em {url} — "
                    f"aguardando {wait:.0f}s",
                    file=sys.stderr,
                )
                await asyncio.sleep(wait)
            else:
                print(
                    f"[HTTP] Falhou após {_MAX_RETRIES} tentativas: {url} — {e}",
                    file=sys.stderr,
                )
                raise

    # Se chegou aqui, todas as tentativas retornaram status de retry
    return response

"""Middleware de rate limiting — controle de requisições por API key.

Sprint 3 — Será implementado:
- Contagem de requisições por API key (sliding window)
- Limites distintos por tier: free (100/dia), paid (10.000/dia)
- Resposta com headers X-RateLimit-Limit, X-RateLimit-Remaining
- Armazenamento em Redis ou memória com expiração
"""


def verificar_rate_limit(api_key: str) -> bool:
    """Verifica se a requisição está dentro do rate limit.

    Por ora, sempre retorna True (sem rate limiting real).
    No Sprint 3, contará requisições por API key.
    """
    return True

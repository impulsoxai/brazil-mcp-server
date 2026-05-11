# PostgreSQL Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate Brazil MCP Server storage from JSON+memory (`usage.py`) to PostgreSQL with SQLAlchemy async, maintaining the same 11-function public interface.

**Architecture:** Replace `usage.py` (JSON files + in-memory dicts) with `database.py` (SQLAlchemy async + asyncpg). Three ORM models (`ApiKey`, `IpFingerprint`, `UsageLog`) map to PostgreSQL tables. Rate limit per-minute stays in-memory (deque). Alembic handles future schema migrations (Stripe, paid plans).

**Tech Stack:** Python 3.11+, SQLAlchemy 2.0+ (async), asyncpg, Alembic, PostgreSQL 14+

---

## Workflow Summary (ImpulsoX v2)

| Fase | Skill | Status |
|---|---|---|
| 0 — SESSÃO | `using-superpowers` | Feito |
| 1 — IDEAR | `brainstorming` | Feito (diagnóstico + aprovação) |
| 2 — PLANEJAR | `writing-plans` | **Este documento** |
| 3 — ISOLAR | `using-git-worktrees` | Pendente |
| 4 — EXECUTAR | `subagent-driven-development` | Tasks 1-9 abaixo |
| 5 — REVISAR | `requesting-code-review` | Pendente |
| 6 — FINALIZAR | `finishing-a-development-branch` | Pendente |
| 7 — LIMPAR | `simplify` | Pendente |
| 8 — SEGURANÇA | `security-review` | Pendente |
| 9 — QA COMPLETO | `testpilot` | Pendente |
| 10 — CAPTURAR | manual (lessons.md + Backlog.md) | Pendente |
| 11 — DEPLOY | manual | Pendente |

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `pyproject.toml` | Modify | Add sqlalchemy[asyncio], asyncpg, alembic |
| `src/config.py` | Modify | Add DATABASE_URL env var |
| `src/models/__init__.py` | Create | Package init |
| `src/models/base.py` | Create | SQLAlchemy async engine + session factory |
| `src/models/api_key.py` | Create | ApiKey ORM model |
| `src/models/ip_fingerprint.py` | Create | IpFingerprint ORM model |
| `src/models/usage_log.py` | Create | UsageLog ORM model |
| `src/services/database.py` | Rewrite | Async CRUD operations (same 11-function interface) |
| `src/main.py` | Modify | Switch imports from usage → database, await calls |
| `src/middleware/auth.py` | Modify | Switch import, await validate_key() |
| `src/middleware/rate_limit.py` | Modify | Switch import, await calls |
| `src/services/usage.py` | Delete | Legacy JSON module (after migration verified) |
| `scripts/migrate_json_to_pg.py` | Create | One-time data migration script |
| `alembic.ini` | Create | Alembic config |
| `alembic/env.py` | Create | Alembic environment |
| `tests/models/test_database.py` | Create | Tests for new database module |
| `.env.example` | Modify | Add DATABASE_URL |

---

### Task 1: Add dependencies and DATABASE_URL

**Files:**
- Modify: `pyproject.toml:16-23`
- Modify: `src/config.py:1-29`
- Modify: `.env.example`

- [ ] **Step 1: Update pyproject.toml dependencies**

```toml
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
    "pydantic>=2.0.0",
    "uvicorn>=0.30.0",
    "python-dotenv>=1.0.0",
    "unidecode>=1.3.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
]
```

- [ ] **Step 2: Add DATABASE_URL to config.py**

After line 28 (`IMPULSOX_MASTER_KEY`), add:

```python
# Database (PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost:5432/impulsox_mcp")
```

- [ ] **Step 3: Update .env.example**

Add:
```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/impulsox_mcp
```

- [ ] **Step 4: Install dependencies locally**

Run: `pip install "sqlalchemy[asyncio]>=2.0.0" "asyncpg>=0.30.0" "alembic>=1.14.0"`
Expected: Successfully installed

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/config.py .env.example
git commit -m "deps: add SQLAlchemy async, asyncpg, Alembic for PostgreSQL migration"
```

---

### Task 2: Create SQLAlchemy models

**Files:**
- Create: `src/models/__init__.py`
- Create: `src/models/base.py`
- Create: `src/models/api_key.py`
- Create: `src/models/ip_fingerprint.py`
- Create: `src/models/usage_log.py`

- [ ] **Step 1: Create base.py with async engine and session**

```python
"""SQLAlchemy async engine and session factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
```

- [ ] **Step 2: Create api_key.py model**

```python
"""ApiKey ORM model."""

from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String, nullable=False, default="free")
    monthly_usage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reset_date: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String, nullable=True)
    ip_created: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_api_keys_key", "api_key"),
        Index("idx_api_keys_email", "email"),
        Index("idx_api_keys_stripe", "stripe_customer_id"),
    )
```

- [ ] **Step 3: Create ip_fingerprint.py model**

```python
"""IpFingerprint ORM model."""

from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class IpFingerprint(Base):
    __tablename__ = "ip_fingerprints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip_address: Mapped[str] = mapped_column(String, nullable=False)
    api_key: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_ip_address", "ip_address"),
        Index("idx_ip_created", "ip_address", "created_at"),
    )
```

- [ ] **Step 4: Create usage_log.py model**

```python
"""UsageLog ORM model."""

from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key: Mapped[str] = mapped_column(String, nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_usage_key", "api_key"),
        Index("idx_usage_created", "created_at"),
    )
```

- [ ] **Step 5: Create __init__.py**

```python
"""SQLAlchemy models package."""

from src.models.base import Base, engine, async_session
from src.models.api_key import ApiKey
from src.models.ip_fingerprint import IpFingerprint
from src.models.usage_log import UsageLog

__all__ = ["Base", "engine", "async_session", "ApiKey", "IpFingerprint", "UsageLog"]
```

- [ ] **Step 6: Commit**

```bash
git add src/models/
git commit -m "feat: add SQLAlchemy ORM models for ApiKey, IpFingerprint, UsageLog"
```

---

### Task 3: Rewrite database.py with async interface

**Files:**
- Rewrite: `src/services/database.py`

This is the core task. The new `database.py` must expose the same 11 functions as `usage.py` but backed by PostgreSQL via SQLAlchemy async. Functions that were sync become async.

**Interface mapping (usage.py → database.py):**

| usage.py function | database.py function | Notes |
|---|---|---|
| `init()` | `init_db()` | Creates tables via `Base.metadata.create_all()` |
| `flush()` | `flush()` | No-op (async writes are immediate) |
| `create_key(api_key, plan)` | `create_key(api_key, plan, email, ...)` | INSERT via SQLAlchemy |
| `validate_key(api_key)` | `validate_key(api_key)` | SELECT WHERE api_key AND status='active' |
| `get_usage(api_key)` | `get_usage(api_key)` | SELECT + reset_if_needed |
| `check_monthly_limit(api_key)` | `check_monthly_limit(api_key)` | SELECT + plan lookup |
| `increment_usage(api_key)` | `increment_usage(api_key)` | UPDATE monthly_usage + 1 |
| `check_rate_limit(api_key)` | `check_rate_limit(api_key)` | **In-memory deque** (same as usage.py) |
| `check_ip_limit(ip)` | `check_ip_limit(ip, limit)` | SELECT COUNT from ip_fingerprints |
| `record_key_creation(ip, api_key)` | `record_key_creation(ip, api_key)` | INSERT into ip_fingerprints + UPDATE api_keys |
| `list_keys()` | `list_keys()` | SELECT all |

- [ ] **Step 1: Write the failing test for init_db()**

Create `tests/models/test_database.py`:

```python
"""Tests for PostgreSQL database module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.database import init_db, create_key, validate_key


@pytest.mark.asyncio
async def test_init_db_creates_tables():
    """init_db should call create_all on the metadata."""
    with patch("src.services.database.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)
        await init_db()
        mock_conn.run_sync.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "Brazil MCP Server" && py -3.13 -m pytest tests/models/test_database.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.services.database'` (or function doesn't exist yet)

- [ ] **Step 3: Implement database.py**

```python
"""PostgreSQL database for API key management and paid plans.

Replaces JSON-based usage.py with SQLAlchemy async + asyncpg.
Rate limit per-minute stays in-memory (deque).
"""

import time
from collections import deque
from datetime import datetime, timezone

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Base, engine, async_session, ApiKey, IpFingerprint, UsageLog
from src.services.plans import get_plan


# In-memory rate limit windows: {api_key: deque of timestamps}
_minute_windows: dict[str, deque] = {}


# ── Lifecycle ────────────────────────────────────────────────

async def init_db() -> None:
    """Create tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def flush() -> None:
    """No-op for PostgreSQL (writes are immediate)."""
    pass


# ── API Key Operations ──────────────────────────────────────

async def create_key(api_key: str, plan: str = "free", email: str = None,
                     stripe_customer_id: str = None, stripe_subscription_id: str = None,
                     ip_created: str = None) -> dict:
    """Create a new API key in the database."""
    now = datetime.now(timezone.utc)
    reset_date = _next_reset_date(now)

    async with async_session() as session:
        key = ApiKey(
            api_key=api_key,
            plan=plan,
            monthly_usage=0,
            reset_date=reset_date,
            status="active",
            email=email,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            ip_created=ip_created,
            created_at=now,
            updated_at=now,
        )
        session.add(key)
        await session.commit()

    return {
        "api_key": api_key,
        "plan": plan,
        "usage": 0,
        "reset_date": reset_date,
        "status": "active",
        "email": email,
    }


async def validate_key(api_key: str) -> dict | None:
    """Validate API key. Returns key data or None if invalid."""
    async with async_session() as session:
        result = await session.execute(
            select(ApiKey).where(ApiKey.api_key == api_key, ApiKey.status == "active")
        )
        row = result.scalar_one_or_none()
        if not row:
            return None

        await _reset_if_needed(session, row)
        await session.refresh(row)

        return {
            "api_key": row.api_key,
            "plan": row.plan,
            "scope": "public",
            "usage": row.monthly_usage,
            "reset_date": row.reset_date,
            "status": row.status,
        }


async def get_usage(api_key: str) -> dict | None:
    """Get usage info for an API key."""
    async with async_session() as session:
        result = await session.execute(
            select(ApiKey).where(ApiKey.api_key == api_key)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None

        await _reset_if_needed(session, row)
        await session.refresh(row)

        plan = get_plan(row.plan)
        return {
            "plan": row.plan,
            "usage": row.monthly_usage,
            "limit": plan.monthly_limit,
            "remaining": max(0, plan.monthly_limit - row.monthly_usage),
            "reset_date": row.reset_date,
        }


async def increment_usage(api_key: str) -> None:
    """Increment usage counter for an API key."""
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        await session.execute(
            update(ApiKey)
            .where(ApiKey.api_key == api_key)
            .values(monthly_usage=ApiKey.monthly_usage + 1, updated_at=now)
        )
        await session.commit()


async def check_monthly_limit(api_key: str) -> dict:
    """Check if API key has remaining monthly quota."""
    async with async_session() as session:
        result = await session.execute(
            select(ApiKey).where(ApiKey.api_key == api_key, ApiKey.status == "active")
        )
        row = result.scalar_one_or_none()
        if not row:
            return {"allowed": False, "usage": 0, "limit": 0, "remaining": 0}

        await _reset_if_needed(session, row)
        await session.refresh(row)

        plan = get_plan(row.plan)
        usage = row.monthly_usage
        remaining = max(0, plan.monthly_limit - usage)

        return {
            "allowed": remaining > 0,
            "usage": usage,
            "limit": plan.monthly_limit,
            "remaining": remaining,
        }


# ── Rate Limit (in-memory) ─────────────────────────────────

def check_rate_limit(api_key: str) -> dict:
    """Check per-minute rate limit using sliding window with deque.

    NOTE: This is intentionally synchronous and in-memory.
    Rate limit windows are lost on server restart — acceptable tradeoff.
    """
    # Need to look up plan from DB, but we keep plan info cached in-memory
    # For now, use a sync approach: check _minute_windows directly
    # Plan lookup happens at validate_key time; we store plan in a local cache

    # Fallback: use free plan defaults if key not in cache
    limit = 20  # default free plan

    now = time.time()
    window_start = now - 60

    if api_key not in _minute_windows:
        _minute_windows[api_key] = deque()

    timestamps = _minute_windows[api_key]

    while timestamps and timestamps[0] <= window_start:
        timestamps.popleft()

    count = len(timestamps)

    if count >= limit:
        return {"allowed": False, "count": count, "limit": limit, "remaining": 0}

    timestamps.append(now)

    return {
        "allowed": True,
        "count": count + 1,
        "limit": limit,
        "remaining": limit - count - 1,
    }


def set_rate_limit_for_key(api_key: str, limit: int) -> None:
    """Cache rate limit per-minute for a key (called after validate_key)."""
    _rate_limit_cache[api_key] = limit


# Rate limit cache: {api_key: limit_per_minute}
_rate_limit_cache: dict[str, int] = {}


# ── IP Fingerprint Operations ───────────────────────────────

async def check_ip_limit(ip: str, limit: int = 3) -> dict:
    """Check if IP has not exceeded key creation limit (per day)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    async with async_session() as session:
        result = await session.execute(
            select(func.count()).select_from(IpFingerprint).where(
                IpFingerprint.ip_address == ip,
                IpFingerprint.created_at >= f"{today}T00:00:00+00:00"
            )
        )
        keys_created = result.scalar() or 0

    return {
        "allowed": keys_created < limit,
        "keys_created": keys_created,
        "limit": limit,
        "remaining": max(0, limit - keys_created),
    }


async def record_key_creation(ip: str, api_key: str) -> None:
    """Record that this IP created this API key."""
    now = datetime.now(timezone.utc)

    async with async_session() as session:
        fingerprint = IpFingerprint(
            ip_address=ip,
            api_key=api_key,
            created_at=now,
        )
        session.add(fingerprint)

        await session.execute(
            update(ApiKey).where(ApiKey.api_key == api_key).values(ip_created=ip)
        )
        await session.commit()


# ── Usage Logging ───────────────────────────────────────────

async def log_usage(api_key: str, tool_name: str = None, ip: str = None,
                    status: int = None, duration_ms: float = None) -> None:
    """Log a tool call for analytics."""
    async with async_session() as session:
        log = UsageLog(
            api_key=api_key,
            tool_name=tool_name,
            ip_address=ip,
            response_status=status,
            duration_ms=duration_ms,
            created_at=datetime.now(timezone.utc),
        )
        session.add(log)
        await session.commit()


# ── Admin Operations ────────────────────────────────────────

async def list_keys() -> list[dict]:
    """List all API keys (admin use)."""
    async with async_session() as session:
        result = await session.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
        rows = result.scalars().all()
        return [
            {
                "api_key": r.api_key,
                "plan": r.plan,
                "usage": r.monthly_usage,
                "status": r.status,
                "email": r.email,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]


async def cancel_key(api_key: str) -> bool:
    """Cancel/deactivate an API key."""
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        result = await session.execute(
            update(ApiKey)
            .where(ApiKey.api_key == api_key)
            .values(status="cancelled", updated_at=now)
        )
        await session.commit()
        return result.rowcount > 0


# ── Helpers ─────────────────────────────────────────────────

async def _reset_if_needed(session: AsyncSession, row: ApiKey) -> None:
    """Reset monthly usage if reset_date has passed."""
    now = datetime.now(timezone.utc)
    reset_date = datetime.fromisoformat(row.reset_date)
    if now >= reset_date:
        new_reset = _next_reset_date(now)
        row.monthly_usage = 0
        row.reset_date = new_reset
        row.updated_at = now
        await session.commit()


def _next_reset_date(now: datetime) -> str:
    """Calculate next month's 1st day at 00:00 UTC."""
    if now.month == 12:
        next_reset = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        next_reset = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return next_reset.isoformat()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "Brazil MCP Server" && py -3.13 -m pytest tests/models/test_database.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/services/database.py tests/models/
git commit -m "feat: rewrite database.py with SQLAlchemy async for PostgreSQL"
```

---

### Task 4: Switch imports in main.py, auth.py, rate_limit.py

**Files:**
- Modify: `src/main.py:17,49-80,92-110,113-138,160-185`
- Modify: `src/middleware/auth.py:6,51`
- Modify: `src/middleware/rate_limit.py:3,16,29`

- [ ] **Step 1: Update main.py imports and calls**

Change line 17 from:
```python
from src.services import usage
```
to:
```python
from src.services import database as usage
```

This preserves all `usage.*` call sites with zero code changes below. The alias means `usage.init()`, `usage.create_key()`, etc. all resolve to the new database module.

Then update the startup and shutdown to be async:

Lines 160-185 — change `__main__` block:
```python
if __name__ == "__main__":
    import asyncio

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
```

Update route handlers to be async-aware:

Line 78 — `usage.increment_usage(api_key)` → `await usage.increment_usage(api_key)`

Line 103 — `usage_data = usage.get_usage(...)` → `usage_data = await usage.get_usage(...)`

Line 122 — `ip_check = usage.check_ip_limit(...)` → `ip_check = await usage.check_ip_limit(...)`

Line 130 — `key_data = usage.create_key(...)` → `key_data = await usage.create_key(...)`

Line 131 — `usage.record_key_creation(...)` → `await usage.record_key_creation(...)`

Note: `check_rate_limit` stays sync (in-memory), no await needed.

- [ ] **Step 2: Update auth.py**

Change line 6 from:
```python
from src.services import usage
```
to:
```python
from src.services import database as usage
```

Change `verificar_autenticacao` to be async:

Line 9: `def verificar_autenticacao(headers: dict) -> dict:` → `async def verificar_autenticacao(headers: dict) -> dict:`

Line 51: `key_data = usage.validate_key(api_key)` → `key_data = await usage.validate_key(api_key)`

- [ ] **Step 3: Update rate_limit.py**

Change line 3 from:
```python
from src.services import usage
```
to:
```python
from src.services import database as usage
```

Change `verificar_limite_mensal` to be async:

Line 19: `def verificar_limite_mensal(api_key: str) -> dict:` → `async def verificar_limite_mensal(api_key: str) -> dict:`

Line 29: `return usage.check_monthly_limit(api_key)` → `return await usage.check_monthly_limit(api_key)`

`verificar_rate_limit` stays sync (in-memory deque).

- [ ] **Step 4: Update main.py middleware to await async auth**

In `AuthRateLimitMiddleware.__call__` (line 55):
```python
# Before (sync):
auth = verificar_autenticacao({"x-api-key": x_api_key})

# After (async):
auth = await verificar_autenticacao({"x-api-key": x_api_key})
```

Line 66:
```python
# Before:
monthly = verificar_limite_mensal(api_key)
# After:
monthly = await verificar_limite_mensal(api_key)
```

Line 78:
```python
# Before:
usage.increment_usage(api_key)
# After:
await usage.increment_usage(api_key)
```

- [ ] **Step 5: Update usage_endpoint route to await**

Line 96-103:
```python
auth = await verificar_autenticacao({"x-api-key": x_api_key})
# ...
usage_data = await usage.get_usage(auth["api_key"])
```

- [ ] **Step 6: Update create_key_endpoint route to await**

Lines 122-131:
```python
ip_check = await usage.check_ip_limit(client_ip)
# ...
key_data = await usage.create_key(api_key, "free")
await usage.record_key_creation(client_ip, api_key)
```

- [ ] **Step 7: Run existing tests**

Run: `cd "Brazil MCP Server" && py -3.13 -m pytest tests/middleware/test_auth.py tests/test_usage_scope.py -v`
Expected: Tests may need updating for async (Task 5)

- [ ] **Step 8: Commit**

```bash
git add src/main.py src/middleware/auth.py src/middleware/rate_limit.py
git commit -m "refactor: switch imports from usage.py to database.py with async/await"
```

---

### Task 5: Update test files for async

**Files:**
- Modify: `tests/middleware/test_auth.py`
- Modify: `tests/test_usage_scope.py`
- Modify: `tests/integration/test_final.py`

- [ ] **Step 1: Update test_auth.py imports and async**

Change `from src.services import usage` to `from src.services import database as usage`.

Add `@pytest.mark.asyncio` to tests that call async functions.

Update `verificar_autenticacao` calls to `await verificar_autenticacao(...)`.

- [ ] **Step 2: Update test_usage_scope.py**

Same pattern — switch import, add async markers, await calls.

- [ ] **Step 3: Update test_final.py line 360**

Change `from src.services import usage` to `from src.services import database as usage`.

Update any direct usage.* calls to await.

- [ ] **Step 4: Run all tests**

Run: `cd "Brazil MCP Server" && py -3.13 -m pytest tests/ -v`
Expected: All tests pass (may need DATABASE_URL set for integration tests)

- [ ] **Step 5: Commit**

```bash
git add tests/
git commit -m "test: update test files for async database module"
```

---

### Task 6: Create migration script (JSON → PostgreSQL)

**Files:**
- Create: `scripts/migrate_json_to_pg.py`

- [ ] **Step 1: Write migration script**

```python
"""One-time migration: JSON files → PostgreSQL.

Reads data/api_keys.json and data/ip_keys.json, inserts into PostgreSQL.
Reports count of migrated vs original records.

Usage:
    cd "Brazil MCP Server"
    python scripts/migrate_json_to_pg.py
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import engine, async_session, Base, ApiKey, IpFingerprint
from sqlalchemy import select, func


DATA_DIR = Path(__file__).parent.parent / "data"
KEYS_FILE = DATA_DIR / "api_keys.json"
IP_KEYS_FILE = DATA_DIR / "ip_keys.json"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


async def migrate():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    keys_data = load_json(KEYS_FILE)
    ip_data = load_json(IP_KEYS_FILE)

    print(f"JSON source: {len(keys_data)} keys, {len(ip_data)} IPs")

    async with async_session() as session:
        # Migrate API keys
        migrated_keys = 0
        skipped_keys = 0
        for api_key, info in keys_data.items():
            existing = await session.execute(
                select(ApiKey).where(ApiKey.api_key == api_key)
            )
            if existing.scalar_one_or_none():
                skipped_keys += 1
                continue

            now = datetime.now(timezone.utc)
            key = ApiKey(
                api_key=api_key,
                plan=info.get("plan", "free"),
                monthly_usage=info.get("usage", 0),
                reset_date=info.get("reset_date", now.isoformat()),
                status="active",
                ip_created=None,
                created_at=datetime.fromisoformat(info["created_at"]) if "created_at" in info else now,
                updated_at=now,
            )
            session.add(key)
            migrated_keys += 1

        # Migrate IP fingerprints
        migrated_ips = 0
        for ip, entry in ip_data.items():
            for api_key, timestamp in zip(entry.get("keys", []), entry.get("timestamps", [])):
                fingerprint = IpFingerprint(
                    ip_address=ip,
                    api_key=api_key,
                    created_at=datetime.fromisoformat(timestamp),
                )
                session.add(fingerprint)
                migrated_ips += 1

        await session.commit()

    # Verify
    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(ApiKey))
        db_count = result.scalar()
        result = await session.execute(select(func.count()).select_from(IpFingerprint))
        ip_count = result.scalar()

    print(f"\n=== Migration Results ===")
    print(f"API Keys — JSON: {len(keys_data)}, Migrated: {migrated_keys}, Skipped: {skipped_keys}, DB total: {db_count}")
    print(f"IP Fingerprints — JSON entries: {sum(len(v.get('keys', [])) for v in ip_data.values())}, Migrated: {migrated_ips}, DB total: {ip_count}")

    if db_count == len(keys_data) - skipped_keys + skipped_keys:
        print("\n✅ Migration verified — counts match")
    else:
        print(f"\n⚠️  Count mismatch — investigate before proceeding")

    print(f"\nNext steps:")
    print(f"1. Verify data in PostgreSQL manually")
    print(f"2. If OK, delete usage.py and JSON files")
    print(f"3. Run testpilot")


if __name__ == "__main__":
    asyncio.run(migrate())
```

- [ ] **Step 2: Run migration (dry run on local SQLite first if no PG)**

Run: `cd "Brazil MCP Server" && py -3.13 scripts/migrate_json_to_pg.py`

- [ ] **Step 3: Verify counts match output**

Expected: `API Keys — JSON: X, Migrated: X, Skipped: 0, DB total: X`

**STOP — do not proceed until user confirms counts are correct.**

- [ ] **Step 4: Commit**

```bash
git add scripts/migrate_json_to_pg.py
git commit -m "feat: add JSON → PostgreSQL migration script with count verification"
```

---

### Task 7: Setup Alembic

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/`

- [ ] **Step 1: Init Alembic**

Run: `cd "Brazil MCP Server" && py -3.13 -m alembic init alembic`

- [ ] **Step 2: Configure alembic.ini**

Set `sqlalchemy.url` to read from env:
```ini
sqlalchemy.url = %(DATABASE_URL)s
```

- [ ] **Step 3: Configure alembic/env.py**

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from src.config import DATABASE_URL
from src.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("+asyncpg", ""))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Generate initial migration**

Run: `cd "Brazil MCP Server" && py -3.13 -m alembic revision --autogenerate -m "initial schema"`

- [ ] **Step 5: Review generated migration**

Verify it creates `api_keys`, `ip_fingerprints`, `usage_logs` tables with correct columns and indexes.

- [ ] **Step 6: Commit**

```bash
git add alembic.ini alembic/
git commit -m "chore: setup Alembic for PostgreSQL schema migrations"
```

---

### Task 8: Cleanup — remove legacy files

**Files:**
- Delete: `src/services/usage.py`
- Delete: `data/api_keys.json` (if exists)
- Delete: `data/ip_keys.json` (if exists)

**PRE-REQUISITE:** User has confirmed migration counts match (Task 6, Step 3).

- [ ] **Step 1: Delete usage.py**

```bash
rm src/services/usage.py
```

- [ ] **Step 2: Delete JSON data files (if present)**

```bash
rm -f data/api_keys.json data/ip_keys.json
```

- [ ] **Step 3: Run full test suite**

Run: `cd "Brazil MCP Server" && py -3.13 -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove legacy usage.py and JSON data files"
```

---

## Fase 4 — EXECUTAR (Tasks 1-9 acima)

As Tasks 1-9 acima são a Fase 4 do fluxo ImpulsoX v2. Usar `subagent-driven-development` ou `executing-plans`.

---

## Fase 5 — REVISAR

**Skill:** `requesting-code-review`

- [ ] Rodar code review no diff completo da branch `feature/postgresql-migration`
- [ ] Verificar: todas as 11 funções públicas mantêm mesma assinatura
- [ ] Verificar: async/await correto em todos os call sites
- [ ] Verificar: nenhum import quebrado de `usage.py` restante
- [ ] Verificar: migration script preserva dados existentes
- [ ] Corrigir findings do review

---

## Fase 6 — FINALIZAR

**Skill:** `finishing-a-development-branch`

- [ ] Verificar branch limpa (sem unstaged changes)
- [ ] Decidir: merge para main ou PR
- [ ] Se PR: `git push -u origin feature/postgresql-migration` + `gh pr create`
- [ ] Se merge: `git checkout main && git merge feature/postgresql-migration`

---

## Fase 7 — LIMPAR

**Skill:** `simplify`

- [ ] Rodar simplify nos arquivos modificados
- [ ] Verificar: não há código morto (imports unused, funções não chamadas)
- [ ] Verificar: não há abstrações desnecessárias
- [ ] Verificar: database.py não cresceu além do necessário
- [ ] Aplicar fixes se findings

---

## Fase 8 — SEGURANÇA

**Skill:** `security-review`

- [ ] Verificar: DATABASE_URL não hardcoded (só em .env)
- [ ] Verificar: SQL injection mitigado (SQLAlchemy ORM, não raw SQL)
- [ ] Verificar: timing-safe comparison para master key mantida
- [ ] Verificar: IP fingerprinting não expõe dados sensíveis
- [ ] Verificar: rate limit in-memory não vaza entre keys
- [ ] Verificar: connection pool não exaure recursos
- [ ] Corrigir findings de segurança

---

## Fase 9 — QA COMPLETO

**Skill:** `testpilot`

- [ ] Rodar `/testpilot` completo (13 fases)
- [ ] Verificar: 13/13 fases passam
- [ ] Se falhar: corrigir e rodar novamente
- [ ] **Gate:** hook pre-deploy bloqueia sem 13/13

---

## Fase 10 — CAPTURAR APRENDIZADO

- [ ] Atualizar `lessons.md` com:
  - Pitfalls de async/await na migração
  - Problemas encontrados com SQLAlchemy async
  - Qualquer erro de encoding/Unicode durante desenvolvimento
- [ ] Atualizar `Backlog.md`:
  - Marcar "PostgreSQL migration" como concluído
  - Adicionar próximos passos (Stripe webhooks, planos pagos)

---

## Fase 11 — DEPLOY

- [ ] Merge para `main` (se ainda não feito)
- [ ] Push para GitHub: `git push origin main`
- [ ] Verificar deploy automático no Railway
- [ ] Rodar migration no VPS Contabo: `py -3.13 scripts/migrate_json_to_pg.py`
- [ ] Verificar `https://mcp.impulsoxai.com.br/health` retorna OK
- [ ] Testar `POST /keys/create` em produção
- [ ] Testar `POST /mcp` com API key existente

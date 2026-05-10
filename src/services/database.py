"""PostgreSQL database for API key management and paid plans.

Replaces JSON-based usage.py with SQLAlchemy async + asyncpg.
Rate limit per-minute stays in-memory (deque).
"""

import time
from collections import deque
from datetime import date, datetime, timezone

from sqlalchemy import select, func, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Base, engine, async_session, ApiKey, IpFingerprint, UsageLog, CommodityCache
from src.services.plans import get_plan


# In-memory rate limit windows: {api_key: deque of timestamps}
_minute_windows: dict[str, deque] = {}

# Rate limit cache: {api_key: limit_per_minute} — populated by validate_key
_rate_limit_cache: dict[str, int] = {}


def cleanup_stale_windows(max_age_seconds: int = 300) -> int:
    """Remove _minute_windows entries older than max_age_seconds. Returns count removed."""
    now = time.time()
    stale_keys = [k for k, ts in _minute_windows.items() if not ts or (now - ts[-1]) > max_age_seconds]
    for k in stale_keys:
        del _minute_windows[k]
    return len(stale_keys)


# ── Lifecycle ────────────────────────────────────────────────

async def init_db() -> None:
    """Create tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


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

        reset_happened = await _reset_if_needed(session, row)
        if reset_happened:
            await session.commit()
            await session.refresh(row)

        # Cache rate limit for this key
        plan = get_plan(row.plan)
        _rate_limit_cache[api_key] = plan.rate_limit_per_minute

        return {
            "api_key": row.api_key,
            "plan": row.plan,
            "scope": row.plan if row.plan in ("premium_t1", "premium_t2", "master") else "public",
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

        reset_happened = await _reset_if_needed(session, row)
        if reset_happened:
            await session.commit()
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

        reset_happened = await _reset_if_needed(session, row)
        if reset_happened:
            await session.commit()
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

    NOTE: Intentionally synchronous and in-memory.
    Rate limit windows are lost on server restart — acceptable tradeoff.

    Depends on validate_key() being called first to populate _rate_limit_cache.
    Unknown keys are denied by default (safe-by-default).
    """
    if api_key not in _rate_limit_cache:
        return {"allowed": False, "count": 0, "limit": 0, "remaining": 0}

    cleanup_stale_windows()

    limit = _rate_limit_cache[api_key]

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


# ── IP Fingerprint Operations ───────────────────────────────

async def check_ip_limit(ip: str, limit: int = 3) -> dict:
    """Check if IP has not exceeded key creation limit (per day)."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    async with async_session() as session:
        result = await session.execute(
            select(func.count()).select_from(IpFingerprint).where(
                IpFingerprint.ip_address == ip,
                IpFingerprint.created_at >= today_start,
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
            tool_name=tool_name[:100] if tool_name else None,
            ip_address=ip[:45] if ip else None,
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

async def _reset_if_needed(session: AsyncSession, row: ApiKey) -> bool:
    """Reset monthly usage if reset_date has passed. Returns True if reset happened.

    Caller is responsible for committing the session.
    """
    now = datetime.now(timezone.utc)
    reset_date = datetime.fromisoformat(row.reset_date)
    if now >= reset_date:
        new_reset = _next_reset_date(now)
        row.monthly_usage = 0
        row.reset_date = new_reset
        row.updated_at = now
        return True
    return False


def _next_reset_date(now: datetime) -> str:
    """Calculate next month's 1st day at 00:00 UTC."""
    if now.month == 12:
        next_reset = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        next_reset = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return next_reset.isoformat()


# ── Commodity Cache (Playwright scraper) ──────────────────

async def get_commodity_cache(commodity: str) -> dict | None:
    """Get cached commodity price from PostgreSQL."""
    async with async_session() as session:
        result = await session.execute(
            select(CommodityCache).where(CommodityCache.commodity == commodity)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return {
            "commodity": row.commodity,
            "preco": float(row.preco),
            "unidade": row.unidade,
            "fonte": row.fonte,
            "data_referencia": row.data_referencia.isoformat(),
            "scraped_at": row.scraped_at.isoformat(),
        }


async def set_commodity_cache(commodity: str, preco: float, unidade: str,
                               fonte: str, data_referencia) -> None:
    """Upsert commodity price cache (atomic — no race condition)."""
    if isinstance(data_referencia, str):
        data_referencia = date.fromisoformat(data_referencia)

    now = datetime.now(timezone.utc)

    async with async_session() as session:
        stmt = pg_insert(CommodityCache).values(
            commodity=commodity,
            preco=preco,
            unidade=unidade,
            fonte=fonte,
            data_referencia=data_referencia,
            scraped_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["commodity"],
            set_={
                "preco": preco,
                "unidade": unidade,
                "fonte": fonte,
                "data_referencia": data_referencia,
                "scraped_at": now,
            },
        )
        await session.execute(stmt)
        await session.commit()

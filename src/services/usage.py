"""API key management and monthly usage tracking.

Storage: JSON file for simplicity. Easy to swap for Redis/DB later.
"""

import json
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from src.services.plans import PLANS, DEFAULT_PLAN, get_plan

# Storage path
_KEYS_FILE = Path(__file__).parent.parent.parent / "data" / "api_keys.json"

# In-memory cache (loaded from JSON)
_keys: dict[str, dict] = {}

# Per-minute rate limit window: {api_key: deque of timestamps}
_minute_windows: dict[str, deque] = {}

# Dirty flag: set True when data changes, flushed by flush()
_dirty = False


def _ensure_data_dir() -> None:
    """Create data directory if it doesn't exist."""
    _KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_keys() -> dict[str, dict]:
    """Load API keys from JSON file."""
    if not _KEYS_FILE.exists():
        return {}
    try:
        return json.loads(_KEYS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_keys() -> None:
    """Persist API keys to JSON file."""
    _ensure_data_dir()
    _KEYS_FILE.write_text(json.dumps(_keys, ensure_ascii=False), encoding="utf-8")


def flush() -> None:
    """Flush pending changes to disk if dirty. Call on shutdown."""
    global _dirty
    if _dirty:
        _save_keys()
        _dirty = False


def init() -> None:
    """Load keys into memory on startup."""
    global _keys
    _keys = _load_keys()


def create_key(api_key: str, plan: str = DEFAULT_PLAN) -> dict:
    """Create a new API key entry."""
    now = datetime.now(timezone.utc)
    _keys[api_key] = {
        "plan": plan,
        "usage": 0,
        "reset_date": _next_reset_date(now),
        "created_at": now.isoformat(),
    }
    _save_keys()
    return _keys[api_key]


def validate_key(api_key: str) -> dict | None:
    """Validate API key. Returns key data or None if invalid."""
    return _keys.get(api_key)


def get_usage(api_key: str) -> dict | None:
    """Get usage info for an API key."""
    key_data = _keys.get(api_key)
    if not key_data:
        return None

    _reset_if_needed(api_key)

    plan = get_plan(key_data["plan"])
    return {
        "plan": key_data["plan"],
        "usage": key_data["usage"],
        "limit": plan.monthly_limit,
        "remaining": max(0, plan.monthly_limit - key_data["usage"]),
        "reset_date": key_data["reset_date"],
    }


def check_monthly_limit(api_key: str) -> dict:
    """
    Check if API key has remaining monthly quota.

    Returns:
        {"allowed": bool, "usage": int, "limit": int, "remaining": int}
    """
    key_data = _keys.get(api_key)
    if not key_data:
        return {"allowed": False, "usage": 0, "limit": 0, "remaining": 0}

    _reset_if_needed(api_key)

    plan = get_plan(key_data["plan"])
    usage = key_data["usage"]
    remaining = max(0, plan.monthly_limit - usage)

    return {
        "allowed": remaining > 0,
        "usage": usage,
        "limit": plan.monthly_limit,
        "remaining": remaining,
    }


def increment_usage(api_key: str) -> None:
    """Increment usage counter for an API key."""
    global _dirty
    if api_key in _keys:
        _keys[api_key]["usage"] += 1
        _dirty = True


def check_rate_limit(api_key: str) -> dict:
    """
    Check per-minute rate limit using sliding window with deque.

    Returns:
        {"allowed": bool, "count": int, "limit": int, "remaining": int}
    """
    key_data = _keys.get(api_key)
    if not key_data:
        return {"allowed": False, "count": 0, "limit": 0, "remaining": 0}

    plan = get_plan(key_data["plan"])
    limit = plan.rate_limit_per_minute
    now = time.time()
    window_start = now - 60

    # Get or create window
    if api_key not in _minute_windows:
        _minute_windows[api_key] = deque()

    timestamps = _minute_windows[api_key]

    # Evict expired entries from front (O(1) amortized)
    while timestamps and timestamps[0] <= window_start:
        timestamps.popleft()

    count = len(timestamps)

    if count >= limit:
        return {"allowed": False, "count": count, "limit": limit, "remaining": 0}

    # Record this request
    timestamps.append(now)

    return {
        "allowed": True,
        "count": count + 1,
        "limit": limit,
        "remaining": limit - count - 1,
    }


def cleanup_stale_windows(max_age_seconds: int = 300) -> int:
    """Remove _minute_windows entries older than max_age_seconds. Returns count removed."""
    now = time.time()
    stale_keys = []
    for api_key, timestamps in _minute_windows.items():
        if not timestamps or (now - timestamps[-1]) > max_age_seconds:
            stale_keys.append(api_key)
    for k in stale_keys:
        del _minute_windows[k]
    return len(stale_keys)


def _reset_if_needed(api_key: str) -> None:
    """Reset monthly usage if reset_date has passed."""
    global _dirty
    key_data = _keys.get(api_key)
    if not key_data:
        return

    now = datetime.now(timezone.utc)
    reset_date = datetime.fromisoformat(key_data["reset_date"])

    if now >= reset_date:
        key_data["usage"] = 0
        key_data["reset_date"] = _next_reset_date(now)
        _dirty = True


def _next_reset_date(now: datetime) -> str:
    """Calculate next month's 1st day at 00:00 UTC."""
    if now.month == 12:
        next_reset = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        next_reset = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return next_reset.isoformat()


def list_keys() -> dict[str, dict]:
    """List all API keys (admin use)."""
    return dict(_keys)


def reset_windows() -> None:
    """Clear all rate limit windows. For testing only."""
    _minute_windows.clear()

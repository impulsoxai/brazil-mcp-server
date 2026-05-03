"""SQLite database for API key management and paid plans.

Replaces JSON files for production use. File-based, no external dependencies.
Database stored in data/brazil_mcp.db (gitignored).
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "brazil_mcp.db"


def _ensure_data_dir() -> None:
    """Create data directory if it doesn't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row_factory."""
    _ensure_data_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT UNIQUE NOT NULL,
                plan TEXT NOT NULL DEFAULT 'free',
                monthly_usage INTEGER NOT NULL DEFAULT 0,
                reset_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                email TEXT,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                ip_created TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(api_key);
            CREATE INDEX IF NOT EXISTS idx_api_keys_email ON api_keys(email);
            CREATE INDEX IF NOT EXISTS idx_api_keys_stripe ON api_keys(stripe_customer_id);

            CREATE TABLE IF NOT EXISTS ip_fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                api_key TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_ip_address ON ip_fingerprints(ip_address);
            CREATE INDEX IF NOT EXISTS idx_ip_created ON ip_fingerprints(ip_address, created_at);

            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL,
                tool_name TEXT,
                ip_address TEXT,
                response_status INTEGER,
                duration_ms REAL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_usage_key ON usage_logs(api_key);
            CREATE INDEX IF NOT EXISTS idx_usage_created ON usage_logs(created_at);
        """)
        conn.commit()
    finally:
        conn.close()


# ── API Key Operations ──────────────────────────────────────

def create_key(api_key: str, plan: str = "free", email: str = None,
               stripe_customer_id: str = None, stripe_subscription_id: str = None,
               ip_created: str = None) -> dict:
    """Create a new API key in the database."""
    now = datetime.now(timezone.utc)
    reset_date = _next_reset_date(now)

    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO api_keys (api_key, plan, monthly_usage, reset_date, status,
                                  email, stripe_customer_id, stripe_subscription_id,
                                  ip_created, created_at, updated_at)
            VALUES (?, ?, 0, ?, 'active', ?, ?, ?, ?, ?, ?)
        """, (api_key, plan, reset_date, email, stripe_customer_id,
              stripe_subscription_id, ip_created, now.isoformat(), now.isoformat()))
        conn.commit()
        return {
            "api_key": api_key,
            "plan": plan,
            "usage": 0,
            "reset_date": reset_date,
            "status": "active",
            "email": email,
        }
    finally:
        conn.close()


def validate_key(api_key: str) -> dict | None:
    """Validate API key. Returns key data or None if invalid."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE api_key = ? AND status = 'active'",
            (api_key,)
        ).fetchone()
        if not row:
            return None
        _reset_if_needed(conn, row)
        return dict(row)
    finally:
        conn.close()


def get_usage(api_key: str) -> dict | None:
    """Get usage info for an API key."""
    from src.services.plans import get_plan

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE api_key = ?", (api_key,)
        ).fetchone()
        if not row:
            return None

        _reset_if_needed(conn, row)
        row = conn.execute(
            "SELECT * FROM api_keys WHERE api_key = ?", (api_key,)
        ).fetchone()

        plan = get_plan(row["plan"])
        return {
            "plan": row["plan"],
            "usage": row["monthly_usage"],
            "limit": plan.monthly_limit,
            "remaining": max(0, plan.monthly_limit - row["monthly_usage"]),
            "reset_date": row["reset_date"],
        }
    finally:
        conn.close()


def increment_usage(api_key: str) -> None:
    """Increment usage counter for an API key."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE api_keys SET monthly_usage = monthly_usage + 1, updated_at = ? WHERE api_key = ?",
            (datetime.now(timezone.utc).isoformat(), api_key)
        )
        conn.commit()
    finally:
        conn.close()


def check_monthly_limit(api_key: str) -> dict:
    """Check if API key has remaining monthly quota."""
    from src.services.plans import get_plan

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE api_key = ? AND status = 'active'",
            (api_key,)
        ).fetchone()
        if not row:
            return {"allowed": False, "usage": 0, "limit": 0, "remaining": 0}

        _reset_if_needed(conn, row)
        row = conn.execute(
            "SELECT * FROM api_keys WHERE api_key = ?", (api_key,)
        ).fetchone()

        plan = get_plan(row["plan"])
        usage = row["monthly_usage"]
        remaining = max(0, plan.monthly_limit - usage)

        return {
            "allowed": remaining > 0,
            "usage": usage,
            "limit": plan.monthly_limit,
            "remaining": remaining,
        }
    finally:
        conn.close()


# ── IP Fingerprint Operations ───────────────────────────────

def check_ip_limit(ip: str, limit: int = 3) -> dict:
    """Check if IP has not exceeded key creation limit (per day)."""
    conn = get_connection()
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM ip_fingerprints WHERE ip_address = ? AND created_at >= ?",
            (ip, today + "T00:00:00")
        ).fetchone()
        keys_created = row["cnt"]
        return {
            "allowed": keys_created < limit,
            "keys_created": keys_created,
            "limit": limit,
            "remaining": max(0, limit - keys_created),
        }
    finally:
        conn.close()


def record_key_creation(ip: str, api_key: str) -> None:
    """Record that this IP created this API key."""
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO ip_fingerprints (ip_address, api_key, created_at) VALUES (?, ?, ?)",
            (ip, api_key, now)
        )
        conn.execute(
            "UPDATE api_keys SET ip_created = ? WHERE api_key = ?",
            (ip, api_key)
        )
        conn.commit()
    finally:
        conn.close()


# ── Usage Logging ───────────────────────────────────────────

def log_usage(api_key: str, tool_name: str = None, ip: str = None,
              status: int = None, duration_ms: float = None) -> None:
    """Log a tool call for analytics."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO usage_logs (api_key, tool_name, ip_address, response_status, duration_ms, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (api_key, tool_name, ip, status, duration_ms, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
    finally:
        conn.close()


def get_usage_stats(api_key: str = None, days: int = 30) -> dict:
    """Get usage statistics. If api_key provided, stats for that key only."""
    conn = get_connection()
    try:
        cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if api_key:
            row = conn.execute(
                "SELECT COUNT(*) as total, AVG(duration_ms) as avg_ms FROM usage_logs WHERE api_key = ? AND created_at >= ?",
                (api_key, cutoff)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) as total, AVG(duration_ms) as avg_ms FROM usage_logs WHERE created_at >= ?",
                (cutoff,)
            ).fetchone()
        return {"total_requests": row["total"], "avg_duration_ms": row["avg_ms"]}
    finally:
        conn.close()


# ── Admin Operations ────────────────────────────────────────

def list_keys() -> list[dict]:
    """List all API keys (admin use)."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM api_keys ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_key_plan(api_key: str, plan: str, stripe_customer_id: str = None,
                    stripe_subscription_id: str = None, email: str = None) -> bool:
    """Update a key's plan (admin or webhook use)."""
    conn = get_connection()
    try:
        updates = ["plan = ?", "updated_at = ?"]
        params = [plan, datetime.now(timezone.utc).isoformat()]
        if stripe_customer_id:
            updates.append("stripe_customer_id = ?")
            params.append(stripe_customer_id)
        if stripe_subscription_id:
            updates.append("stripe_subscription_id = ?")
            params.append(stripe_subscription_id)
        if email:
            updates.append("email = ?")
            params.append(email)
        params.append(api_key)
        conn.execute(f"UPDATE api_keys SET {', '.join(updates)} WHERE api_key = ?", params)
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def cancel_key(api_key: str) -> bool:
    """Cancel/deactivate an API key."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE api_keys SET status = 'cancelled', updated_at = ? WHERE api_key = ?",
            (datetime.now(timezone.utc).isoformat(), api_key)
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


# ── Migration from JSON ─────────────────────────────────────

def migrate_from_json() -> int:
    """Migrate existing JSON data to SQLite. Returns count of migrated keys."""
    json_path = Path(__file__).parent.parent.parent / "data" / "api_keys.json"
    if not json_path.exists():
        return 0

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0

    conn = get_connection()
    migrated = 0
    try:
        for api_key, info in data.items():
            existing = conn.execute(
                "SELECT 1 FROM api_keys WHERE api_key = ?", (api_key,)
            ).fetchone()
            if existing:
                continue
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("""
                INSERT INTO api_keys (api_key, plan, monthly_usage, reset_date, status,
                                      ip_created, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'active', ?, ?, ?)
            """, (api_key, info.get("plan", "free"), info.get("usage", 0),
                  info.get("reset_date", now), None, info.get("created_at", now), now))
            migrated += 1
        conn.commit()
    finally:
        conn.close()

    return migrated


# ── Helpers ─────────────────────────────────────────────────

def _reset_if_needed(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    """Reset monthly usage if reset_date has passed."""
    now = datetime.now(timezone.utc)
    reset_date = datetime.fromisoformat(row["reset_date"])
    if now >= reset_date:
        new_reset = _next_reset_date(now)
        conn.execute(
            "UPDATE api_keys SET monthly_usage = 0, reset_date = ?, updated_at = ? WHERE api_key = ?",
            (new_reset, now.isoformat(), row["api_key"])
        )
        conn.commit()


def _next_reset_date(now: datetime) -> str:
    """Calculate next month's 1st day at 00:00 UTC."""
    if now.month == 12:
        next_reset = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        next_reset = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return next_reset.isoformat()

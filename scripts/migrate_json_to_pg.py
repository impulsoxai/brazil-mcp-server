"""One-time migration: JSON files -> PostgreSQL.

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


def _parse_date(value: str | None, fallback: datetime) -> datetime:
    """Parse ISO date string with fallback on malformed input."""
    if not value:
        return fallback
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return fallback


async def migrate():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    keys_data = load_json(KEYS_FILE)
    ip_data = load_json(IP_KEYS_FILE)

    print(f"JSON source: {len(keys_data)} keys, {len(ip_data)} IPs")

    async with async_session() as session:
        migrated_keys = 0
        skipped_keys = 0
        now = datetime.now(timezone.utc)
        for api_key, info in keys_data.items():
            existing = await session.execute(
                select(ApiKey).where(ApiKey.api_key == api_key)
            )
            if existing.scalar_one_or_none():
                skipped_keys += 1
                continue

            key = ApiKey(
                api_key=api_key,
                plan=info.get("plan", "free"),
                monthly_usage=info.get("usage", 0),
                reset_date=info.get("reset_date", now.isoformat()),
                status="active",
                ip_created=None,
                created_at=_parse_date(info.get("created_at"), now),
                updated_at=now,
            )
            session.add(key)
            migrated_keys += 1

        migrated_ips = 0
        for ip, entry in ip_data.items():
            for api_key, timestamp in zip(entry.get("keys", []), entry.get("timestamps", [])):
                fingerprint = IpFingerprint(
                    ip_address=ip,
                    api_key=api_key,
                    created_at=_parse_date(timestamp, now),
                )
                session.add(fingerprint)
                migrated_ips += 1

        await session.commit()

    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(ApiKey))
        db_count = result.scalar()
        result = await session.execute(select(func.count()).select_from(IpFingerprint))
        ip_count = result.scalar()

    print(f"\n=== Migration Results ===")
    print(f"API Keys - JSON: {len(keys_data)}, Migrated: {migrated_keys}, Skipped: {skipped_keys}, DB total: {db_count}")
    print(f"IP Fingerprints - JSON entries: {sum(len(v.get('keys', [])) for v in ip_data.values())}, Migrated: {migrated_ips}, DB total: {ip_count}")

    if db_count == len(keys_data):
        print("\nMigration verified - counts match")
    else:
        print(f"\nCount mismatch - investigate before proceeding")

    print(f"\nNext steps:")
    print(f"1. Verify data in PostgreSQL manually")
    print(f"2. If OK, delete usage.py and JSON files")
    print(f"3. Run testpilot")


if __name__ == "__main__":
    asyncio.run(migrate())

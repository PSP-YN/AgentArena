"""Optional durable benchmark history storage.

Configure DATABASE_URL with a managed PostgreSQL database in hosted deployments.
No database is silently emulated on serverless ephemeral filesystems.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def database_url() -> str:
    return os.getenv("DATABASE_URL", "").strip()


def storage_enabled() -> bool:
    return bool(database_url())


@lru_cache(maxsize=4)
def _cached_engine(url: str) -> Engine:
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return create_engine(url, pool_pre_ping=True, pool_recycle=300, pool_size=2, max_overflow=0)


def _engine() -> Engine | None:
    url = database_url()
    return _cached_engine(url) if url else None


def _ensure_table(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS agentarena_runs (
                run_id VARCHAR(64) PRIMARY KEY,
                task_id VARCHAR(120) NOT NULL,
                run_type VARCHAR(40) NOT NULL,
                created_at VARCHAR(40) NOT NULL,
                payload TEXT NOT NULL
            )
        """))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_agentarena_runs_created_at ON agentarena_runs (created_at)"))


def save_result(result: dict[str, Any], run_type: str = "benchmark") -> bool:
    engine = _engine()
    if engine is None:
        return False
    _ensure_table(engine)
    run_id = str(result.get("run_id") or "")
    task_id = str(result.get("task_id") or "")
    if not run_id or not task_id:
        raise ValueError("Persisted benchmark results require run_id and task_id")
    created_at = datetime.now(timezone.utc).isoformat()
    with engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO agentarena_runs (run_id, task_id, run_type, created_at, payload)
            VALUES (:run_id, :task_id, :run_type, :created_at, :payload)
            ON CONFLICT (run_id) DO UPDATE SET
                task_id = excluded.task_id,
                run_type = excluded.run_type,
                created_at = excluded.created_at,
                payload = excluded.payload
        """), {
            "run_id": run_id,
            "task_id": task_id,
            "run_type": run_type,
            "created_at": created_at,
            "payload": json.dumps(result, separators=(",", ":"), ensure_ascii=False),
        })
    return True


def list_results(limit: int = 25, offset: int = 0) -> list[dict[str, Any]]:
    engine = _engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured; durable history is unavailable")
    _ensure_table(engine)
    with engine.connect() as connection:
        rows = connection.execute(text("""
            SELECT payload, run_type, created_at FROM agentarena_runs
            ORDER BY created_at DESC, run_id DESC
            LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset}).fetchall()
    records = []
    for row in rows:
        record = json.loads(row[0])
        record["run_type"] = row[1]
        record["created_at"] = row[2]
        records.append(record)
    return records


def check_storage() -> bool:
    """Verify database connectivity and ensure the history schema exists."""
    engine = _engine()
    if engine is None:
        return False
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    _ensure_table(engine)
    return True

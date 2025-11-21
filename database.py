"""
PostgreSQL database helpers using psycopg2.
- Initializes tables on startup
- Provides simple query helpers
"""
import os
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional, Tuple
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

_DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/trustguard")
# Normalize SQLAlchemy-style URL if provided
if "+psycopg2" in _DB_URL:
    _DB_URL = _DB_URL.replace("+psycopg2", "")

# Use autocommit for DDL convenience; transactions are managed per execute call
_conn = None


def _get_conn():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(_DB_URL)
        _conn.autocommit = True
    return _conn


@contextmanager
def get_cursor():
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        yield cur
    finally:
        cur.close()


def execute(query: str, params: Optional[Iterable[Any]] = None) -> int:
    with get_cursor() as cur:
        cur.execute(query, params or [])
        try:
            return cur.rowcount
        except Exception:
            return 0


def fetchone(query: str, params: Optional[Iterable[Any]] = None) -> Optional[Dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(query, params or [])
        row = cur.fetchone()
        return dict(row) if row else None


def fetchall(query: str, params: Optional[Iterable[Any]] = None) -> List[Dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(query, params or [])
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def init_db() -> None:
    # Create tables if they don't exist
    ddl = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        name VARCHAR(255),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS identity_checks (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        deepfake_score DOUBLE PRECISION DEFAULT 0,
        liveness_status VARCHAR(32) DEFAULT 'PASS',
        overall_result VARCHAR(32) DEFAULT 'VERIFIED',
        latency_ms INTEGER DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS official_apps (
        id SERIAL PRIMARY KEY,
        package_name VARCHAR(255) UNIQUE,
        sha256_hash VARCHAR(64),
        publisher VARCHAR(255),
        google_play_link TEXT,
        last_verified TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS suspicious_apps (
        id SERIAL PRIMARY KEY,
        package_name VARCHAR(255),
        publisher VARCHAR(255),
        google_play_link TEXT,
        confidence DOUBLE PRECISION DEFAULT 0.8
    );

    CREATE TABLE IF NOT EXISTS grievances (
        id SERIAL PRIMARY KEY,
        complaint_id VARCHAR(64) UNIQUE NOT NULL,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        text TEXT NOT NULL,
        category VARCHAR(64) NOT NULL DEFAULT 'other',
        urgency VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
        status VARCHAR(32) NOT NULL DEFAULT 'RECEIVED',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    with get_cursor() as cur:
        cur.execute(ddl)


# Initialize immediately on import so server comes up with schema
try:
    init_db()
except Exception:
    # defer errors to health endpoint if DB not up yet
    pass

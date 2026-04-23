"""
Verify Postgres and Redis are reachable for local (non-Docker) development.

Usage (from repo root):
    python scripts/check_local_services.py
"""
from __future__ import annotations

import os
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


def _tcp_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _pg_host_port() -> tuple[str, int]:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = int(os.environ.get("POSTGRES_PORT", "5432"))
        return host, port
    normalized = url.replace("postgresql+asyncpg", "postgresql", 1)
    parsed = urlparse(normalized)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    return host, port


def _redis_host_port(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    return host, port


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    load_dotenv(repo / ".env")

    pg_host, pg_port = _pg_host_port()
    broker = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
    r_host, r_port = _redis_host_port(broker)

    ok_pg = _tcp_open(pg_host, pg_port)
    ok_r = _tcp_open(r_host, r_port)

    if ok_pg:
        print(f"OK  PostgreSQL reachable at {pg_host}:{pg_port}")
    else:
        print(f"FAIL PostgreSQL not reachable at {pg_host}:{pg_port}", file=sys.stderr)

    if ok_r:
        print(f"OK  Redis reachable at {r_host}:{r_port}")
    else:
        print(f"FAIL Redis not reachable at {r_host}:{r_port}", file=sys.stderr)

    if not ok_pg or not ok_r:
        print(
            "\nStart Postgres and Redis locally (or point .env to a remote instance), then retry.\n"
            "Windows: install PostgreSQL from postgresql.org; use Memurai or Redis for Windows for port 6379.\n"
            "Create database matching POSTGRES_DB in .env if it does not exist yet.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

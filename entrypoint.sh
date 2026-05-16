#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import os
import socket
import time

host = os.getenv("CRM_DB_HOST", "db")
port = int(os.getenv("CRM_DB_PORT", "5432"))
timeout_seconds = int(os.getenv("DB_WAIT_TIMEOUT", "60"))
deadline = time.time() + timeout_seconds

while True:
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"PostgreSQL is available at {host}:{port}")
            break
    except OSError as exc:
        if time.time() >= deadline:
            raise SystemExit(
                f"PostgreSQL did not become available at {host}:{port} "
                f"within {timeout_seconds}s: {exc}"
            )
        print(f"Waiting for PostgreSQL at {host}:{port}...")
        time.sleep(2)
PY

python manage.py migrate --noinput

exec "$@"
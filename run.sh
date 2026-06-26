#!/usr/bin/env bash
set -e

cd /root/task

echo "[task] validating required files"
for file in docker-compose.yml Dockerfile init_database.sql requirements.txt app/main.py; do
  if [ ! -f "$file" ]; then
    echo "[task] missing required file: $file" >&2
    exit 1
  fi
done

echo "[task] starting FastAPI and PostgreSQL services"
docker compose up -d --build

echo "[task] waiting for PostgreSQL readiness"
for i in $(seq 1 60); do
  if docker compose exec -T postgres pg_isready -U taskuser -d taskdb >/dev/null 2>&1; then
    echo "[task] PostgreSQL is ready"
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "[task] PostgreSQL did not become ready" >&2
    exit 1
  fi
  sleep 1
done

echo "[task] waiting for FastAPI readiness"
for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/health/ready >/dev/null 2>&1; then
    echo "[task] FastAPI is ready"
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "[task] FastAPI did not become ready" >&2
    exit 1
  fi
  sleep 1
done

echo "[task] validating an application endpoint"
curl -fsS -H 'X-Tenant-Id: 00000000-0000-0000-0000-000000000001' -H 'X-Actor-User-Id: 00000000-0000-0000-0000-000000000101' 'http://127.0.0.1:8000/api/v1/projects/11111111-1111-1111-1111-111111111111/activity?limit=1' >/dev/null

echo "[task] environment is ready"
echo "[task] API: http://127.0.0.1:8000"
echo "[task] Health: http://127.0.0.1:8000/health/ready"

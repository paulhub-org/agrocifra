#!/bin/sh
set -e
echo "[entrypoint] Применение миграций базы данных (alembic upgrade head)…"
alembic upgrade head
if [ "${SEED_DEMO:-0}" = "1" ]; then
  echo "[entrypoint] Создание демонстрационных данных…"
  python -m app.db.seed || echo "[entrypoint] сидирование пропущено (не критично)"
fi
echo "[entrypoint] Запуск сервера: $*"
exec "$@"

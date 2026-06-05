#!/usr/bin/env bash
# Восстановление БД PostgreSQL АгроЦифра из дампа (через docker compose).
# Использование: ./scripts/restore.sh backups/agrocifra_YYYYmmdd_HHMMSS.sql.gz
set -euo pipefail
FILE="${1:?Укажите файл бэкапа, напр.: ./scripts/restore.sh backups/agrocifra_20260604_023000.sql.gz}"
DB_USER="${POSTGRES_USER:-agrocifra}"
DB_NAME="${POSTGRES_DB:-agrocifra}"
echo "[restore] Восстановление из ${FILE} в БД ${DB_NAME} (текущие данные будут перезаписаны)."
gunzip -c "$FILE" | docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME"
echo "[restore] Готово."

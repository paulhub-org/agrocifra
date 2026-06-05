#!/usr/bin/env bash
# Резервное копирование БД PostgreSQL АгроЦифра (через docker compose).
# Использование: ./scripts/backup.sh   (переменные: BACKUP_DIR, RETENTION_DAYS, POSTGRES_USER, POSTGRES_DB)
# Планирование (ежедневно в 02:30):  30 2 * * *  cd /opt/agrocifra && ./scripts/backup.sh >> backups/backup.log 2>&1
set -euo pipefail
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
DB_USER="${POSTGRES_USER:-agrocifra}"
DB_NAME="${POSTGRES_DB:-agrocifra}"
mkdir -p "$BACKUP_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/agrocifra_${TS}.sql.gz"
echo "[backup] Создание дампа → $OUT"
docker compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$OUT"
echo "[backup] Удаление архивов старше ${RETENTION_DAYS} дн."
find "$BACKUP_DIR" -name 'agrocifra_*.sql.gz' -mtime +"${RETENTION_DAYS}" -delete
echo "[backup] Готово: $(du -h "$OUT" | cut -f1)"

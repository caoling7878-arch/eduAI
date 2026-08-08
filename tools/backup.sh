#!/usr/bin/env bash
# eduAI 本地数据备份（SQLite + 静态资源）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${1:-$ROOT/backups/eduai-$STAMP}"
DB_SRC="$ROOT/apps/api/data/eduai_p0.db"
STATIC_SRC="$ROOT/apps/api/app/static"

mkdir -p "$OUT_DIR"

if [[ -f "$DB_SRC" ]]; then
  cp "$DB_SRC" "$OUT_DIR/eduai_p0.db"
  # 若系统有 sqlite3，再做一次一致性 dump
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$DB_SRC" ".backup '$OUT_DIR/eduai_p0.backup.db'"
  fi
  echo "DB -> $OUT_DIR/eduai_p0.db"
else
  echo "warn: database not found at $DB_SRC" >&2
fi

if [[ -d "$STATIC_SRC" ]]; then
  mkdir -p "$OUT_DIR/static"
  cp -R "$STATIC_SRC/." "$OUT_DIR/static/"
  echo "static -> $OUT_DIR/static"
fi

cat >"$OUT_DIR/MANIFEST.txt" <<EOF
eduAI backup
created_at=$STAMP
host=$(hostname 2>/dev/null || echo unknown)
db_src=$DB_SRC
static_src=$STATIC_SRC
EOF

echo "backup complete: $OUT_DIR"

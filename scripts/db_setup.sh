#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# db_setup.sh — Create the app DB user, database, and PostGIS ext.
# Works for both local dev and production.
#
# Usage:
#   bash scripts/db_setup.sh             # prompts interactively
#   DB_USER=gisapp DB_PASSWORD=secret DB_NAME=gisapp bash scripts/db_setup.sh
# ─────────────────────────────────────────────────────────────────
set -e

# ── Config (use env vars or fall back to prompts) ─────────────────
DB_USER="${DB_USER:-}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_NAME="${DB_NAME:-gisapp}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# Auto-detect the PostgreSQL superuser (macOS Homebrew uses the OS username, not 'postgres')
PG_SUPERUSER="${PG_SUPERUSER:-$(psql -d postgres -c "SELECT current_user" -t 2>/dev/null | tr -d ' \n')}"
if [ -z "$PG_SUPERUSER" ]; then
  echo "ERROR: Could not connect to PostgreSQL. Is it running?" >&2
  exit 1
fi
echo "Using PostgreSQL superuser: $PG_SUPERUSER"

if [ -z "$DB_USER" ]; then
  read -rp "New DB username [gisapp]: " DB_USER
  DB_USER="${DB_USER:-gisapp}"
fi

if [ -z "$DB_PASSWORD" ]; then
  read -rsp "Password for '$DB_USER': " DB_PASSWORD
  echo
  read -rsp "Confirm password: " DB_PASSWORD2
  echo
  if [ "$DB_PASSWORD" != "$DB_PASSWORD2" ]; then
    echo "ERROR: Passwords do not match." >&2
    exit 1
  fi
fi

echo ""
echo "=== DB Setup ==="
echo "  User:     $DB_USER"
echo "  Database: $DB_NAME"
echo "  Host:     $DB_HOST:$DB_PORT"
echo ""

# ── Create role ───────────────────────────────────────────────────
echo "Creating role '$DB_USER'..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$PG_SUPERUSER" -d postgres -tc \
  "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 && \
  echo "  Role already exists, skipping." || \
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$PG_SUPERUSER" -d postgres \
    -c "CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASSWORD';"

# ── Create database ───────────────────────────────────────────────
echo "Creating database '$DB_NAME'..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$PG_SUPERUSER" -d postgres -tc \
  "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 && \
  echo "  Database already exists, skipping." || \
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$PG_SUPERUSER" -d postgres \
    -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# ── Enable PostGIS ────────────────────────────────────────────────
echo "Enabling PostGIS extension..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$PG_SUPERUSER" -d "$DB_NAME" \
  -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Grant usage to app user
psql -h "$DB_HOST" -p "$DB_PORT" -U "$PG_SUPERUSER" -d "$DB_NAME" \
  -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$PG_SUPERUSER" -d "$DB_NAME" \
  -c "GRANT ALL ON SCHEMA public TO $DB_USER;"

# ── Write .env ────────────────────────────────────────────────────
ENV_FILE="$(dirname "$0")/../.env"
echo ""
echo "Updating .env..."

update_env() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    # Replace existing line (macOS-compatible sed)
    sed -i '' "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

update_env "DB_ENGINE" "django.contrib.gis.db.backends.postgis"
update_env "DB_NAME"   "$DB_NAME"
update_env "DB_USER"   "$DB_USER"
update_env "DB_PASSWORD" "$DB_PASSWORD"
update_env "DB_HOST"   "$DB_HOST"
update_env "DB_PORT"   "$DB_PORT"

echo ""
echo "=== Done! ==="
echo "  Run 'bash setup.sh' (or just 'python manage.py migrate') to continue."

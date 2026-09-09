#!/bin/bash
# ============================================================
# Runs automatically on first Postgres container startup
# (mounted into /docker-entrypoint-initdb.d/).
#
# Creates one restricted DB user per service. Passwords are read
# from environment variables (passed through from .env via
# docker-compose.yml) — never hardcoded here. Each service gets
# only the permissions it needs; see grant_permissions.sql, which
# must be run after each service's first Alembic migration.
#
# Each user also gets CREATE on schema public: every service runs
# its OWN Alembic migrations (`docker compose exec <service> alembic
# upgrade head`) using its own restricted DB user, so that user must
# be able to create its own tables. Postgres 15+ no longer grants
# CREATE on public to PUBLIC by default, so this must be explicit.
# grant_permissions.sql (run after migrations) then locks each user
# down to SELECT/INSERT/UPDATE on only the tables it owns — CREATE
# stays granted so future migrations keep working, but every other
# service's tables remain unreachable.
# ============================================================
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER auth_svc WITH PASSWORD '$AUTH_DB_PASSWORD';
    CREATE USER traffic_svc WITH PASSWORD '$TRAFFIC_DB_PASSWORD';
    CREATE USER complaint_svc WITH PASSWORD '$COMPLAINT_DB_PASSWORD';
    CREATE USER alert_svc WITH PASSWORD '$ALERT_DB_PASSWORD';

    GRANT CREATE ON SCHEMA public TO auth_svc, traffic_svc, complaint_svc, alert_svc;
EOSQL

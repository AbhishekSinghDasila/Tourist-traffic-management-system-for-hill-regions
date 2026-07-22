-- ============================================================
-- Run this ONCE after the first Alembic migration has created
-- the users table (alembic upgrade head).
--
-- Grants the auth_svc user exactly the permissions it needs —
-- nothing more. This means even if the auth-service container
-- is fully compromised, the attacker's DB user cannot touch
-- any table outside what auth-service legitimately needs.
--
-- Usage:
--   docker exec -i devbhumi-postgres psql -U devbhumi_admin -d devbhumi \
--     < database/seeds/grant_permissions.sql
-- ============================================================

GRANT CONNECT ON DATABASE devbhumi TO auth_svc;
GRANT USAGE ON SCHEMA public TO auth_svc;

GRANT SELECT, INSERT, UPDATE ON users TO auth_svc;
-- Note: no DELETE grant. Account deactivation is a soft delete
-- (is_active = false), never a hard row delete — preserves audit trail.

GRANT SELECT, USAGE ON ALL SEQUENCES IN SCHEMA public TO auth_svc;
GRANT USAGE ON SEQUENCE alembic_version_seq TO auth_svc;

-- As future services are added (traffic_svc, complaint_svc, alert_svc),
-- add their corresponding GRANT blocks here, each scoped to only the
-- tables that service owns. Never grant broad schema-level write access.

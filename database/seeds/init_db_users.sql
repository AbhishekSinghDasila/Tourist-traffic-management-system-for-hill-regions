-- ============================================================
-- Runs automatically on first Postgres container startup
-- (mounted into /docker-entrypoint-initdb.d/)
--
-- Creates a restricted DB user for the auth-service.
-- More users get added here as each service is built —
-- traffic_svc, complaint_svc, alert_svc each get their own
-- user with only the permissions they need.
-- ============================================================

-- Auth service user: owns users, roles, refresh_token tables only
CREATE USER auth_svc WITH PASSWORD 'Msdasila3030';

-- Note: GRANT statements run after Alembic creates the tables
-- (see database/seeds/grant_permissions.sql, run after first migration)

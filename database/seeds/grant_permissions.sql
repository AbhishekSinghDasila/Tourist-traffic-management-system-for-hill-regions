-- ============================================================
-- Run this after each service's first Alembic migration has
-- created its tables (docker compose exec <service> alembic upgrade head).
--
-- Grants each restricted service user exactly the permissions it
-- needs — nothing more. This means even if one service's container
-- is fully compromised, the attacker's DB user cannot touch any
-- table outside what that service legitimately owns.
--
-- Usage (safe to re-run — every grant is idempotent):
--   docker exec -i devbhumi-postgres psql -U devbhumi_admin -d devbhumi \
--     < database/seeds/grant_permissions.sql
-- ============================================================

-- ---------------- auth_svc: owns users, roles, refresh_token tables ----------------
GRANT CONNECT ON DATABASE devbhumi TO auth_svc;
GRANT USAGE ON SCHEMA public TO auth_svc;

GRANT SELECT, INSERT, UPDATE ON users TO auth_svc;
-- No DELETE grant. Account deactivation is a soft delete (is_active = false),
-- never a hard row delete — preserves audit trail.

-- ---------------- traffic_svc: owns checkpoints, vehicles, traffic_entries ----------------
GRANT CONNECT ON DATABASE devbhumi TO traffic_svc;
GRANT USAGE ON SCHEMA public TO traffic_svc;

GRANT SELECT, INSERT, UPDATE ON checkpoints TO traffic_svc;
GRANT SELECT, INSERT, UPDATE ON vehicles TO traffic_svc;
GRANT SELECT, INSERT, UPDATE ON traffic_entries TO traffic_svc;
-- No DELETE — a vehicle timing out at a checkpoint updates its exit
-- timestamp, it never deletes the entry (needed for density history).

-- ---------------- complaint_svc: owns complaints, complaint_media, police_stations, audit_logs ----------------
GRANT CONNECT ON DATABASE devbhumi TO complaint_svc;
GRANT USAGE ON SCHEMA public TO complaint_svc;

GRANT SELECT, INSERT, UPDATE ON complaints TO complaint_svc;
GRANT SELECT, INSERT, UPDATE ON complaint_media TO complaint_svc;
GRANT SELECT ON police_stations TO complaint_svc;
-- police_stations is reference data seeded via scripts/seed_police_stations.py,
-- not written by the running service.
GRANT SELECT, INSERT ON audit_logs TO complaint_svc;
-- audit_logs is append-only: no UPDATE, no DELETE, ever.

-- ---------------- alert_svc: owns emergency_alerts, alert_recipients, user_locations ----------------
GRANT CONNECT ON DATABASE devbhumi TO alert_svc;
GRANT USAGE ON SCHEMA public TO alert_svc;

GRANT SELECT, INSERT, UPDATE ON emergency_alerts TO alert_svc;
GRANT SELECT, INSERT, UPDATE ON alert_recipients TO alert_svc;
GRANT SELECT, INSERT, UPDATE, DELETE ON user_locations TO alert_svc;
-- user_locations is ephemeral live-tracking data (for geofenced alert
-- targeting) — unlike every other table here, stale rows are meant to
-- be hard-deleted/expired, not soft-deleted.

-- ---------------- sequences ----------------
-- Every service needs USAGE on its own tables' sequences to INSERT.
-- Simplest safe grant: SELECT+USAGE on all sequences to all service
-- users — sequences carry no sensitive data, only auto-increment state.
GRANT SELECT, USAGE ON ALL SEQUENCES IN SCHEMA public TO auth_svc, traffic_svc, complaint_svc, alert_svc;

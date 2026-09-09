# DevBhumi — Smart Traffic & Tourism Management System

Microservices-based platform addressing tourist density, traffic congestion,
and citizen safety in the hill regions of Uttarakhand and Himachal Pradesh.

All five backend services, the Postgres/Redis/Kafka/MinIO infrastructure, the
nginx API gateway, and the React frontend are implemented. This README covers
bringing the whole stack up from a clean clone.

---

## What's running

| Service | Port (direct) | Routed through nginx at |
|---|---|---|
| PostgreSQL | 5432 | — |
| Redis | 6379 | — |
| Kafka + Zookeeper | 9092 (internal), 29092 (host) | — |
| MinIO (S3-compatible storage) | 9000 (API), 9001 (console) | — |
| Auth Service | 8001 | `/api/v1/auth/*` |
| Traffic Service | 8002 | `/api/v1/traffic/*` |
| Complaint Service | 8003 | `/api/v1/complaints/*` |
| Alert Service | 8004 | `/api/v1/alerts/*` |
| ML Service | 8005 | `/api/v1/predict/*` |
| Nginx (gateway + frontend) | 80 | `/` |

The direct service ports are exposed on the host for debugging (curl,
`/docs`), but the frontend and any real client should only ever talk to
nginx on port 80 — that's the single origin that has CORS, rate limiting,
and routing all set up.

---

## First-time setup

### 1. Copy the environment file
```bash
cp .env.example .env
```
Edit `.env` and replace every `change_me_*` placeholder with a real, unique
value — `POSTGRES_PASSWORD`, `AUTH_DB_PASSWORD`, `TRAFFIC_DB_PASSWORD`,
`COMPLAINT_DB_PASSWORD`, `ALERT_DB_PASSWORD`, `MINIO_ROOT_PASSWORD`. Each
`*_DATABASE_URL` embeds its matching `*_DB_PASSWORD` — keep them in sync.
`.env` is gitignored — never commit it.

> **If you're picking up this repo after August 2026**: an earlier version
> of `database/seeds/init_db_users.sql` had a real password hardcoded in
> plain text and committed to git. It's been replaced with an env-var-driven
> script, but that old password is still in git history — treat it as
> burned and make sure it isn't reused anywhere.

### 2. Generate JWT signing keys
```bash
chmod +x scripts/generate_jwt_keys.sh
./scripts/generate_jwt_keys.sh
```
Creates `secrets/jwt_private_key.pem` (auth-service only) and
`secrets/jwt_public_key.pem` (mounted read-only into every other service, for
verification only). Mounted as Docker secrets, never baked into images.

### 3. Bring up the full stack
```bash
docker compose up -d --build
```
First run takes several minutes (pulling base images, building 5 Python
services, installing `easyocr`/`torch` for complaint-service in particular).

Check everything is healthy:
```bash
docker compose ps
```
If anything shows unhealthy: `docker compose logs <service-name>`.

### 4. Run each service's database migrations
Every service owns and migrates its own tables, using its own restricted DB
user (see **Security model** below for why):
```bash
docker compose exec auth-service      alembic upgrade head
docker compose exec traffic-service   alembic upgrade head
docker compose exec complaint-service alembic upgrade head
docker compose exec alert-service     alembic upgrade head
```
(ml-service has no database — it's a stateless prediction service.)

### 5. Lock down DB permissions
```bash
docker exec -i devbhumi-postgres psql -U devbhumi_admin -d devbhumi \
  < database/seeds/grant_permissions.sql
```
Safe to re-run any time — every grant is idempotent.

### 6. Seed reference data
```bash
docker compose exec traffic-service   python -m scripts.seed_checkpoints
docker compose exec complaint-service python -m scripts.seed_police_stations
```

### 7. Train the crowd-prediction model
```bash
docker compose exec ml-service python -m scripts.train_model
```
Trains on synthetic data (~30s on CPU) and writes artifacts to
`model_artifacts/`. The repo already ships pre-trained artifacts, so this
step is only needed if you want to retrain.

### 8. Create the first admin account
```bash
docker compose exec auth-service python -m scripts.create_admin
```
Prompted interactively for name, phone, and password. `police`, `admin`, and
`emergency_team` accounts can only be created this way, or by an existing
admin — public self-registration only allows `tourist`/`citizen`.

### 9. Open the app
**http://localhost** — the frontend, served by nginx, calling the API
through the same origin.

---

## Verifying the backend works

### Health checks (direct per-service port)
```bash
curl http://localhost:8001/health   # auth
curl http://localhost:8002/health   # traffic
curl http://localhost:8003/health   # complaint
curl http://localhost:8004/health   # alert
curl http://localhost:8005/health   # ml — check "model_ready": true
```
Only `/api/v1/*` is routed through nginx by design (see
`nginx/conf.d/default.conf`) — `/health` isn't part of the public API
surface, so it's checked directly per-service here, which is also what each
container's own Docker `HEALTHCHECK` does internally.

### Register a tourist account and log in
```bash
curl -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Tourist","phone":"+919876543210","password":"TestPass123","role":"tourist"}'

curl -i -c cookies.txt -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=+919876543210&password=TestPass123"
```
Returns `access_token` in the body. The refresh token is set as an
`HttpOnly`, `SameSite=Lax` cookie (via `-c cookies.txt`), scoped to
`/api/v1/auth` — it's never exposed to frontend JS, so an XSS bug elsewhere
can't exfiltrate it.

```bash
# Refresh
curl -X POST http://localhost/api/v1/auth/refresh -b cookies.txt

# Protected route
curl http://localhost/api/v1/auth/me -H "Authorization: Bearer <access_token>"

# Logout — blacklists both the access and refresh token
curl -X POST http://localhost/api/v1/auth/logout \
  -H "Authorization: Bearer <access_token>" -b cookies.txt
```

Interactive API docs per service (FastAPI auto-generated):
`http://localhost:8001/docs` (auth), `:8002` (traffic), `:8003` (complaint),
`:8004` (alert), `:8005` (ml).

---

## Running tests

Each backend service has its own unit test suite, run inside its own
Dockerfile's Python version (3.11):
```bash
docker compose build auth-service && docker run --rm devbhumi-auth-service pytest tests/ -v
# same pattern for traffic-service / complaint-service / alert-service / ml-service
```
(swap the image name — `docker compose build <service>` tags it as
`<project>-<service>`; check with `docker images` if unsure.)

If Docker isn't available, each service's tests also run in a plain Python
3.11 venv with no external services required (Postgres/Redis/Kafka/S3 are
all mocked at the unit level):
```bash
cd services/<service-name>
py -3.11 -m venv .venv && .venv/Scripts/pip install -r requirements.txt pytest
.venv/Scripts/pytest tests/ -v
```

Frontend:
```bash
cd frontend
npm install
npm run build   # type-checks + builds to dist/, which nginx serves
npm run lint
```

---

## Project structure
```
devbhumi/
├── docker-compose.yml            # all 5 services + postgres/redis/kafka/minio/nginx
├── .env.example
├── secrets/                      # gitignored — JWT keys live here
├── nginx/
│   ├── nginx.conf                # rate-limit zones, gzip, security header baseline
│   └── conf.d/
│       ├── default.conf          # routes /api/v1/* to each service, serves frontend/dist
│       └── proxy_common.inc      # shared proxy_set_header block
├── services/
│   ├── auth-service/             # registration, login, JWT issuance, RBAC
│   ├── traffic-service/          # checkpoint/vehicle entries, live district density
│   ├── complaint-service/        # citizen complaints, OCR plate extraction, S3/MinIO photos
│   ├── alert-service/            # geofenced emergency alerts, FCM push (optional)
│   └── ml-service/                # XGBoost crowd prediction, stateless
│       # each service follows the same layout:
│       # Dockerfile, requirements.txt, alembic/, app/{core,models,repositories,routes,schemas,services},
│       # scripts/, tests/
├── database/
│   └── seeds/                    # init_db_users.sh, grant_permissions.sql
├── scripts/                       # generate_jwt_keys.sh
└── frontend/                      # React + TypeScript + Tailwind + Leaflet
    └── src/{api,components,context,pages,types}/
```

---

## Security model

- **RS256 JWT** (asymmetric) — auth-service's private key signs; every other
  service verifies with the public key only. No shared secret.
- **Access token**: 15 min TTL, returned in the response body — held in
  frontend memory only, never persisted (localStorage/sessionStorage). Lost
  on page reload by design.
- **Refresh token**: 7 days TTL, set as an `HttpOnly`, `SameSite=Lax` cookie
  scoped to `/api/v1/auth` — never readable by frontend JS. The frontend
  silently calls `/auth/refresh` on load to resume a session.
- **Token blacklisting**: logout adds both the access and refresh token's
  `jti` to Redis; checked on every authenticated request and on `/refresh`.
- **RBAC**: enforced via a `require_role()` dependency at the route level in
  every service — never inferred inside business logic.
- **Self-registration restricted**: public `/register` can only create
  `tourist` or `citizen` accounts. `police`, `admin`, `emergency_team`
  require an existing admin (bootstrap the first one via `create_admin.py`).
- **Generic login errors**: wrong password and non-existent phone return an
  identical error — prevents account enumeration.
- **Per-service restricted DB users**: each service (`auth_svc`,
  `traffic_svc`, `complaint_svc`, `alert_svc`) has `SELECT/INSERT/UPDATE`
  (never `DELETE`) on only the tables it owns — see
  `database/seeds/grant_permissions.sql`. If one service's container is
  fully compromised, its DB user can't touch any other service's data.
  `audit_logs` is additionally INSERT/SELECT-only (no UPDATE) — append-only.
- **Non-root Docker containers**: every service runs as `appuser` (uid 1001).
- **Nginx edge**: rate limiting (5/min on auth, 20/min on anonymous
  complaint submission, 10/s general), security headers (CSP, X-Frame-Options,
  etc.), 10MB request body cap.

---

## Known gotchas already fixed

- `bcrypt==5.0.0` breaks `passlib==1.7.4` (removed attribute passlib reads,
  plus stricter 72-byte truncation). Pinned to `bcrypt==4.0.1` in
  auth-service. Don't upgrade without re-running `tests/test_security.py`.
- `python-bidi==0.6.x` breaks `easyocr==1.7.1`'s import of `get_display`.
  Pinned to `python-bidi==0.4.2` in complaint-service.
- The committed ml-service model artifacts were pickled under
  scikit-learn 1.8.0; requirements.txt is pinned to match (was 1.4.2, which
  raised `InconsistentVersionWarning` and risked silently wrong predictions).
- Postgres 15+ no longer grants `CREATE` on the `public` schema to new users
  by default, but every service migrates its own tables using its own
  restricted user — `init_db_users.sh` explicitly grants `CREATE` to each
  service user for this reason.

---

## Known limitations / what to verify next

This was built and reviewed without a working local Docker daemon (sandbox
limitation — Docker Desktop's engine wouldn't start). Every service's unit
test suite was run and passes in a version-matched local Python 3.11 venv
instead, and `docker compose config` confirms the compose file itself is
valid, but **a real `docker compose up` end-to-end run has not been done**.
Before relying on this for a demo or thesis evaluation, run through the
setup steps above once with Docker actually up, and:

- Confirm all 5 services + nginx report healthy in `docker compose ps`.
- Walk one full flow through the actual UI: register → login → view the
  tourist density map → submit a complaint (as citizen/police/admin — see
  note below) → broadcast + receive an emergency alert.
- `ml-service`'s prediction pipeline (`predictor.py`) has no dedicated unit
  tests (only schema/data-generator tests exist) — worth adding before
  trusting it unattended.

One product-design note surfaced during the frontend build: complaint
submission requires an authenticated `citizen`/`police`/`admin`/
`emergency_team` account — **`tourist` accounts cannot file complaints** by
current design (`POST /api/v1/complaints` explicitly excludes that role).
"Anonymous" in this service means anonymous *to police* (their identity
isn't shown in the police-facing view), not anonymous/no-login. If tourists
should be able to report incidents too, that's a role-restriction change in
`services/complaint-service/app/routes/complaint.py`, not a bug fix.

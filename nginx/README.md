# Nginx reverse proxy

Fronts all five backend services and serves the built frontend as static
files. Started as part of the main `docker-compose.yml` (`nginx` service).

- `nginx.conf` — worker/event tuning, gzip, security headers baseline,
  and the three `limit_req_zone` rate-limit definitions.
- `conf.d/default.conf` — the actual server block: routes `/api/v1/auth/*`,
  `/api/v1/traffic/*`, `/api/v1/complaints/*`, `/api/v1/alerts/*`, and
  `/api/v1/predict/*` to their respective upstream service, and serves
  `frontend/dist/` (SPA fallback to `index.html`) for everything else.
- `conf.d/proxy_common.inc` — shared `proxy_set_header` block, included by
  every API location. Deliberately named `.inc`, not `.conf` — nginx.conf
  globs `conf.d/*.conf`, and a `.conf` file here would be loaded twice.

Rate limits: 5 req/min on `/api/v1/auth/*` (credential-stuffing surface),
20 req/min on `/api/v1/complaints/*` (anonymous, unauthenticated
submission), 10 req/s general elsewhere.

To validate the config without starting the full stack:
```bash
docker run --rm \
  -v "$(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" \
  -v "$(pwd)/nginx/conf.d:/etc/nginx/conf.d:ro" \
  nginx:1.27-alpine nginx -t
```

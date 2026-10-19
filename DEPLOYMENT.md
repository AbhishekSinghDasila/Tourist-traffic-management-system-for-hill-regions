# Deployment

## GitHub

Target repository: https://github.com/AbhishekSinghDasila/Tourist-traffic-management-system-for-hill-regions

GitHub stores source and runs CI. This five-service application needs a server
with Docker; GitHub Pages cannot run its Python APIs or databases.

Before publishing, run frontend build/lint, backend tests, and the Docker smoke
test below. Push a review branch based on the latest remote main branch; do not
replace remote history with the ZIP's contents blindly. Never commit .env,
secrets/, virtual environments, dependency directories, or database volumes.
The included .github/workflows/ci.yml checks frontend, backend, and Compose.

## Local full stack

1. Start Docker Desktop in Linux-container mode.
2. Run python -m pip install cryptography.
3. Run python scripts/setup.py (preserves existing .env and keys).
4. Run python scripts/start.py (build, migrate, seed, start).
5. Run docker compose exec auth-service python -m scripts.create_admin.
6. Open http://localhost and sign in. Use User accounts in the admin panel
   to provision officers and emergency staff.

For repeat deployments, back up the database and object storage before running
migrations. The startup script stops on failure and never deletes volumes.
Use docker compose down to stop; do not add -v unless you intend to erase data.

## Smoke test checklist

- Register a citizen and a tourist; log in and reload to verify cookie refresh.
- Tourist: density map loads tiles; prediction returns data for Nainital.
- Citizen: submit a real image, then see the complaint in My complaints.
- Police in the same district: see the complaint without citizen identity.
- Admin: inspect that complaint and open its temporary image URL.
- Emergency/admin: create an alert; a tourist sees it through polling.
- Admin: dismiss the cancel dialog and verify the alert stays active;
  then confirm cancellation and verify it disappears from active alerts.
- Citizen: requests to /api/v1/auth/users must return 403.
- Log out, reload, and verify authenticated pages are inaccessible.

## Live server

Provision a Linux Docker host with adequate memory/disk for OCR and Kafka.
Set DNS for your domain and terminate HTTPS at an edge proxy in front of port 80.
Set ENVIRONMENT=production so refresh cookies require HTTPS.
Keep database, Redis, Kafka, service-debug, and MinIO admin ports private
(Compose binds them to localhost). Back up Postgres and MinIO volumes.

For media access, place the MinIO S3 API behind a separate HTTPS hostname and set
S3_PUBLIC_ENDPOINT_URL to that hostname before starting the complaint service.
The signer must use the public hostname; do not rewrite generated signed URLs.
The proxy must preserve the signed host and path. The MinIO console should
remain private. Verify image access with the actual browser used for the demo.

The repository contains local deployment tooling; a live deployment still needs
your hosting account/server, domain, TLS, and deployment credentials.
Do not enable Firebase notifications until Firebase credentials and client
device registration have been configured and tested.

## Optional Vercel frontend + Render backend

This is an operator configuration path, not an already deployed service.

1. Deploy each Python service on Render using its service directory as the
   Docker build context. Configure its environment variables from .env.example.
   Use Render Postgres, a Redis-compatible service, and external S3 storage.
   Kafka requires an additional broker deployment if event publishing is needed.
2. Upload the JWT private key only to auth-service and the public key to the
   verifying services as secret files. Point their JWT paths at those files.
3. Run migrations and seeds with the correct database credentials. Keep the
   services in the same region/private network, and deploy an API gateway with
   upstream names replaced by their Render private addresses. The gateway is
   the publicly reachable Render web service.
4. Import the GitHub repository into Vercel with Root Directory = frontend,
   build command npm run build, and output directory dist.
5. Copy frontend/vercel.json.example to frontend/vercel.json and replace the
   gateway placeholder with its real HTTPS URL before deploying. The API rewrite
   keeps browser authentication on the frontend origin. Validate refresh cookies
   through the actual proxy before sharing the site.
6. Set ENVIRONMENT=production and the public HTTPS S3 endpoint. Test every flow
   in the smoke checklist above on the hosted deployment.

Render's private services and persistent disks may require paid resources.
Do not provision them until the hosting plan and costs have been chosen.
Official references: [Vercel rewrites](https://vercel.com/docs/routing/rewrites),
[Render Docker](https://render.com/docs/docker),
[Render private services](https://render.com/docs/private-services),
[Render persistent disks](https://render.com/docs/disks).

MinIO images are built from pinned upstream community sources in deploy/minio.
The original Docker Hub and Quay image references returned access errors during
validation. Source builds require access to the Go module proxy and can be slow.

# Validation status — 19 October 2026

## Passed locally

- Frontend: npm ci, npm run build, npm run lint (zero errors; three existing
  React fast-refresh export warnings).
- Backend unit/regression suites: auth 14, traffic 8, complaint 12, alert 15,
  ML 21 — 70 passing tests. These ran locally using Python 3.12; CI targets
  the Docker runtime's Python 3.11.
- The traffic suite also passed inside its Python 3.11 Docker image.
- CPU-only XGBoost model retraining, artifact reload, and Nainital prediction.
  Training used 10,000 synthetic samples; this does not establish real-world accuracy.
- docker compose --env-file .env.example config --quiet.
- Python source compilation and git diff --check.
- On 18 October: Postgres/Redis/traffic were healthy; migrations and 18 checkpoint
  seeds succeeded; traffic API returned 11 districts.
- On 18 October: real auth API smoke passed registration, login, identity,
  admin denial, refresh, logout, and token revocation.
- Built frontend landing/registration navigation inspected in the browser.

## Not yet established locally

- Complete gateway → complaint upload → storage → police/admin privacy →
  alert → prediction integration. scripts/smoke_stack.py and the integration
  CI job cover this; their result must be checked before declaring deployment ready.
- Full OCR model download and recognition. CI's full-stack smoke deliberately uses
  INSTALL_OCR=false and USE_OCR=false; OCR remains available in the normal build.
- Firebase delivery to real devices, live traffic hardware, and public hosting.

The resumed local Docker engine failed at startup because Windows could not
access Docker's stale sailor-ingest.sock runtime file. Attempts to remove that
socket failed; no Docker data volumes were deleted or reset.

## GitHub / hosting

The source was compared against the current repository; it matched the supplied
ZIP before these changes. Work is prepared on codex/complete-project-deployment.
Check the branch's latest GitHub Actions result for post-push verification.
Vercel/Render setup is documented but no public site has been deployed.

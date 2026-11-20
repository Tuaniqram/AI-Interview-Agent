#!/bin/bash
# Full deploy on the instabox host: pull prod, install, build the frontend, restart both services, check health.
# Called by the "Deploy to instabox" step of .github/workflows/sync-prod.yml, and safe to run by hand.
set -euo pipefail
cd ~/AI-Interview-Agent

git fetch -q origin prod
git reset --hard origin/prod

# backend
source app/.venv/bin/activate
pip install -q --disable-pip-version-check -r requirements.txt
# alembic upgrade head      # enable for additive migrations only; apply destructive ones by hand

# frontend: a static build (the Vite dev server must not run in production)
cd frontend
npm ci --silent --no-audit --no-fund
npm run build --silent
cd ..

~/AI-Interview-Agent/start.sh

curl -fsS --retry 20 --retry-delay 3 --retry-all-errors http://127.0.0.1:8000/health >/dev/null
curl -fsS --retry 10 --retry-delay 2 --retry-all-errors http://127.0.0.1:5173/ >/dev/null
echo "Deployed $(git rev-parse --short HEAD)"

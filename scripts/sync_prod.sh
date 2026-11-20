#!/usr/bin/env bash
# Copy what gets deployed from a checkout of `main` into a checkout of `prod`, and stage it there.
#
#   scripts/sync_prod.sh <main-checkout> <prod-checkout>
#
# `prod` is the deploy branch: the backend (Render) AND the frontend (Vercel) live on it and nothing else (no tests,
# docs or tools; see its .gitignore allow-list). It is NOT merged from main: a merge would bring back everything prod
# deliberately drops. Only the paths below are copied, so render.yaml and prod's own .gitignore are never touched.
# Run by .github/workflows/sync-prod.yml.
set -euo pipefail

SRC="${1:?usage: sync_prod.sh <main-checkout> <prod-checkout>}"
DST="${2:?usage: sync_prod.sh <main-checkout> <prod-checkout>}"

DIRS=(app prompts alembic frontend)
FILES=(alembic.ini requirements.txt runtime.txt .env.example)
# Never needed to build or serve the frontend (build output, installed packages, end-to-end tests and their reports).
FRONTEND_EXCLUDES=(node_modules dist e2e playwright-report test-results .vite playwright.config.ts)

for p in "${DIRS[@]}"; do
  [ -d "$SRC/$p" ] || { echo "error: '$p/' is missing from the main checkout" >&2; exit 1; }
done
for p in "${FILES[@]}"; do
  [ -f "$SRC/$p" ] || { echo "error: '$p' is missing from the main checkout" >&2; exit 1; }
done
[ -f "$SRC/frontend/package.json" ] || { echo "error: frontend/package.json is missing from the main checkout" >&2; exit 1; }
[ -f "$DST/render.yaml" ] || { echo "error: $DST does not look like the prod branch (no render.yaml)" >&2; exit 1; }

for p in "${DIRS[@]}"; do
  rm -rf "${DST:?}/$p"          # replace the whole folder so files deleted on main disappear from prod too
  cp -R "$SRC/$p" "$DST/$p"
  find "$DST/$p" -name __pycache__ -type d -prune -exec rm -rf {} +
done
for x in "${FRONTEND_EXCLUDES[@]}"; do
  rm -rf "${DST:?}/frontend/$x"
done
for p in "${FILES[@]}"; do
  cp "$SRC/$p" "$DST/$p"
done

git -C "$DST" add -A -- "${DIRS[@]}" "${FILES[@]}"
if git -C "$DST" diff --cached --quiet; then
  echo "prod is already up to date"
else
  git -C "$DST" diff --cached --stat | tail -n 1
fi

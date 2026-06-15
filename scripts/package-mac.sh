#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYINSTALLER="${PYINSTALLER:-/Library/Frameworks/Python.framework/Versions/3.14/bin/pyinstaller}"

cd "$ROOT_DIR/backend"
"$PYINSTALLER" \
  --clean \
  --onefile \
  --name focus-task-backend \
  --hidden-import passlib.handlers.bcrypt \
  --add-data "alembic:alembic" \
  --add-data "alembic.ini:." \
  app_server.py

cd "$ROOT_DIR"
node scripts/e2e-smoke.mjs

cd "$ROOT_DIR/frontend"
npm test
npm run build

cd "$ROOT_DIR/frontend/src-tauri"
cargo tauri build --bundles app

echo "Focus Task.app generated:"
echo "$ROOT_DIR/frontend/src-tauri/target/release/bundle/macos/Focus Task.app"

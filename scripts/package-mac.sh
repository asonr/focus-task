#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYINSTALLER="${PYINSTALLER:-/Library/Frameworks/Python.framework/Versions/3.14/bin/pyinstaller}"

cd "$ROOT_DIR/backend"
"$PYINSTALLER" \
  --clean \
  --noconfirm \
  --name focus-task-backend \
  --hidden-import passlib.handlers.bcrypt \
  --add-data "alembic:alembic" \
  --add-data "alembic.ini:." \
  app_server.py

# Tauri's resource collector does not preserve the Python framework symlink
# layout reliably. Materialize symlinks into a dedicated bundle directory.
mkdir -p "$ROOT_DIR/backend/dist/focus-task-backend-bundle"
rsync -aL --delete \
  "$ROOT_DIR/backend/dist/focus-task-backend/" \
  "$ROOT_DIR/backend/dist/focus-task-backend-bundle/"

cd "$ROOT_DIR"
node scripts/e2e-smoke.mjs

cd "$ROOT_DIR/frontend"
npm test
npm run build

cd "$ROOT_DIR/frontend/src-tauri"
cargo tauri build --bundles app

APP_PATH="$ROOT_DIR/frontend/src-tauri/target/release/bundle/macos/Focus Task.app"
mkdir -p "$APP_PATH/Contents/Resources/backend"
rsync -a --delete \
  "$ROOT_DIR/backend/dist/focus-task-backend-bundle/" \
  "$APP_PATH/Contents/Resources/backend/"
codesign --force --deep --sign - "$APP_PATH"

echo "Focus Task.app generated:"
echo "$APP_PATH"

#!/usr/bin/env bash
# Put new code from GitHub live on the server:  bash deploy/oracle/update.sh
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$APP_DIR"
git pull --ff-only
PIP="$APP_DIR/backend/.venv/bin/python -m pip"
TORCH_PIN="$(grep -E '^torch==' backend/requirements.txt | head -1)"
$PIP install "${TORCH_PIN:-torch}" --index-url https://download.pytorch.org/whl/cpu
$PIP install -r backend/requirements.txt
( cd frontend/frontend && npm ci && npm run build )
sudo systemctl restart enterprise-ai
sleep 5
systemctl is-active enterprise-ai && curl -fsS http://127.0.0.1:8000/health && echo

#!/usr/bin/env bash
# Push code (and your local config/*.yaml) from the Mac to the Pi, then restart.
#   bash deploy/deploy.sh pi@raspberrypi.local            # code + config
#   bash deploy/deploy.sh pi@raspberrypi.local --photos   # also sync photos/
# Secrets (.env), the database and caches stay on the Pi and are never overwritten.
# config/frame.yaml and config/chores.yaml: if you have them on the Mac they are
# copied over the Pi's; if you don't, the Pi's copies are left alone.
# Photos are only ever added, never deleted from the Pi.
set -euo pipefail
TARGET="${1:?usage: deploy.sh user@host [--photos]}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE_DIR="doorpost"

rsync -az --delete \
  --exclude .git --exclude .venv --exclude data --exclude photos --exclude .env \
  --exclude __pycache__ --exclude .pytest_cache \
  --filter 'P config/frame.yaml' --filter 'P config/chores.yaml' \
  "$DIR/" "$TARGET:$REMOTE_DIR/"

if [ "${2:-}" = "--photos" ]; then
  rsync -az --exclude .gitkeep "$DIR/photos/" "$TARGET:$REMOTE_DIR/photos/"
fi

ssh "$TARGET" "cd $REMOTE_DIR && .venv/bin/pip install -q -r requirements.txt && sudo systemctl restart doorpost && sleep 2 && curl -fsS localhost:8090/healthz"
echo
echo "Deployed."

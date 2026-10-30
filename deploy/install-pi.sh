#!/usr/bin/env bash
# First-time setup ON THE PI (or any always-on Linux box). Safe to re-run.
#   cd ~/doorpost && bash deploy/install-pi.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="$(whoami)"
cd "$DIR"

echo "==> Packages"
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv python3-pip libjpeg-dev zlib1g-dev >/dev/null

echo "==> Python environment"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

echo "==> Config (existing files are left alone)"
[ -f config/frame.yaml ] || cp config/frame.example.yaml config/frame.yaml
[ -f config/chores.yaml ] || cp config/chores.example.yaml config/chores.yaml
[ -f .env ] || { cp .env.example .env; chmod 600 .env; }
grep -q '^FRAME_SECRET=.\+' .env || .venv/bin/python -m app.tools new-secret
mkdir -p data photos

echo "==> Service"
sed -e "s|__USER__|$USER_NAME|" -e "s|__DIR__|$DIR|" deploy/doorpost.service \
  | sudo tee /etc/systemd/system/doorpost.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now doorpost.service

IP="$(hostname -I | awk '{print $1}')"
cat <<EOF

Done. Doorpost is running at  http://$IP:8090/
Settings:                     http://$IP:8090/admin
Parent phone page:            http://$IP:8090/parent

Next, from a laptop on your home Wi-Fi (see docs/setup-guide.md):
  1. Open Settings and add your location, family, calendars, chores
     and a PIN for each parent.
  2. Give this Pi a fixed address in your router ($IP now).
  3. Check calendars and weather:  .venv/bin/python -m app.tools check
Optional extras (Home Assistant token, weather contact email) go in .env;
restart after editing it:  sudo systemctl restart doorpost
EOF

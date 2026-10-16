#!/usr/bin/env bash
# Assemble the Home Assistant add-on into dist/family_frame/.
# Copy that folder into Home Assistant's "local_apps" share, then in HA:
# Settings > Apps (add-ons) > store > (menu) Check for updates > Local apps > Doorpost.
#
# A private overlay (local/, see docs/private-overlay.md) goes in too, when there is one:
#   local/config, local/packs, local/themes, local/web    copied into the add-on as local/...
#   local/addon/addon.conf                                 name, sidebar title and version start (see below)
#   local/addon/icon.png, local/addon/logo.png             your own add-on icon and logo
# Never copied: local/.env, local/scripts, local/denylist.txt and anything else in local/.
# FRAME_LOCAL_DIR=/some/folder uses that folder as local/ instead.
set -euo pipefail
cd "$(dirname "$0")/.."

LOCAL="${FRAME_LOCAL_DIR:-local}"
CONF="$LOCAL/addon/addon.conf"

# One setting from addon.conf (KEY=value lines; read as text, never run).
conf() {
  local v=""
  if [ -f "$CONF" ]; then
    v="$(grep -E "^$1=" "$CONF" | tail -n 1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"
  fi
  printf '%s' "${v:-$2}"
}

OUT="${ADDON_OUT:-dist/family_frame}"   # ADDON_OUT builds somewhere else (the tests do)
# Home Assistant only offers an update when the version goes up. ADDON_VERSION_PREFIX in addon.conf lets a
# private copy start above a version it installed before (for example 2.0 after 1.1.70).
PREFIX="$(conf ADDON_VERSION_PREFIX 1.1)"
VERSION="${ADDON_VERSION:-$PREFIX.$(git rev-list --count HEAD 2>/dev/null || echo 0)}"
NAME="$(conf ADDON_NAME Doorpost)"
PANEL="$(conf ADDON_PANEL_TITLE "$NAME")"
rm -rf "$OUT"
mkdir -p "$OUT"

cp addon/family_frame/{Dockerfile,run.sh,DOCS.md,README.md,icon.png,logo.png} "$OUT/"
esc() { printf '%s' "$1" | sed -e 's/[\/&|]/\\&/g'; }
sed -e "s/__VERSION__/$VERSION/" \
    -e "s|^name: .*|name: $(esc "$NAME")|" \
    -e "s|^panel_title: .*|panel_title: $(esc "$PANEL")|" \
    addon/family_frame/config.yaml > "$OUT/config.yaml"
cp requirements.txt "$OUT/"
rsync -a --exclude __pycache__ app "$OUT/"
rsync -a web "$OUT/"
rsync -a packs "$OUT/"   # the built-in art packs and the list of packs to install
rsync -a themes "$OUT/"  # the looks (app/themes.py)
mkdir -p "$OUT/config"
cp config/frame.example.yaml config/chores.example.yaml "$OUT/config/"   # defaults; the panel saves over them

mkdir -p "$OUT/local"   # always there, so the Dockerfile's COPY works without an overlay
OVERLAY="none"
if [ -d "$LOCAL" ]; then
  OVERLAY=""
  for part in config packs themes web; do
    if [ -d "$LOCAL/$part" ]; then
      rsync -a --exclude .DS_Store --exclude __pycache__ "$LOCAL/$part" "$OUT/local/"
      OVERLAY="$OVERLAY $part"
    fi
  done
  for img in icon.png logo.png; do
    if [ -f "$LOCAL/addon/$img" ]; then cp "$LOCAL/addon/$img" "$OUT/$img"; OVERLAY="$OVERLAY addon/$img"; fi
  done
  OVERLAY="${OVERLAY:- (empty)}"
fi
touch "$OUT/local/.keep"
chmod +x "$OUT/run.sh"

echo "Built $OUT (version $VERSION, name \"$NAME\", private overlay:$OVERLAY)"
echo
echo "Next: copy it into Home Assistant's local_apps share, e.g."
echo "  Finder > Go > Connect to Server > smb://${HA_HOST:-homeassistant.local}/local_apps, drag the family_frame folder in"
echo "  or: bash scripts/push-addon.sh   (if the share is already mounted at /Volumes/local_apps)"

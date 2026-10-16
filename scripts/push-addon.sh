#!/usr/bin/env bash
# Build the add-on and copy it into Home Assistant's "local_apps" Samba share.
# Mount the share first: Finder > Go > Connect to Server > smb://<your HA host>/local_apps
#   HA_HOST=homeassistant.local ADDONS_SHARE=/Volumes/local_apps bash scripts/push-addon.sh
set -euo pipefail
HA_HOST="${HA_HOST:-homeassistant.local}"
cd "$(dirname "$0")/.."
SHARE="${ADDONS_SHARE:-/Volumes/local_apps}"
[ -d "$SHARE" ] || { echo "The local_apps share isn't mounted at $SHARE. Connect to smb://$HA_HOST/local_apps first."; exit 1; }

bash scripts/build-addon.sh
rsync -a --delete dist/family_frame/ "$SHARE/family_frame/"
echo
echo "Copied. In Home Assistant: Settings > Apps > store > (menu) Check for updates."
echo "First time: open Local apps > Doorpost > Install. After that, it shows as an Update."

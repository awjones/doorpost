#!/usr/bin/env bash
# Send your Apple Photos *Favorites* to the frame, and remove ones you un-favorite.
# Run on the Mac that has the Photos library (one that stays on). Safe to run any time;
# only new favorites are uploaded. Schedule it hourly (see docs/photos.md).
#
#   FRAME_URL=http://doorpost.local:8090 FRAME_UPLOAD_TOKEN=<from Settings > Photos> \
#     bash scripts/sync-apple-favorites.sh
#
# Needs osxphotos (reads the Photos library):  brew install pipx && pipx install osxphotos
# The first run asks macOS for Photos access for Terminal.
set -euo pipefail
shopt -s nullglob nocaseglob   # iPhone originals can be .JPG
: "${FRAME_URL:?Set FRAME_URL, e.g. http://doorpost.local:8090}"
: "${FRAME_UPLOAD_TOKEN:?Set FRAME_UPLOAD_TOKEN (copy it from Settings > Photos)}"
EXPORT_DIR="${EXPORT_DIR:-$HOME/Pictures/Doorpost Favorites}"
SENT="$EXPORT_DIR/.sent-to-frame"
OSXPHOTOS="$(command -v osxphotos || echo "$HOME/.local/bin/osxphotos")"
[ -x "$OSXPHOTOS" ] || { echo "osxphotos isn't installed. Run: brew install pipx && pipx install osxphotos"; exit 1; }

mkdir -p "$EXPORT_DIR"
touch "$SENT"

# 1. Mirror Favorites into a local folder as JPEGs. --update skips ones already
#    exported; --cleanup deletes files whose photo is no longer a favorite.
"$OSXPHOTOS" export "$EXPORT_DIR" \
  --favorite --only-photos --not-hidden \
  --convert-to-jpeg --jpeg-ext jpg --jpeg-quality 0.85 \
  --skip-original-if-edited --skip-live --skip-raw \
  --download-missing \
  --filename "{created.strftime,%Y%m%d-%H%M%S}-{uuid}" \
  --update --cleanup --keep "$(basename "$SENT")" --no-progress >/dev/null

# 2. Upload the new ones, shrunk to 1920 px (the frame shows 1280x800).
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
uploaded=0
for f in "$EXPORT_DIR"/*.jpg "$EXPORT_DIR"/*.jpeg; do
  name="$(basename "$f")"
  grep -qxF "$name" "$SENT" && continue
  sips -Z 1920 "$f" --out "$TMP/$name" >/dev/null
  curl -fsS -H "X-Upload-Token: $FRAME_UPLOAD_TOKEN" \
    -F "file=@$TMP/$name;type=image/jpeg" \
    "$FRAME_URL/api/photos/upload?source=apple-favorites" >/dev/null
  echo "$name" >> "$SENT"
  uploaded=$((uploaded + 1))
done

# 3. Tell the frame which favorites still exist, so un-favorited photos come off it.
list_local() { find "$EXPORT_DIR" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' \) -exec basename {} \; ; }
keep="$(list_local | sed 's/.*/"&"/' | paste -sd, - || true)"
removed="$(curl -fsS -H "X-Upload-Token: $FRAME_UPLOAD_TOKEN" -H "Content-Type: application/json" \
  -d "{\"keep\":[${keep}]}" "$FRAME_URL/api/photos/prune?source=apple-favorites")"
# Forget names that are gone locally, so a re-favorited photo uploads again.
list_local > "$SENT.tmp" && grep -xFf "$SENT.tmp" "$SENT" > "$SENT.new" || true
mv "$SENT.new" "$SENT"; rm -f "$SENT.tmp"

# 4. Where the faces are, so each photo's crop starts centered on the people (Settings > Photos can change it).
PYOSX="$(dirname "$(readlink "$OSXPHOTOS" 2>/dev/null || echo "$OSXPHOTOS")")/python"
faces=""
if [ -x "$PYOSX" ] && faces="$("$PYOSX" "$(dirname "$0")/apple-faces.py" "$EXPORT_DIR" 2>/dev/null)" && [ -n "$faces" ]; then
  faces="$(printf '{"faces": %s}' "$faces" | curl -fsS -H "X-Upload-Token: $FRAME_UPLOAD_TOKEN" -H "Content-Type: application/json" \
    --data-binary @- "$FRAME_URL/api/photos/faces?source=apple-favorites" || true)"
fi

# 5. (Off) Profile photos from Apple Photos' People. By default each person's photo is picked by hand in
#    Settings > Family instead. scripts/apple-portraits.py still works if run by hand.
portraits="off"

echo "Favorites synced: $uploaded new; frame says $removed; faces: ${faces:-none}; portraits: ${portraits:-none}"

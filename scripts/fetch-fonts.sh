#!/usr/bin/env bash
# Download the three open-source (OFL) fonts the frame uses into web/fonts/.
# The frame has no internet access, so fonts are served by our own server.
# Source: Fontsource via jsDelivr. Re-run any time; files are committed.
set -euo pipefail
cd "$(dirname "$0")/../web/fonts"

get() { # family-slug file-suffix
  local url="https://cdn.jsdelivr.net/fontsource/fonts/$1@latest/latin-$2.woff2"
  echo "  $1 $2"
  curl -fsSL "$url" -o "$1-$2.woff2"
}

for w in 400 500 600 700; do get libre-franklin "$w-normal"; done
for w in 500 600 700; do get playfair-display "$w-normal"; done
for w in 400 500; do get playfair-display "$w-italic"; done
get pinyon-script 400-normal
echo "Done."

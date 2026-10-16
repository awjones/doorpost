#!/bin/sh
# Look for private words (local/denylist.txt) outside local/. See scripts/check_private.py and docs/private-overlay.md.
#   scripts/check-private.sh                      the working copy
#   scripts/check-private.sh --commits A..B       commits: messages, every file version, paths
#   scripts/check-private.sh --pre-push NAME URL  what git is about to push (run by .githooks/pre-push)
# Exits 0 when clean, 1 on any hit, 2 when it can't run.
exec python3 "$(dirname "$0")/check_private.py" "$@"

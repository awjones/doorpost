#!/bin/sh
# Start Doorpost inside Home Assistant.
#   /data           this add-on's private storage (settings, chores, caches), included in HA backups
#   /media/family_frame   slideshow photos (also reachable from the Samba "media" share)
set -e
export FRAME_DATA_DIR=/data
export FRAME_CONFIG_DIR=/app/config
export FRAME_PHOTOS_DIR=/media/family_frame
export FRAME_ADDON=1
mkdir -p /media/family_frame
cd /app
exec uvicorn app.main:app --host 0.0.0.0 --port 8090 --no-access-log

"""Where the faces are in each exported favorite, from the Apple Photos library (run with osxphotos' Python).

Prints {"<exported file name>": [x, y]} as fractions across and down: the middle of the box around
all the faces Photos found. Doorpost uses it as the photo's starting focal point.
Usage: <osxphotos venv>/bin/python scripts/apple-faces.py "<export folder>"
"""
import json
import re
import sys
from pathlib import Path

import osxphotos

folder = Path(sys.argv[1])
uuids = {}
for f in folder.iterdir():
    m = re.search(r"-([0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12})\.jpe?g$", f.name, re.I)
    if m:
        uuids[m.group(1).upper()] = f.name

out = {}
db = osxphotos.PhotosDB()
for photo in db.photos(uuid=list(uuids)):
    faces = [fi for fi in photo.face_info if not fi.intrash]
    if not faces:
        continue
    w, h = photo.width, photo.height
    if photo.orientation in (5, 6, 7, 8):
        w, h = h, w
    if not w or not h:
        continue
    pts = [(fi.center[0] / w, fi.center[1] / h) for fi in faces]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x, y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    if 0 <= x <= 1 and 0 <= y <= 1:
        out[uuids[photo.uuid.upper()]] = [round(x, 4), round(y, 4)]
print(json.dumps(out))

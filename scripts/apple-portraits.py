"""Birthday portraits from Apple Photos (run with osxphotos' Python, from sync-apple-favorites.sh).

Asks the frame who needs a portrait (/api/portraits/wanted), finds each person in Photos' People by name, and uses
the cover photo you chose for them in Photos (its "key photo"). Someone without a cover gets their newest photo
where they're the only face, facing the camera and big enough to fill a portrait. Exports it,
shrinks it, and sends it with where the face is (the edited photo, as you see it in Photos: that's what
Photos measured the faces on). Only sends when the pick changed, and the frame never replaces a
portrait someone picked by hand.

Usage: FRAME_URL=... FRAME_UPLOAD_TOKEN=... <osxphotos venv>/bin/python scripts/apple-portraits.py <osxphotos cli>
Prints one line per person.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import osxphotos

FRAME, TOKEN = os.environ["FRAME_URL"].rstrip("/"), os.environ["FRAME_UPLOAD_TOKEN"]
OSXPHOTOS = sys.argv[1] if len(sys.argv) > 1 else "osxphotos"
MIN_FACE = 0.09          # face height as a share of the photo's shorter side: smaller is a crowd or a landscape
MAX_TURN = 0.6           # radians of head turn (yaw); more is a profile
CV = 3                   # how face spots are worked out; raise it to send everyone's photo again


def frame_get(path):
    req = urllib.request.Request(FRAME + path, headers={"X-Upload-Token": TOKEN})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def names_for(p):
    """The names to look for, in order: "Name in Apple Photos" from Settings (several allowed, comma-separated), then
    the frame's name and nicknames."""
    out = [n for n in (p.get("photos_name") or "").split(",")] + [p["name"], *p.get("aliases", [])]
    return [n.strip().lower() for n in out if n and n.strip()]


def _words(name):
    return re.sub(r"[^a-z0-9 ]+", " ", name.lower()).split()


def find_person(db_people, p):
    """Photos' person for this frame person. Your favorite people in Photos are tried first, then everyone. For each
    name on the list ("Name in Apple Photos" from Settings first, then the frame's name and nicknames): an exact
    name; then a Photos name containing all of its words ("Sam Lee" finds "Sam Lee Example"), the shortest
    if several; then a first-name match, only when just one person has it."""
    want = names_for(p)
    favorites = [x for x in db_people if getattr(x, "favorite", False)]
    for pool in ([favorites] if favorites else []) + [db_people]:
        for n in want:
            nw = _words(n)
            exact = [x for x in pool if _words(x.name) == nw]
            if exact:
                return max(exact, key=lambda x: len(x.photos)), ""
            within = [x for x in pool if nw and set(nw) <= set(_words(x.name))]
            if within:
                fewest = min(len(_words(x.name)) for x in within)
                best = [x for x in within if len(_words(x.name)) == fewest]
                if len({x.name for x in best}) == 1:
                    return max(best, key=lambda x: len(x.photos)), ""
        first = [x for x in pool if _words(x.name)[:1] and _words(x.name)[0] in {w for n in want for w in _words(n)[:1]}]
        if len({x.name for x in first}) == 1:
            return max(first, key=lambda x: len(x.photos)), ""
    return None, "no match in Apple Photos: set Name in Apple Photos on the Family page"


def cover(person):
    """The cover photo chosen for this person in Photos, and where their face is in it."""
    kp = getattr(person, "keyphoto", None)
    if not kp or kp.ismovie or kp.intrash:
        return None
    mine = [f for f in kp.face_info if f.person_info is not None and f.person_info.uuid == person.uuid]
    if not mine:
        return kp, None    # still the chosen photo; the frame looks for the face itself
    x, y, size = spot(mine[0], kp)
    return kp, ((x, y, size) if 0 <= x <= 1 and 0 <= y <= 1 else None)


def spot(f, photo):
    """Where a face is in the photo as you see it in Photos (edits included, which is what we export), as
    (x, y, size) fractions. Photos measures faces on the edited picture, so osxphotos' center over the current size."""
    w, h = oriented(photo)
    if not w or not h:
        return 0.5, 0.4, 0.2
    cx, cy = f.center
    return cx / w, cy / h, min(1.0, f.size_pixels / h)


def oriented(photo):
    w, h = photo.width, photo.height
    return (h, w) if photo.orientation in (5, 6, 7, 8) else (w, h)


def solo_face(photo, person):
    """This person's face, if it's the only face in the photo and a good portrait one: (x, y, size) fractions."""
    if photo.hidden or photo.intrash or photo.ismovie or getattr(photo, "screenshot", False):
        return None
    faces = list(photo.face_info)
    if len(faces) != 1 or faces[0].person_info is None or faces[0].person_info.uuid != person.uuid:
        return None
    f = faces[0]
    w, h = oriented(photo)
    if not w or not h:
        return None
    if f.size_pixels / min(w, h) < MIN_FACE or (f.yaw is not None and abs(f.yaw) > MAX_TURN):
        return None
    x, y, size = spot(f, photo)
    return (x, y, size) if 0 <= x <= 1 and 0 <= y <= 1 else None


def send(slug, path, photo, face):
    q = f"slug={slug}&taken={photo.date.isoformat()}&ref={photo.uuid}&cv={CV}"
    if face:   # otherwise the frame finds the face itself
        q += f"&fx={face[0]:.4f}&fy={face[1]:.4f}&fs={face[2]:.4f}"
    r = subprocess.run(["curl", "-fsS", "-H", f"X-Upload-Token: {TOKEN}", "-F", f"file=@{path};type=image/jpeg",
                        f"{FRAME}/api/portraits/upload?{q}"], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or "upload failed")
    return json.loads(r.stdout or "{}")


def main():
    try:
        wanted = frame_get("/api/portraits/wanted")
    except Exception as exc:  # an older frame without portraits: nothing to do
        print(f"portraits: skipped ({exc})")
        return
    db = osxphotos.PhotosDB()
    db_people = [x for x in db.person_info if x.name and x.name != "_UNKNOWN_"]
    missing = False
    for p in wanted:
        have = p.get("have") or {}
        if have and have.get("source") not in (None, "apple"):
            print(f"{p['name']}: keeping the {have['source']} portrait")
            continue
        person, why = find_person(db_people, p)
        if not person:
            print(f"{p['name']}: {why}")
            missing = True
            continue
        cands = []
        c = cover(person)
        if c:
            cands.append((c[0], c[1], "cover photo"))
        for photo in sorted(person.photos, key=lambda ph: ph.date, reverse=True):
            if len(cands) >= 6:
                break
            face = solo_face(photo, person)
            if face and not (c and photo.uuid == c[0].uuid):
                cands.append((photo, face, "newest solo photo"))
        if not cands:
            print(f"{p['name']}: no cover photo and no photo with only them in it")
            continue
        tried = []
        for photo, face, kind in cands:
            if have.get("ref") == photo.uuid and have.get("cv") == CV:   # same photo, same math: nothing to send
                print(f"{p['name']}: up to date ({person.name}, {kind})")
                break
            with tempfile.TemporaryDirectory() as tmp:
                r = subprocess.run([OSXPHOTOS, "export", tmp, "--uuid", photo.uuid, "--convert-to-jpeg", "--jpeg-ext", "jpg",
                                    "--skip-original-if-edited", "--skip-live", "--skip-raw", "--download-missing",
                                    "--filename", "portrait", "--no-progress"], capture_output=True, text=True, check=False)
                files = sorted(f for f in Path(tmp).glob("portrait*") if f.is_file())
                if not files:   # e.g. only in iCloud and it wouldn't download: try the next photo
                    err = (r.stderr or r.stdout or "").strip().splitlines()
                    tried.append(f"{kind} wouldn't export" + (f" ({err[-1][:80]})" if err else ""))
                    continue
                small = Path(tmp) / "small.jpg"
                subprocess.run(["sips", "-s", "format", "jpeg", "-Z", "1600", str(files[0]), "--out", str(small)], capture_output=True, check=False)
                try:
                    send(p["slug"], small if small.exists() else files[0], photo, face)
                    note = f"; {', '.join(tried)}" if tried else ""
                    print(f"{p['name']}: new portrait ({person.name}, {kind}, {photo.date:%b %-d, %Y}{note})")
                except RuntimeError as exc:
                    print(f"{p['name']}: upload failed ({exc})")
                break
        else:
            print(f"{p['name']}: couldn't export any photo ({'; '.join(tried)})")

    if missing:   # help set "Name in Apple Photos": the favorite people Photos has
        favs = sorted({x.name for x in db_people if getattr(x, "favorite", False)})
        print("Photos favorites: " + (", ".join(favs) if favs else "(none marked)"))


if __name__ == "__main__":
    main()

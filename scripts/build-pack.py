"""Make an art pack from the Python drawing code.

    python3 scripts/build-pack.py faith          one pack: dist/packs/faith/ and dist/packs/faith-<version>.zip (+ .sha256)
    python3 scripts/build-pack.py --all          every pack, the built-in folders in packs/, and packs/index.json

Built-in packs (holidays-us, seasons, family-basics) are also written to packs/<id>/, which the server reads.
Optional packs (faith, outings, kids-activities) are listed in packs/index.json with their sha256, and a
preview drawing goes to packs/previews/<id>.svg. Run --all after changing any drawing or table in app/.
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from app import pack_build as pb  # noqa: E402

DIST = ROOT / "dist" / "packs"


def one(pid: str) -> dict:
    z, sha = pb.build_zip(pid, DIST, DIST)
    (DIST / (z.name + ".sha256")).write_text(f"{sha}  {z.name}\n")
    folder = DIST / pid
    if pid in pb.BUILT_IN:
        dest = ROOT / "packs" / pid
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(folder, dest)
    print(f"{pid}: {folder.relative_to(ROOT)}  {z.relative_to(ROOT)}  {z.stat().st_size // 1024} KB  sha256 {sha[:16]}…")
    return pb.index_entry(pid, folder, sha, z.stat().st_size)


def main(args):
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 1
    ids = list(pb.BUILT_IN + pb.OPTIONAL) if args[0] == "--all" else args
    entries = [one(pid) for pid in ids]
    if args[0] == "--all":
        prev = ROOT / "packs" / "previews"
        prev.mkdir(parents=True, exist_ok=True)
        index = []
        for e in entries:
            if e["id"] in pb.OPTIONAL:
                m = json.loads((DIST / e["id"] / "pack.json").read_text())
                shutil.copyfile(DIST / e["id"] / m["preview"], prev / f"{e['id']}.svg")
                index.append(e)
        (ROOT / "packs" / "index.json").write_text(json.dumps({"packs": index}, indent=1, ensure_ascii=False) + "\n")
        print(f"wrote packs/index.json ({len(index)} downloadable packs)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

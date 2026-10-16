#!/usr/bin/env python3
"""Back up a PF1007L (Allwinner A33) frame over root ADB. Read-only on the frame.

Reads eMMC sectors 0 .. start of UDISK (every boot loader area and every
partition except user storage), plus the two eMMC hardware boot areas.
Each 64 MiB chunk is read twice and must hash the same both times; finished
chunks are kept, so a rerun after a USB drop picks up where it stopped.
Then it joins the chunks, checks the exact byte count, gzips the image and
verifies the gzip decompresses to the same SHA-256.

    python3 -I scripts/a33-backup.py <adb-serial>

Output: ./frame-backups/<serial>/ (or FRAME_BACKUP_DIR/<serial>/). It holds the
serial and any saved Wi-Fi details, so keep it private.

Set STOCK_BOOT_SHA to the SHA-256 of a known stock boot image to have the
backup say whether the boot partition still matches it.
"""

import gzip
import hashlib
import os
import pathlib
import subprocess
import sys

CHUNK = 131072  # sectors = 64 MiB
SECTOR = 512
EXPECTED_LAYOUT = {  # partition: start sector, from docs/pf1007l-start-here.md T6
    "mmcblk0p5": 139264,   # env
    "mmcblk0p6": 172032,   # boot
    "mmcblk0p7": 237568,   # system
    "mmcblk0p9": 2400256,  # recovery
}
STOCK_BOOT_SHA = os.environ.get("STOCK_BOOT_SHA", "").strip().lower()


def sh(serial, cmd):
    return subprocess.run(["adb", "-s", serial, "shell", cmd], capture_output=True,
                          text=True, timeout=60, check=True).stdout.strip()


def read(serial, dev, skip, count):
    cmd = f"dd if={dev} bs=512 skip={skip} count={count} 2>/dev/null"
    return subprocess.run(["adb", "-s", serial, "exec-out", cmd], capture_output=True,
                          timeout=600, check=True).stdout


LIMIT = (1 << 31) // SECTOR  # the frame's toybox dd can't lseek past 2 GiB


def read_range(serial, parts, start, count):
    """Read whole-disk sectors; past 2 GiB, read through the partition nodes."""
    if start + count <= LIMIT:
        return read(serial, "/dev/block/mmcblk0", start, count)
    out = b""
    pos, end = start, start + count
    while pos < end:
        name, pstart, psize = next((n, ps, sz) for n, ps, sz in parts if ps <= pos < ps + sz)
        if pos - pstart >= LIMIT:
            stop(f"{name}: offset past 2 GiB inside the partition")
        n = min(end, pstart + psize) - pos
        out += read(serial, f"/dev/block/{name}", pos - pstart, n)
        pos += n
    return out


def stop(msg):
    sys.exit(f"STOP: {msg}")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    serial = sys.argv[1]
    out = pathlib.Path(os.environ.get("FRAME_BACKUP_DIR", "frame-backups")).expanduser() / serial
    chunks = out / "chunks"
    chunks.mkdir(parents=True, exist_ok=True)

    if sh(serial, "id").split()[0] != "uid=0(root)":
        stop("adb shell is not root")
    for part, start in EXPECTED_LAYOUT.items():
        got = int(sh(serial, f"cat /sys/class/block/{part}/start"))
        if got != start:
            stop(f"{part} starts at {got}, expected {start}")
    end = int(sh(serial, "cat /sys/class/block/mmcblk0p1/start"))  # UDISK
    print(f"Layout matches. Backing up sectors 0..{end - 1} ({end * SECTOR:,} bytes).")

    parts = []
    for line in sh(serial, "for p in /sys/class/block/mmcblk0p*; do echo ${p##*/} $(cat $p/start) $(cat $p/size); done").splitlines():
        name, ps, sz = line.split()
        parts.append((name, int(ps), int(sz)))
    covered = sorted((ps, ps + sz) for _, ps, sz in parts if ps >= LIMIT or ps + sz > LIMIT)
    pos = LIMIT
    for a, b in covered:
        if a > pos and a < end:
            stop(f"sectors {pos}..{a} past 2 GiB are not in any partition")
        pos = max(pos, b)

    n = (end + CHUNK - 1) // CHUNK
    for i in range(n):
        f = chunks / f"emmc-{i:02d}.bin"
        count = min(CHUNK, end - i * CHUNK)
        if f.exists() and f.stat().st_size == count * SECTOR:
            continue
        a = read_range(serial, parts, i * CHUNK, count)
        b = read_range(serial, parts, i * CHUNK, count)
        if len(a) != count * SECTOR:
            stop(f"chunk {i:02d}: got {len(a)} bytes, expected {count * SECTOR}")
        if hashlib.sha256(a).digest() != hashlib.sha256(b).digest():
            stop(f"chunk {i:02d}: two reads differ")
        if a == b"\xcc" * len(a):
            stop(f"chunk {i:02d}: all 0xCC filler")
        f.write_bytes(a)
        print(f"  chunk {i + 1}/{n} ok", flush=True)

    for hw in ("mmcblk0boot0", "mmcblk0boot1"):
        size = int(sh(serial, f"cat /sys/class/block/{hw}/size"))
        a = read(serial, f"/dev/block/{hw}", 0, size)
        b = read(serial, f"/dev/block/{hw}", 0, size)
        if len(a) != size * SECTOR or a != b:
            stop(f"{hw}: short or unstable read")
        (out / f"{hw}.bin").write_bytes(a)
        print(f"  {hw} ok ({len(a):,} bytes)")

    img = out / f"emmc-0-{end}.img"
    h = hashlib.sha256()
    with img.open("wb") as w:
        for i in range(n):
            data = (chunks / f"emmc-{i:02d}.bin").read_bytes()
            h.update(data)
            w.write(data)
    if img.stat().st_size != end * SECTOR:
        stop(f"image is {img.stat().st_size} bytes, expected {end * SECTOR}")
    digest = h.hexdigest()

    with img.open("rb") as r:
        r.seek(172032 * SECTOR)
        boot = hashlib.sha256(r.read(31028 * SECTOR)).hexdigest()
    if STOCK_BOOT_SHA:
        print(f"  boot image sha256 {boot[:8]} ({'matches STOCK_BOOT_SHA' if boot == STOCK_BOOT_SHA else 'does NOT match STOCK_BOOT_SHA'})")
    else:
        print(f"  boot image sha256 {boot}")

    gz = img.with_suffix(".img.gz")
    with img.open("rb") as r, gzip.open(gz, "wb", compresslevel=6) as w:
        while block := r.read(1 << 24):
            w.write(block)
    g = hashlib.sha256()
    with gzip.open(gz, "rb") as r:
        while block := r.read(1 << 24):
            g.update(block)
    if g.hexdigest() != digest:
        stop("gzip readback does not match the image")
    (out / "SHA256SUMS").write_text(f"{digest}  {img.name}\n")
    img.unlink()
    for f in chunks.iterdir():
        f.unlink()
    chunks.rmdir()
    print(f"Backup verified: {gz} ({gz.stat().st_size:,} bytes compressed)")
    print(f"Image sha256 {digest} recorded in SHA256SUMS")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Watch USB and ADB while the picture frame is plugged in, and say what it is.

Read-only. It never writes to the frame: it lists USB devices (ioreg), runs
`adb devices`, and, once ADB is authorized, reads a few `getprop` values.
Some frames only show up for a few seconds during boot or reset, so this
polls twice a second and prints every change with a timestamp.

Run it, then power the frame on or plug it in:

    python3 -I scripts/frame-watch.py

A copy of the output goes to ./frame-diagnostics/ (or FRAME_DIAG_DIR). It can
hold the frame's serial number, so keep it out of anything you publish.
Ctrl-C to stop.
"""

import datetime
import os
import pathlib
import plistlib
import shutil
import subprocess
import sys
import time

# Vendor IDs we care about, with what each product ID means on the frames in
# Wes Bos's repo (docs/devices.md, docs/pf1007l-start-here.md).
VENDORS = {
    0x2207: "Rockchip",
    0x1F3A: "Allwinner",
    0x18D1: "Google/Android",
}
KNOWN = {
    (0x2207, 0x0006): "Android with ADB (BIUFRAME / Synergy 10X1 shows this)",
    (0x2207, 0x0007): "Android, file transfer (MTP)",
    (0x2207, 0x350A): "Rockchip loader / MaskROM mode",
    (0x1F3A, 0x1000): "Android, no ADB (PF1007L stock: USB data works, ADB off)",
    (0x1F3A, 0x1001): "Android with ADB (PF1007L)",
    (0x1F3A, 0x1002): "Android with ADB (PF1007L; stock on some units, or after Route U)",
    (0x1F3A, 0xEFE8): "Allwinner FEL mode (SD stub card)",
}

LOG_DIR = pathlib.Path(os.environ.get("FRAME_DIAG_DIR", "frame-diagnostics")).expanduser()
PROPS = [
    "ro.product.model",
    "ro.product.manufacturer",
    "ro.board.platform",
    "ro.hardware",
    "ro.build.display.id",
    "ro.build.fingerprint",
    "ro.build.version.release",
]

log_file = None


def say(msg):
    line = f"[{datetime.datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    if log_file:
        log_file.write(line + "\n")
        log_file.flush()


def usb_devices():
    """Return {(vid, pid, name, location)} for every USB device. No serials."""
    raw = subprocess.check_output(["ioreg", "-a", "-l", "-p", "IOUSB"], timeout=10)
    found = set()

    def walk(node):
        if not isinstance(node, dict):
            return
        vid, pid = node.get("idVendor"), node.get("idProduct")
        if isinstance(vid, int) and isinstance(pid, int):
            name = node.get("USB Product Name") or node.get("IORegistryEntryName", "")
            found.add((vid, pid, name, node.get("locationID", 0)))
        for child in node.get("IORegistryEntryChildren", []):
            walk(child)

    root = plistlib.loads(raw)
    for r in root if isinstance(root, list) else [root]:
        walk(r)
    return found


def describe(dev):
    vid, pid, name, _ = dev
    label = KNOWN.get((vid, pid)) or VENDORS.get(vid, "")
    flag = ">>> " if vid in (0x2207, 0x1F3A) else ""
    return f"{flag}{vid:04x}:{pid:04x} {name!r}" + (f"  ({label})" if label else "")


def adb_devices():
    """Return {serial: state} from `adb devices`."""
    try:
        out = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10).stdout
    except subprocess.TimeoutExpired:
        return {}
    result = {}
    for line in out.splitlines()[1:]:
        parts = line.split()
        # adb probes localhost ports 5555-5585 for emulators; another app on
        # this Mac answers there and shows up as a flapping emulator-NNNN.
        if len(parts) >= 2 and not parts[0].startswith("emulator-"):
            result[parts[0]] = parts[1]
    return result


def identify(serial):
    def prop(p):
        r = subprocess.run(["adb", "-s", serial, "shell", "getprop", p],
                           capture_output=True, text=True, timeout=15)
        return r.stdout.strip()

    values = {p: prop(p) for p in PROPS}
    for p, v in values.items():
        say(f"    {p} = {v}")
    uid = subprocess.run(["adb", "-s", serial, "shell", "id"],
                         capture_output=True, text=True, timeout=15).stdout.strip()
    say(f"    adb shell id = {uid}")

    blob = " ".join(values.values()).lower()
    if "synergy 10x1" in blob or "rk312x" in blob:
        say("  VERDICT: Rockchip BIUFRAME (the frame in the video).")
        say("  Next: in your clone of wesbos/photo-frame-dashboard, run scripts/biuframe-setup.sh check  (read-only)")
    elif "pf1007l" in blob or "a33" in blob or "astar" in blob or "aimor" in blob:
        say("  VERDICT: Allwinner A33 / PF1007L, NOT the video's board.")
        say("  Next: docs/pf1007l-start-here.md in Wes Bos's repo, T6 onward. Keep the frame OFF Wi-Fi until T8.")
    else:
        say("  VERDICT: unknown board. Stop here and work through the README phase map.")


def main():
    global log_file
    if not shutil.which("adb"):
        sys.exit("adb not found. Run: brew install android-platform-tools")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"frame-watch-{datetime.datetime.now():%Y%m%d-%H%M%S}.log"
    log_file = path.open("w")

    subprocess.run(["adb", "start-server"], capture_output=True)
    baseline = usb_devices()
    adb_seen = adb_devices()
    say(f"Watching USB and ADB. Log: {path}")
    say(f"{len(baseline)} USB devices already connected (ignored). Plug in or power on the frame now.")
    for d in sorted(baseline):
        if d[0] in VENDORS:
            say("  already connected: " + describe(d))
    identified = set()
    for s, st in adb_seen.items():
        say(f"  ADB already sees {s}: {st}")
        if st == "device":
            identified.add(s)
            identify(s)

    current = baseline
    try:
        while True:
            now = usb_devices()
            for d in sorted(now - current):
                say("USB plugged in:  " + describe(d))
            for d in sorted(current - now):
                say("USB went away:   " + describe(d))
            current = now

            adb_now = adb_devices()
            for s, st in adb_now.items():
                if adb_seen.get(s) != st:
                    say(f"ADB {s}: {st}")
                    if st == "unauthorized":
                        say("  Tap ALLOW on the frame's 'Allow USB debugging?' prompt "
                            "and tick 'Always allow from this computer'.")
                    if st == "device" and s not in identified:
                        identified.add(s)
                        identify(s)
            for s in set(adb_seen) - set(adb_now):
                say(f"ADB {s}: gone")
            adb_seen = adb_now
            time.sleep(0.5)
    except KeyboardInterrupt:
        say("Stopped.")


if __name__ == "__main__":
    main()

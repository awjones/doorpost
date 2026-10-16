"""Build the add-on and copy it to Home Assistant's local_apps share, no Finder mount needed.

    .venv/bin/pip install smbprotocol        # one time
    HA_HOST=homeassistant.local .venv/bin/python scripts/push-addon-smb.py

Needs Home Assistant's Samba share add-on. Settings come from the environment:
  HA_HOST           the Home Assistant host (default homeassistant.local)
  HA_SMB_USER       the Samba user (default homeassistant)
  HA_SMB_PASSWORD   the Samba password; if unset, on a Mac it is read from the
                    login Keychain item "Home Assistant Samba (<HA_HOST>)"
Afterwards, Home Assistant shows an Update for Doorpost (Settings > Apps,
or refresh the store from its menu).
"""
import os
import subprocess
import sys

import smbclient

SERVER = os.environ.get("HA_HOST", "homeassistant.local")
USER = os.environ.get("HA_SMB_USER", "homeassistant")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

subprocess.run(["bash", os.path.join(ROOT, "scripts", "build-addon.sh")], check=True)
password = os.environ.get("HA_SMB_PASSWORD")
if not password:
    pw = subprocess.run(["security", "find-generic-password", "-a", USER, "-s",
                         f"Home Assistant Samba ({SERVER})", "-w"], capture_output=True, text=True)
    if pw.returncode:
        sys.exit("Set HA_SMB_PASSWORD (or save the Samba login in the Mac's Keychain).")
    password = pw.stdout.strip()
smbclient.register_session(SERVER, username=USER, password=password)

src = os.path.join(ROOT, "dist", "family_frame")
dst = rf"\\{SERVER}\local_apps\family_frame"
if smbclient.path.isdir(dst):  # replace our own folder's contents only
    for root, dirs, files in list(smbclient.walk(dst, topdown=False)):
        for f in files:
            smbclient.remove(rf"{root}\{f}")
        for d in dirs:
            smbclient.rmdir(rf"{root}\{d}")
smbclient.makedirs(dst, exist_ok=True)
count = 0
for root, dirs, files in os.walk(src):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    rel = os.path.relpath(root, src)
    target = dst if rel == "." else dst + "\\" + rel.replace("/", "\\")
    smbclient.makedirs(target, exist_ok=True)
    for f in files:
        with open(os.path.join(root, f), "rb") as fh, smbclient.open_file(rf"{target}\{f}", mode="wb") as out:
            out.write(fh.read())
        count += 1
print(f"Copied {count} files to {dst}. In Home Assistant, Doorpost now shows an Update.")

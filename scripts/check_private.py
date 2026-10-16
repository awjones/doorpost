#!/usr/bin/env python3
"""Look for private words (local/denylist.txt) anywhere they must not be. scripts/check-private.sh runs this.

    scripts/check-private.sh                       the working copy: every file outside local/
    scripts/check-private.sh --commits A..B        those commits: their messages, the lines they add, their paths
    scripts/check-private.sh --pre-push NAME URL   what git is about to push (the .githooks/pre-push hook)

The denylist is one exact string per line, matched without regard to case. Lines starting with # are notes.
FRAME_LOCAL_DIR moves local/; --denylist FILE uses another list.

Some hits can be on purpose (your name in LICENSE, say). local/denylist-allow.txt lists them, one per line as
`path: text` (that file may contain that text). Everything else is a hit.

Exit codes: 0 nothing found, 1 something found (each hit is listed), 2 the check could not run.
Pushes to a public remote are refused when there is no denylist, unless FRAME_PRIVACY_SKIP=1.
A remote counts as public when its name is "public" or "upstream", its address contains "doorpost", or it is
listed with `git config --add privacy.publicRemote <name or address part>`.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ZERO = "0" * 40
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "dist"}


def git(*args: str, cwd: Path, data: bool = False):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.decode(errors='replace').strip()}")
    return r.stdout if data else r.stdout.decode(errors="replace")


def repo_root() -> Path:
    here = Path(__file__).resolve().parent.parent
    try:
        return Path(git("rev-parse", "--show-toplevel", cwd=here).strip())
    except (RuntimeError, FileNotFoundError):
        return here


def local_dir(root: Path) -> Path:
    return Path(os.environ.get("FRAME_LOCAL_DIR") or root / "local").expanduser().resolve()


def read_list(path: Path) -> list[str]:
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def read_allow(path: Path) -> list[tuple[str, str]]:
    if not path.exists():
        return []
    out = []
    for line in read_list(path):
        if ":" in line:
            p, t = line.split(":", 1)
            out.append((p.strip(), t.strip().lower()))
    return out


class Checker:
    def __init__(self, terms: list[str], allow: list[tuple[str, str]]):
        self.terms = [(t, t.lower().encode()) for t in terms]
        self.allow = allow
        self.hits: list[str] = []

    def allowed(self, where: str, term: str) -> bool:
        return any(where == p and term.lower() == t for p, t in self.allow)

    def scan(self, where: str, blob: bytes, line_offset: int = 0, path: str = "") -> None:
        """path: the file this is from, for denylist-allow.txt (defaults to where)."""
        low = blob.lower()
        for term, needle in self.terms:
            if needle in low and not self.allowed(path or where, term):
                n = low[:low.index(needle)].count(b"\n") + 1 + line_offset
                self.hits.append(f"{where}:{n}: {term}")

    def scan_name(self, where: str, name: str) -> None:
        self.scan(f"{where} (file name)", name.encode())


def is_local_path(path: str, root: Path) -> bool:
    return path == "local" or path.startswith("local/")


def tree_files(root: Path, skip: Path) -> list[Path]:
    """Every file in the working copy except local/ (tracked and untracked; git-ignored ones too when they
    are not in a skipped folder, since an ignored file can still be added by hand)."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        dirnames[:] = [n for n in dirnames if n not in SKIP_DIRS and (d / n).resolve() != skip]
        for f in filenames:
            if f != ".git":   # a worktree's .git is a file that points at the main repo
                out.append(d / f)
    return out


def check_tree(ch: Checker, root: Path, skip: Path) -> int:
    files = tree_files(root, skip)
    for p in files:
        rel = p.relative_to(root).as_posix()
        if rel.startswith("local/"):
            continue
        ch.scan_name(rel, rel)
        try:
            ch.scan(rel, p.read_bytes())
        except OSError:
            continue
    return len(files)


def blobs(root: Path, revs: list[str]):
    """(path, content) of every file version these commits bring (each object once), binary files too."""
    listing = git("rev-list", "--objects", *revs, cwd=root)
    pairs = [ln.split(" ", 1) for ln in listing.splitlines() if " " in ln]
    if not pairs:
        return
    r = subprocess.run(["git", "cat-file", "--batch"], cwd=root, input="\n".join(s for s, _ in pairs).encode() + b"\n",
                       capture_output=True)
    out, i = r.stdout, 0
    for sha, path in pairs:
        nl = out.index(b"\n", i)
        head = out[i:nl].split()
        if len(head) < 3:
            i = nl + 1
            continue
        size = int(head[2])
        body = out[nl + 1:nl + 1 + size]
        i = nl + 1 + size + 1
        if head[1] == b"blob":
            yield path, body


def check_commits(ch: Checker, root: Path, revs: list[str], problems: list[str]) -> int:
    """These commits: their messages, every file version they bring, and the paths they touch (none under local/)."""
    commits = [c for c in git("rev-list", *revs, cwd=root).split() if c]
    for c in commits:
        short = c[:10]
        ch.scan(f"commit {short} message", git("log", "-1", "--format=%B", c, cwd=root, data=True))
        names = git("diff-tree", "--root", "--no-commit-id", "-r", "--name-only", "-z", c, cwd=root, data=True)
        for name in [n.decode(errors="replace") for n in names.split(b"\0") if n]:
            if is_local_path(name, root):
                problems.append(f"commit {short} touches {name} (nothing under local/ may go public)")
            ch.scan_name(f"commit {short} {name}", name)
    if commits:
        for path, body in blobs(root, revs):
            if not is_local_path(path, root):
                ch.scan(f"{path} (in these commits)", body, path=path)
    return len(commits)


def is_public(name: str, url: str, root: Path) -> bool:
    try:
        extra = [x.strip() for x in git("config", "--get-all", "privacy.publicRemote", cwd=root).split("\n") if x.strip()]
    except RuntimeError:
        extra = []
    if name in ("public", "upstream") or "doorpost" in url.lower():
        return True
    return any(x == name or (x and x in url) for x in extra)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Look for private words outside local/.")
    ap.add_argument("--denylist")
    ap.add_argument("--allow")
    ap.add_argument("--commits", metavar="RANGE")
    ap.add_argument("--pre-push", nargs=2, metavar=("REMOTE", "URL"))
    a = ap.parse_args(argv)
    root = repo_root()
    loc = local_dir(root)
    deny = Path(a.denylist).expanduser() if a.denylist else loc / "denylist.txt"
    allow = Path(a.allow).expanduser() if a.allow else deny.with_name("denylist-allow.txt")

    if a.pre_push:
        name, url = a.pre_push
        if not is_public(name, url, root):
            return 0   # a private remote: anything may go there
        if os.environ.get("FRAME_PRIVACY_SKIP") == "1":
            print("check-private: skipped (FRAME_PRIVACY_SKIP=1).", file=sys.stderr)
            return 0
    if not deny.is_file():
        print(f"check-private: no denylist at {deny}. Copy local.example/denylist.txt there and fill it in "
              "(or set FRAME_PRIVACY_SKIP=1 for a push you have checked yourself).", file=sys.stderr)
        return 2
    terms = read_list(deny)
    short = [t for t in terms if len(t) < 3]
    if short:
        print(f"check-private: ignoring {len(short)} denylist line(s) under 3 characters.", file=sys.stderr)
        terms = [t for t in terms if len(t) >= 3]
    ch = Checker(terms, read_allow(allow))
    problems: list[str] = []

    if a.pre_push:
        n = 0
        for line in sys.stdin.read().splitlines():
            parts = line.split()
            if len(parts) != 4:
                continue
            _lref, lsha, _rref, rsha = parts
            if lsha == ZERO:
                continue   # deleting a branch sends nothing
            revs = [lsha, f"^{rsha}"] if rsha != ZERO else [lsha, "--not", f"--remotes={name}"]
            n += check_commits(ch, root, revs, problems)
            tree = git("ls-tree", "-r", "--name-only", "-z", lsha, cwd=root, data=True)
            for p in [x.decode(errors="replace") for x in tree.split(b"\0") if x]:
                if is_local_path(p, root):
                    problems.append(f"{p} is in the pushed files (nothing under local/ may go public)")
                    continue
                blob = git("show", f"{lsha}:{p}", cwd=root, data=True)
                ch.scan(p, blob)
        what = f"{n} outgoing commit(s) to {name}"
    elif a.commits:
        what = f"{check_commits(ch, root, [a.commits], problems)} commit(s)"
    else:
        what = f"{check_tree(ch, root, loc)} files outside local/"

    for p in problems:
        print(f"REFUSED: {p}")
    for h in ch.hits:
        print(f"PRIVATE: {h}")
    if problems or ch.hits:
        print(f"check-private: {len(ch.hits)} private word(s) and {len(problems)} local/ path(s) in {what}. Nothing was pushed."
              if a.pre_push else f"check-private: {len(ch.hits)} hit(s) and {len(problems)} local/ path(s) in {what}.")
        return 1
    print(f"check-private: clean ({len(terms)} words checked in {what}).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

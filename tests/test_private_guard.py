"""The private overlay's guards: scripts/check-private.sh, the pre-push hook, .gitignore and the add-on build."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WORD = "Zebraquux"          # a made-up private word
ZERO = "0" * 40


def run(args, cwd, stdin=None, env=None):
    e = dict(os.environ)
    e.pop("FRAME_LOCAL_DIR", None)   # these repos have their own local/
    e.update(env or {})
    return subprocess.run(args, cwd=cwd, input=stdin, capture_output=True, text=True, env=e)


def git(cwd, *a):
    r = run(["git", "-c", "user.name=T", "-c", "user.email=t@example.com", *a], cwd)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A small git repo with the guard scripts, a local/ with a denylist, and one clean commit."""
    r = tmp_path / "repo"
    (r / "scripts").mkdir(parents=True)
    for f in ("check-private.sh", "check_private.py"):
        shutil.copy2(ROOT / "scripts" / f, r / "scripts" / f)
    shutil.copytree(ROOT / ".githooks", r / ".githooks")
    shutil.copy2(ROOT / ".gitignore", r / ".gitignore")
    (r / "app.txt").write_text("nothing private here\n")
    (r / "LICENSE").write_text(f"Copyright Pat {WORD}\n")
    (r / "local").mkdir()
    (r / "local" / "denylist.txt").write_text(f"# notes are fine\n{WORD}\n192.0.2.77\nab\n")
    (r / "local" / "denylist-allow.txt").write_text(f"LICENSE: {WORD}\n")
    (r / "local" / "secret.yaml").write_text(f"domain: {WORD}.example\n")
    git(r, "init", "-q", "-b", "main")
    git(r, "add", ".")
    git(r, "commit", "-qm", "start")
    return r


def check(repo, *args, stdin=None, env=None):
    return run([sys.executable, "scripts/check_private.py", *args], repo, stdin=stdin, env=env)


def test_gitignore_keeps_local_out(repo):
    assert "local/" not in git(repo, "ls-files")
    assert (ROOT / "local.example" / "denylist.txt").is_file()


def test_clean_tree_passes_and_allowlist_counts(repo):
    r = check(repo)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "clean" in r.stdout and "under 3 characters" in r.stderr


def test_hit_outside_local_fails(repo):
    (repo / "docs.md").write_text(f"call us at 192.0.2.77, love the {WORD.lower()}s\n")
    (repo / f"photo-{WORD}.jpg").write_bytes(b"\x00\x01")
    r = check(repo)
    assert r.returncode == 1
    assert "docs.md:1: 192.0.2.77" in r.stdout and f"docs.md:1: {WORD}" in r.stdout
    assert "(file name)" in r.stdout
    assert "secret.yaml" not in r.stdout     # local/ itself is never checked


def test_commits_catch_a_word_that_was_removed_later(repo):
    (repo / "app.txt").write_text(f"oops {WORD}\n")
    git(repo, "commit", "-qam", "oops")
    (repo / "app.txt").write_text("fixed\n")
    git(repo, "commit", "-qam", "fixed")
    assert check(repo).returncode == 0                       # the files are clean now...
    r = check(repo, "--commits", "HEAD~2..HEAD")
    assert r.returncode == 1 and "app.txt (in these commits)" in r.stdout   # ...but history still has it


def _push(repo, remote, url, env=None, base=ZERO):
    head = git(repo, "rev-parse", "HEAD")
    return check(repo, "--pre-push", remote, url, stdin=f"refs/heads/main {head} refs/heads/main {base}\n", env=env)


def test_pre_push_refuses_local_paths_and_words(repo):
    git(repo, "add", "-f", "local/secret.yaml")
    git(repo, "commit", "-qm", f"add {WORD} settings")
    r = _push(repo, "public", "https://github.com/someone/doorpost.git")
    assert r.returncode == 1
    assert "REFUSED: local/secret.yaml" in r.stdout and "message" in r.stdout and "Nothing was pushed" in r.stdout
    assert _push(repo, "origin", "https://github.com/someone/private-copy.git").returncode == 0   # private: fine


def test_pre_push_public_by_config_and_no_denylist(repo):
    git(repo, "config", "--add", "privacy.publicRemote", "example.org/pub")
    (repo / "local" / "denylist.txt").unlink()
    r = _push(repo, "mirror", "https://example.org/pub/x.git")
    assert r.returncode == 2 and "no denylist" in r.stderr
    assert _push(repo, "mirror", "https://example.org/pub/x.git", env={"FRAME_PRIVACY_SKIP": "1"}).returncode == 0


def test_hook_runs_the_check(repo, tmp_path):
    """A real push to a bare 'public' remote through .githooks/pre-push."""
    bare = tmp_path / "doorpost-public.git"
    git(tmp_path, "init", "-q", "--bare", str(bare))
    git(repo, "config", "core.hooksPath", ".githooks")
    git(repo, "remote", "add", "public", str(bare))
    (repo / "app.txt").write_text(f"{WORD}\n")
    git(repo, "commit", "-qam", "leak")
    r = run(["git", "push", "-q", "public", "main"], repo)
    assert r.returncode != 0 and "PRIVATE" in r.stdout + r.stderr
    git(repo, "reset", "-q", "--hard", "HEAD~1")
    r = run(["git", "push", "-q", "public", "main"], repo)
    assert r.returncode == 0, r.stdout + r.stderr


def test_addon_build_takes_the_overlay(tmp_path):
    if not shutil.which("rsync"):
        pytest.skip("needs rsync")
    loc = tmp_path / "local"
    (loc / "packs" / "mine").mkdir(parents=True)
    (loc / "packs" / "mine" / "pack.json").write_text(json.dumps({"id": "mine", "name": "Mine"}))
    (loc / "web" / "img").mkdir(parents=True)
    (loc / "web" / "img" / "monogram.png").write_bytes(b"png")
    (loc / "addon").mkdir()
    (loc / "addon" / "addon.conf").write_text("ADDON_NAME=Our Frame & Co\nADDON_VERSION_PREFIX=2.0\n")
    (loc / "addon" / "icon.png").write_bytes(b"icon")
    (loc / "scripts").mkdir()
    (loc / "scripts" / "push.sh").write_text("secret")
    (loc / "denylist.txt").write_text("secret")
    (loc / ".env").write_text("CAL=secret")
    out = tmp_path / "out"
    r = run(["bash", "scripts/build-addon.sh"], ROOT, env={"FRAME_LOCAL_DIR": str(loc), "ADDON_OUT": str(out)})
    assert r.returncode == 0, r.stderr
    cfg = (out / "config.yaml").read_text()
    assert "name: Our Frame & Co" in cfg and "panel_title: Our Frame & Co" in cfg and "slug: family_frame" in cfg
    assert 'version: "2.0.' in cfg
    assert (out / "local" / "packs" / "mine" / "pack.json").is_file()
    assert (out / "local" / "web" / "img" / "monogram.png").read_bytes() == b"png"
    assert (out / "icon.png").read_bytes() == b"icon"
    assert not (out / "local" / "scripts").exists() and not (out / "local" / "denylist.txt").exists()
    assert not (out / "local" / ".env").exists() and not (out / "local" / "addon").exists()
    assert "COPY local ./local" in (out / "Dockerfile").read_text()


def test_addon_build_without_overlay(tmp_path):
    if not shutil.which("rsync"):
        pytest.skip("needs rsync")
    out = tmp_path / "out"
    r = run(["bash", "scripts/build-addon.sh"], ROOT, env={"FRAME_LOCAL_DIR": str(tmp_path / "none"), "ADDON_OUT": str(out)})
    assert r.returncode == 0, r.stderr
    cfg = (out / "config.yaml").read_text()
    assert "name: Doorpost" in cfg and 'version: "1.1.' in cfg
    assert [p.name for p in (out / "local").iterdir()] == [".keep"]

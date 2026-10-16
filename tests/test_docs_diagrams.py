"""The diagrams in docs/img are built by scripts/docs/gen_diagrams.py, and the docs link to them."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "docs" / "img"


def test_generator_rebuilds_the_committed_diagrams(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "scripts" / "docs" / "gen_diagrams.py"), str(tmp_path)],
                   check=True, capture_output=True)
    made = sorted(p.name for p in tmp_path.glob("*.svg"))
    assert made == sorted(p.name for p in IMG.glob("*.svg"))
    for name in made:
        assert (tmp_path / name).read_text() == (IMG / name).read_text(), f"{name} is stale: rerun the generator"


def test_diagrams_have_dark_mode_and_no_emoji():
    for svg in IMG.glob("*.svg"):
        text = svg.read_text()
        assert "prefers-color-scheme: dark" in text, svg.name
        assert "<title" in text and "<desc" in text, svg.name
        assert not re.search("[\U0001F300-\U0001FAFF☀-➿]", text), svg.name


def test_doc_links_and_images_resolve():
    docs = [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]
    for doc in docs:
        for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", doc.read_text()):
            if "://" in target:
                continue
            assert (doc.parent / target).exists(), f"{doc.name} links to missing {target}"


def test_new_guides_have_no_em_dashes():
    for name in ("setup-guide.md", "hardware.md", "screens.md"):
        assert "—" not in (ROOT / "docs" / name).read_text(), name

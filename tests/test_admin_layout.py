"""Settings layout: every page is one card; its sections are folding blocks inside it (web/js/admin.js blocks())."""
import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"


def test_page_plugins_draw_blocks_not_cards():
    # The Settings look, Bible translation and Email updates pieces sit inside a page's card.
    for name in ("admin-look.js", "bible-admin.js"):
        assert '<section class="card"' not in (WEB / "js" / name).read_text(), name
    email = (WEB / "js" / "email-admin.js").read_text()
    assert email.count('<section class="card"') == 3   # the page's one card, in its loading, error and normal states
    assert "AdminBlocks.blocks(" in email


def test_pages_once_split_into_cards_are_one_card_now():
    js = (WEB / "js" / "admin.js").read_text()
    for gone in ("card('pk-more'", "card('pk-up'", "card('storage'", "card('display'", "storageCard()"):
        assert gone not in js, gone
    build = re.search(r"var BUILD = \{(.*?)\};", js, re.S).group(1)
    assert "overview: overview," in build and "'special-days': special," in build
    for page in ("function overview()", "function artPacks()", "function screenTime()", "function lists()", "function photos()"):
        body = js.split(page, 1)[1].split("\n  function ", 1)[0]
        assert "blocks([" in body, page


def test_block_styles_are_there():
    html = (WEB / "admin.html").read_text()
    assert ".blks {" in html and ".disk-tile" in html

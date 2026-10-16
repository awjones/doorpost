"""Shared-album readers against saved page/JSON shapes (no network)."""
import json

import httpx
import pytest

from app import photo_sources as ps


def test_google_album_page_parsing():
    html = ('...["AF1QipAAA111",["https://lh3.googleusercontent.com/pw/ABCdef_1=w600",4032,3024,null]...'
            '["AF1QipBBB222",["https://lh3.googleusercontent.com/pw/XYZghi_2",3024,4032,null]...'
            '["AF1QipCCC333",["https://lh3.googleusercontent.com/a/avatar",96,96,null]')  # tiny = profile pic, skipped
    items = ps.parse_google_album(html)
    assert [i["key"] for i in items] == ["g-AF1QipAAA111", "g-AF1QipBBB222"]
    assert items[0]["url"] == "https://lh3.googleusercontent.com/pw/ABCdef_1=w1920-h1200"


def test_google_rejects_other_links():
    with pytest.raises(ps.SourceError):
        ps.google_album("https://example.com/album")


def test_icloud_token_and_host():
    tok = ps.icloud_token("https://www.icloud.com/sharedalbum/#B0aExampleTok1")
    assert tok == "B0aExampleTok1"
    assert ps.icloud_host(tok) == "p36-sharedstreams.icloud.com"   # "0a" in base 62 = 0*62 + 36
    assert ps.icloud_host("A5abcdefghij").startswith("p05-")
    # newer, longer links include - and _
    long = "D2abcdef-BIabcdefghijklmnopqrstuvwxyz012-OoABCDE_V8abcd_IHabcde_2dabcdefghij_yi8"
    assert ps.icloud_token("https://www.icloud.com/sharedalbum/#" + long) == long


def test_icloud_album_flow_with_redirect():
    calls = []

    def handler(req: httpx.Request):
        calls.append(str(req.url))
        if req.url.host.startswith("p36") and req.url.path.endswith("webstream"):
            return httpx.Response(330, json={"X-Apple-MMe-Host": "p99-sharedstreams.icloud.com"})
        if req.url.path.endswith("webstream"):
            return httpx.Response(200, json={"photos": [
                {"photoGuid": "G1", "derivatives": {"1": {"checksum": "small", "width": "300"},
                                                    "2": {"checksum": "big", "width": "2048"}}},
                {"photoGuid": "V1", "mediaAssetType": "video", "derivatives": {"1": {"checksum": "v", "width": "1"}}}]})
        if req.url.path.endswith("webasseturls"):
            assert json.loads(req.content) == {"photoGuids": ["G1"]}
            return httpx.Response(200, json={"items": {"big": {"url_location": "cvws.icloud-content.com", "url_path": "/B/abc"}}})
        return httpx.Response(404)

    items = ps.icloud_album("https://www.icloud.com/sharedalbum/#B0aExampleTok1",
                            http=httpx.Client(transport=httpx.MockTransport(handler)))
    assert items == [{"key": "i-G1", "url": "https://cvws.icloud-content.com/B/abc"}]
    assert any("p99-" in c for c in calls)

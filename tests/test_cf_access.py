"""Cloudflare Access sign-ins: real signatures accepted, anything else refused."""
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

TEAM = "yourteam.cloudflareaccess.com"
AUD = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def token(key=KEY, aud=AUD, iss=f"https://{TEAM}", email="mom@example.com", exp=3600):
    return jwt.encode({"aud": [aud], "iss": iss, "email": email, "exp": int(time.time()) + exp,
                       "iat": int(time.time())}, key, algorithm="RS256", headers={"kid": "k1"})


class FakeJWKS:
    def get_signing_key_from_jwt(self, _tok):
        class K:
            key = KEY.public_key()
        return K()


@pytest.fixture
def addon_client(demo_env, monkeypatch):
    import json
    data = demo_env / "data"
    data.mkdir(parents=True, exist_ok=True)   # Access is off by default: turn it on for these tests
    (data / "settings.demo.json").write_text(json.dumps({"cloudflare_access": {"team_domain": TEAM, "aud": AUD}}))
    monkeypatch.setenv("FRAME_ADDON", "1")
    monkeypatch.setenv("FRAME_NOW", "2026-10-15T16:12:00")
    import importlib
    import sys
    sys.modules.pop("app.admin", None)
    import app.cf_access
    monkeypatch.setattr(app.cf_access.jwt, "PyJWKClient", lambda *a, **k: FakeJWKS())
    import app.main
    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        yield c


def test_verifier_checks_signature_audience_issuer_expiry(monkeypatch):
    from app import cf_access
    monkeypatch.setattr(cf_access.jwt, "PyJWKClient", lambda *a, **k: FakeJWKS())
    v = cf_access.AccessVerifier(TEAM, AUD)
    assert v.email(token()) == "mom@example.com"
    assert v.email(token(key=OTHER)) is None                     # forged signature
    assert v.email(token(aud="someone-elses-app")) is None       # another Access app
    assert v.email(token(iss="https://evil.cloudflareaccess.com")) is None
    assert v.email(token(exp=-10)) is None                       # expired
    assert v.email("not-a-jwt") is None and v.email(None) is None


def test_signed_in_parent_needs_no_pin_and_can_open_settings(addon_client):
    h = {"Cf-Access-Jwt-Assertion": token()}
    assert addon_client.get("/api/parent/summary").status_code == 401          # home network, no PIN
    assert addon_client.get("/api/parent/summary", headers=h).status_code == 200
    me = addon_client.get("/api/parent/me", headers=h).json()
    assert me == {"access": True, "name": "Mom", "can_admin": True}
    assert addon_client.get("/api/admin/settings", headers=h).status_code == 200
    r = addon_client.post("/api/parent/chores/child2-set-the-table/approve", headers=h)
    assert r.status_code == 200


def test_forged_header_from_home_network_is_refused(addon_client):
    bad = {"Cf-Access-Jwt-Assertion": token(key=OTHER)}
    assert addon_client.get("/api/admin/settings", headers=bad).status_code == 403
    assert addon_client.get("/api/parent/summary", headers=bad).status_code == 401
    assert addon_client.get("/api/parent/me", headers=bad).json()["can_admin"] is False

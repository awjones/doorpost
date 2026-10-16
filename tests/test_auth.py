import pytest

from app.auth import PinGuard, check_pin_hash, hash_pin, session_name, sign_session, verify_session


def test_pin_hash_roundtrip():
    h = hash_pin("4821", iterations=1000)
    assert check_pin_hash("4821", h)
    assert not check_pin_hash("4822", h)


def test_pin_rules():
    with pytest.raises(ValueError):
        hash_pin("12")
    with pytest.raises(ValueError):
        hash_pin("abcd")


def test_lockout_after_five_misses():
    t = [0.0]
    g = PinGuard(hash_pin("1234", iterations=1000), clock=lambda: t[0])
    for _ in range(4):
        assert g.check("0000")[0] is False
    ok, msg = g.check("0000")
    assert not ok and "locked" in msg
    assert g.check("1234")[0] is False      # still locked, even with the right PIN
    t[0] += 301
    assert g.check("1234")[0] is True


def test_no_pin_configured():
    ok, msg = PinGuard(None).check("1234")
    assert not ok and "No parent PIN" in msg


def test_session_tokens():
    tok = sign_session("s3cret", now=1000, ttl_seconds=60)
    assert verify_session("s3cret", tok, now=1030)
    assert not verify_session("s3cret", tok, now=1061)       # expired
    assert not verify_session("other", tok, now=1030)        # wrong secret
    assert not verify_session("s3cret", tok + "x", now=1030)  # tampered
    assert not verify_session("s3cret", None)


def test_session_carries_the_parents_name():
    tok = sign_session("s3cret", now=1000, ttl_seconds=60, name="Mom")
    assert session_name("s3cret", tok, now=1030) == "Mom"
    assert session_name("s3cret", sign_session("s3cret", now=1000, ttl_seconds=60), now=1030) == ""
    assert session_name("s3cret", tok.replace(tok.split(".")[2], "QW5kcmV3"), now=1030) is None  # can't swap the name


def test_a_pin_each():
    g = PinGuard([("Dad", hash_pin("1234")), ("Mom", hash_pin("5678")), ("", hash_pin("9999"))])
    assert g.check_who("5678") == (True, "ok", "Mom")
    assert g.check_who("9999")[2] == ""
    assert g.check_who("0000")[0] is False

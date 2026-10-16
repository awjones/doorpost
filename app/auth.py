"""Parent PIN checks and the phone page's session cookie.

PINs are stored only as PBKDF2 hashes: one each for Dad and Mom (so the
screen time log says who did what), plus an optional shared PIN that logs as
"Parent". Five wrong tries lock PIN entry for five minutes, so a kid can't
guess it by mashing keys. Sessions carry the parent's name.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from threading import Lock

ITERATIONS = 200_000
MAX_TRIES = 5
LOCKOUT_SECONDS = 300
SESSION_DAYS = 30


def hash_pin(pin: str, salt: bytes | None = None, iterations: int = ITERATIONS) -> str:
    if not pin.isdigit() or not 4 <= len(pin) <= 8:
        raise ValueError("PIN must be 4 to 8 digits")
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, iterations)
    return f"pbkdf2${iterations}${salt.hex()}${digest.hex()}"


def check_pin_hash(pin: str, stored: str) -> bool:
    try:
        scheme, iters, salt_hex, digest_hex = stored.split("$")
        if scheme != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


SHARED = ""  # name used for the shared PIN


class PinGuard:
    def __init__(self, pins, clock=time.monotonic):
        """`pins`: a list of (name, hash), or a single hash for the shared PIN (or None)."""
        if pins is None or isinstance(pins, str):
            pins = [(SHARED, pins)] if pins else []
        self.pins = [(n, h) for n, h in pins if h]
        self.clock = clock
        self.failures = 0
        self.locked_until = 0.0
        self._lock = Lock()

    @property
    def stored_hash(self):
        """Identity of the PIN set (to keep the lockout state across a settings reload)."""
        return tuple(self.pins)

    @property
    def configured(self) -> bool:
        return bool(self.pins)

    def seconds_locked(self) -> int:
        return max(0, int(self.locked_until - self.clock()))

    def match(self, pin: str):
        """Name of the parent whose PIN this is ("" for the shared PIN), or None."""
        for name, h in self.pins:
            if check_pin_hash(pin, h):
                return name
        return None

    def check(self, pin: str) -> tuple[bool, str]:
        ok, msg, _name = self.check_who(pin)
        return ok, msg

    def check_who(self, pin: str) -> tuple[bool, str, str]:
        """Returns (ok, message, name)."""
        with self._lock:
            if not self.pins:
                return False, "No parent PIN is set up yet.", SHARED
            if self.seconds_locked():
                return False, f"Too many tries. Wait {self.seconds_locked() // 60 + 1} min.", SHARED
            name = self.match(pin)
            if name is not None:
                self.failures = 0
                return True, "ok", name
            self.failures += 1
            if self.failures >= MAX_TRIES:
                self.failures = 0
                self.locked_until = self.clock() + LOCKOUT_SECONDS
                return False, "Too many tries. PIN is locked for 5 minutes.", SHARED
            return False, "That PIN didn't match.", SHARED


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def sign_session(secret: str, now: float | None = None, ttl_seconds: int = SESSION_DAYS * 86400,
                 name: str = "") -> str:
    expires = int((now or time.time()) + ttl_seconds)
    nonce = secrets.token_hex(8)
    payload = f"{expires}.{nonce}" + (f".{_b64(name.encode())}" if name else "")
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    return payload + "." + _b64(sig)


def session_name(secret: str, token: str | None, now: float | None = None):
    """The parent's name in a valid session ("" if it has none), or None if the token isn't valid."""
    if not token or token.count(".") not in (2, 3):
        return None
    parts = token.split(".")
    payload, sig = ".".join(parts[:-1]), parts[-1]
    good = _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(good, sig):
        return None
    try:
        if int(parts[0]) <= (now or time.time()):
            return None
        if len(parts) == 4:
            return base64.urlsafe_b64decode(parts[2] + "=" * (-len(parts[2]) % 4)).decode()
    except (ValueError, UnicodeDecodeError):
        return None
    return ""


def verify_session(secret: str, token: str | None, now: float | None = None) -> bool:
    return session_name(secret, token, now) is not None

"""Trust Cloudflare Access sign-ins (optional; off unless cloudflare_access has a team_domain and aud).

The Cloudflare tunnel forwards each signed-in request with a JWT in the
Cf-Access-Jwt-Assertion header, signed by your Access team's keys. We check
the signature, issuer, audience (this Access app) and expiry, so the header
can't be faked by anyone on the home network.
"""
from __future__ import annotations

import logging
from typing import Optional

import jwt

log = logging.getLogger(__name__)
HEADER = "Cf-Access-Jwt-Assertion"


class AccessVerifier:
    def __init__(self, team_domain: Optional[str], aud: Optional[str]):
        self.team_domain = (team_domain or "").strip().removeprefix("https://").rstrip("/")
        self.aud = (aud or "").strip()
        self._jwks = (jwt.PyJWKClient(f"https://{self.team_domain}/cdn-cgi/access/certs", lifespan=3600)
                      if self.enabled else None)

    @property
    def enabled(self) -> bool:
        return bool(self.team_domain and self.aud)

    def email(self, token: Optional[str]) -> Optional[str]:
        """The signed-in person's email, or None if the token isn't a valid sign-in for this app."""
        if not token or not self.enabled:
            return None
        try:
            key = self._jwks.get_signing_key_from_jwt(token).key
            claims = jwt.decode(token, key, algorithms=["RS256"], audience=self.aud,
                                issuer=f"https://{self.team_domain}", options={"require": ["exp", "aud", "iss"]})
        except Exception as exc:
            log.info("rejected Cloudflare Access token: %s", exc)
            return None
        return claims.get("email") or None


def display_name(email: str) -> str:
    return email.split("@")[0].replace(".", " ").title()

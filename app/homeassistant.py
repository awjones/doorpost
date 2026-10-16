"""Optional read-only house status (garage, doors) from Home Assistant's REST API.

We read a few entity states with a long-lived token and show them as small
chips. We never load Home Assistant's own web UI on the frame.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx

from .config import HAEntity

log = logging.getLogger(__name__)


class HomeAssistant:
    def __init__(self, url: Optional[str], token: Optional[str], entities: list[HAEntity],
                 enabled: bool, http: Optional[httpx.Client] = None):
        self.url = (url or "").rstrip("/")
        self.token = token
        self.entities = entities
        self.enabled = enabled and bool(self.url and token and entities)
        self.http = http or httpx.Client(timeout=8)
        self.cached: list[dict] = []
        self.fetched_at: Optional[datetime] = None
        self.error: Optional[str] = None

    def status(self, now: datetime) -> list[dict]:
        if not self.enabled:
            return []
        if self.fetched_at and now - self.fetched_at < timedelta(seconds=30):
            return self.cached
        chips = []
        try:
            for e in self.entities:
                r = self.http.get(f"{self.url}/api/states/{e.entity}",
                                  headers={"Authorization": f"Bearer {self.token}"})
                r.raise_for_status()
                state = r.json().get("state", "unknown")
                chips.append({
                    "icon": e.icon,
                    "text": e.states.get(state, f"{e.entity.split('.')[-1].replace('_', ' ')}: {state}"),
                    "alert": state in e.alert_when,
                })
            self.cached, self.error = chips, None
        except Exception as exc:
            log.warning("home assistant failed: %s", exc)
            self.error = str(exc)[:200]
        self.fetched_at = now
        return self.cached

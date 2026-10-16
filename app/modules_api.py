"""Settings > Modules: turn parts of the frame on and off (see app/modules.py)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from . import modules as mods
from .config import effective_config


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def status_of(s, cfg: dict, mid: str) -> str:
    """A short line on how the module is doing, for its row. A leading "!" marks one that needs a look."""
    st = s.settings
    try:
        if mid == "calendar":
            good = len([c for c in st.calendars if c.ics_url or c.ics_file or c.caldav_calendar])
            return f"{good} of {len(st.calendars)} calendars connected" + (" · a problem to look at" if s.calendar.errors else "")
        if mid == "weather":
            if st.latitude is None or st.longitude is None:
                return "!Add your town in Settings > Overview"
            return "!Problem: " + s.weather.error if s.weather.error else "Location set"
        if mid == "chores":
            return f"{_plural(len(st.chores), 'chore')} for {_plural(len(st.kids), 'kid')}"
        if mid == "screen_time":
            return "Waiting for Chores" if not s.on("chores") else "Weekend total: " + s.screen()["total_label"]
        if mid == "photos":
            return _plural(len(s.photos.listing()), "photo") + " in the slideshow" if s.on("photos") else "Your photos stay saved"
        if mid == "portraits":
            have = len(s.portraits.index()) + len([k for k in st.kids if k.photo])
            return _plural(have, "photo") + " saved"
        if mid == "lists":
            shown = s.lists.shown()
            return _plural(len(shown), "list") + " on the frame" if shown else "!No lists picked yet"
        if mid == "house":
            ha = cfg.get("home_assistant") or {}
            n = len(ha.get("entities") or [])
            return _plural(n, "door or lock") + " shown" if ha.get("enabled") and n else "!Not set up yet"
        if mid == "special_days":
            return _plural(len(s.packs.on), "art pack") + " on"
        if mid == "lords_day":
            return "Faith art pack installed"
        if mid == "remote_access":
            ca = cfg.get("cloudflare_access") or {}
            return "Set up" if ca.get("team_domain") and ca.get("aud") else "!Not set up yet (see the setup guide)"
        if mid == "multi_frame":
            return _plural(len(st.frames) or 1, "frame")
        if mid == "kids_view":
            n = len([f for f in st.frames if (f or {}).get("home") == "kids"])
            return _plural(n, "kids frame") if n else "!Pick Kids as a frame's home screen in Settings > Frames"
    except Exception:  # a status line must never stop the page from loading
        return ""
    return ""


def make_router(require_admin, svc) -> APIRouter:
    """Settings > Modules routes (made by app/main.py, like app/storage.py's)."""
    router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])

    @router.get("/modules")
    def get_modules(s=Depends(svc)):
        cfg = effective_config(s.settings.demo)
        rows = mods.rows(s.settings, cfg, s.packs, lambda mid: status_of(s, cfg, mid))
        return {"modules": rows, "on": sorted(mods.on_set(s.settings)),
                "count": len([r for r in rows if r["on"]]), "total": len(rows)}

    @router.put("/modules")
    def put_modules(body: dict, request: Request, s=Depends(svc)):
        """Body: {id: true/false} for the modules that changed. Nothing is deleted when one goes off."""
        changes = {k: bool(v) for k, v in (body or {}).items() if k in mods.BY_ID}
        cfg = effective_config(s.settings.demo)
        try:
            new, notes = mods.apply_choice(mods.chosen(cfg, s.settings.demo), changes, s.packs)
        except ValueError as exc:
            raise HTTPException(400, str(exc))

        from .admin import _save   # the current admin module (tests reload it)

        def m(store, _cfg):
            store["modules"] = {k: v for k, v in new.items() if not mods.BY_ID[k].get("always_on")}
        _save(request, s, m)
        return {"ok": True, "notes": notes}

    return router

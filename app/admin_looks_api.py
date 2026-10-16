"""Settings > Overview > Settings look (app/admin_looks.py): the setting, and dressing /admin and /parent in it."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from . import admin_looks, frames, themes
from .config import effective_config, read_store, write_store


def make_router(require_admin, svc) -> APIRouter:
    router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])

    @router.get("/settings-look")
    def get_settings_look(s=Depends(svc)):
        cfg = effective_config(s.settings.demo)
        profs = frames.profiles(s.settings)
        choice = admin_looks.choose(cfg, profs, "admin")
        return {"setting": admin_looks.setting(cfg), "looks": admin_looks.list_public(),
                "frames": [{"id": p["id"], "name": p["name"], "look": p["look"],
                            "look_name": (themes.by_id(p["look"]) or {}).get("name", p["look"])} for p in profs],
                "now": {"id": choice["id"], "name": choice["name"], "reason": choice["reason"]}}

    @router.put("/settings-look")
    def put_settings_look(body: dict, request: Request, s=Depends(svc)):
        try:
            clean = admin_looks.validate(body, [p["id"] for p in frames.profiles(s.settings)])
        except admin_looks.LookError as exc:
            raise HTTPException(400, str(exc))
        store = read_store(s.settings.demo)
        store["settings_look"] = clean
        write_store(store, s.settings.demo)
        return {"ok": True, "setting": clean}

    return router


def dress(html: str, request: Request, page: str) -> str:
    """/admin and /parent in the Settings look. Never fails the page: anything wrong gives plain Navy."""
    try:
        s = request.app.state.services
        cfg = effective_config(s.settings.demo)
        choice = admin_looks.choose(cfg, frames.profiles(s.settings), page, request.query_params.get("look", ""))
        photo = ""
        t = themes.by_id(choice["id"])
        if t and admin_looks.admin_block(t).get("photo"):
            try:
                ph = s.photos.listing() if s.on("photos") else []
            except Exception:  # noqa: BLE001
                ph = []
            if ph:
                photo = f"photos/{ph[0]['id']}.jpg?shape=wide"
        here = request.url.path.lstrip("/") or page   # links stay on this Settings page
        return admin_looks.dress(html, choice, page, photo, here)
    except Exception:  # noqa: BLE001  (a look never stops Settings from opening)
        admin_looks.log.exception("Settings look failed; plain style used")
        return admin_looks.dress(html, {"id": "navy", "name": "Navy & gilt", "options": {}, "plain": True, "reason": "", "match": ""}, page)

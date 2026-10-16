"""Settings > Special days > Bible translation (app/bible.py, docs/bible-translations.md)."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from . import bible as B
from .config import read_store
from .main import Services, require_admin, svc

router = APIRouter(prefix="/api/admin/bible", dependencies=[Depends(require_admin)])


def _save(request: Request, s: Services, mutate) -> dict:
    from .admin import _save as save   # the settings page's save (checks, writes, reloads)
    return save(request, s, mutate)


def _extra(s: Services) -> list:
    """Every verse the turned-on packs quote, so a download covers packs beyond the built-in pictures too."""
    out = []
    for p in s.packs.passages():
        out += [v for v in (p.get("verses") or B.parse_ref(p.get("ref", ""))) if v not in out]
    return out


@router.get("")
def get_bible(s: Services = Depends(svc)):
    demo = s.settings.demo
    b = B.current(demo)
    passages = s.packs.passages()
    sample = next((p for p in passages if B.canon(p.get("ref", "")) == "Psalm 118:24"), passages[0] if passages else None)
    preview = []
    if sample:
        for t in B.status(demo):
            one = B.Bible(t["code"], b.sources, b.as_is, b.nasb_edition)
            text, cite, code = one.show(sample)
            preview.append({"code": t["code"], "text": text, "cite": cite, "from": code})
    cfg = B.settings_of(demo)
    return {"choice": b.choice, "translations": B.status(demo), "has_verses": bool(passages), "verses": len(passages),
            "preview": preview, "nasb_edition": b.nasb_edition, "demo": demo,
            "apibible": {"key_set": bool((read_store(demo).get("secrets") or {}).get("apibible_key")),
                         "bible_id": str(cfg.get("nasb_bible_id") or "")}}


@router.put("")
def put_bible(body: dict, request: Request, s: Services = Depends(svc)):
    choice = str(body.get("translation") or "").lower()
    if choice and choice not in B.TRANSLATIONS:
        raise HTTPException(400, "Pick ESV, KJV, BSB or NASB.")
    edition = str(body.get("nasb_edition") or "")
    if edition and edition not in B.NASB_NOTICE:
        raise HTTPException(400, "The NASB edition is 2020 or 1995.")

    def m(store, _cfg):
        cur = dict(store.get("bible") or {})
        if choice:
            cur["translation"] = choice
        if edition:
            cur["nasb_edition"] = edition
        store["bible"] = cur
    return _save(request, s, m)


@router.post("/bsb/download")
def download_bsb(s: Services = Depends(svc)):
    try:
        n = B.download_bsb(s.settings.demo, _extra(s))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Couldn't get the BSB file: {str(exc)[:160]}")
    return {"ok": True, "verses": n}


@router.delete("/{code}")
def remove(code: str, s: Services = Depends(svc)):
    """Remove a downloaded or added translation. The frame falls back to the next one (KJV, then the pack's text)."""
    if code not in ("bsb", "nasb"):
        raise HTTPException(400, "Only downloaded or added text can be removed.")
    B.remove(s.settings.demo, code)
    return {"ok": True}


@router.post("/nasb/import")
async def import_nasb(file: UploadFile, s: Services = Depends(svc)):
    raw = await file.read(B.MAX_IMPORT + 1)
    try:
        n = B.import_text(s.settings.demo, "nasb", raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True, "verses": n}


@router.get("/template.json")
def template():
    """The references to fill in with your own licensed text."""
    return JSONResponse(B.template(), headers={"Content-Disposition": 'attachment; filename="bible-verses-to-fill-in.json"'})


@router.put("/apibible")
def put_apibible(body: dict, request: Request, s: Services = Depends(svc)):
    """Your API.Bible key (kept with the other secrets, never sent back) and the Bible ID of the NASB on your plan."""
    key = str(body.get("key") or "").strip()
    bible_id = str(body.get("bible_id") or "").strip()
    if bible_id and not re.match(r"^[A-Za-z0-9_-]{6,80}$", bible_id):
        raise HTTPException(400, "That Bible ID doesn't look right. It's a code like 'a1b2c3d4e5f6a7b8-01' from API.Bible.")

    def m(store, _cfg):
        sec = dict(store.get("secrets") or {})
        if key:
            sec["apibible_key"] = key[:200]
        elif body.get("clear_key"):
            sec.pop("apibible_key", None)
        store["secrets"] = sec
        cur = dict(store.get("bible") or {})
        cur["nasb_bible_id"] = bible_id
        store["bible"] = cur
    return _save(request, s, m)


@router.post("/nasb/fetch")
def fetch_nasb(s: Services = Depends(svc)):
    demo = s.settings.demo
    key = (read_store(demo).get("secrets") or {}).get("apibible_key", "")
    try:
        n = B.fetch_apibible(demo, key, str(B.settings_of(demo).get("nasb_bible_id") or ""), "nasb", _extra(s))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Couldn't reach API.Bible: {str(exc)[:160]}")
    return {"ok": True, "verses": n}

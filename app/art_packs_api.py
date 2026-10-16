"""Settings > Art packs, and the drawings the frame loads (/art.js). See app/packs.py and docs/art-packs.md."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response

from . import packs as P
from .main import Services, require_admin, svc

public = APIRouter()
router = APIRouter(prefix="/api/admin/packs", dependencies=[Depends(require_admin)])
SVG_HEADERS = {"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'", "X-Content-Type-Options": "nosniff",
               "Cache-Control": "no-cache"}


@public.get("/art.js")
def art_js(request: Request, s: Services = Depends(svc)):
    """window.THEMES: every drawing from the turned-on packs. The pages ask for it as art.js?v=<packs version>."""
    tag = f'"{s.packs.signature}"'
    if request.headers.get("if-none-match") == tag:
        return Response(status_code=304, headers={"ETag": tag})
    return Response(s.packs.art_js(), media_type="application/javascript; charset=utf-8",
                    headers={"ETag": tag, "Cache-Control": "no-cache"})


@public.get("/art/preview/{pid}.svg")
def preview(pid: str, s: Services = Depends(svc)):
    svg = P.preview_svg(s.packs, pid)
    if svg is None:
        raise HTTPException(404)
    return Response(svg, media_type="image/svg+xml", headers=SVG_HEADERS)


@public.get("/art/packs/{pid}/{rel:path}")
def pack_picture(pid: str, rel: str, s: Services = Depends(svc)):
    """A png or jpg picture from a turned-on pack."""
    path = P.file_in_pack(s.packs, pid, rel)
    if path is None:
        raise HTTPException(404)
    return FileResponse(path, headers={"X-Content-Type-Options": "nosniff"})


@router.get("")
def list_packs(s: Services = Depends(svc)):
    return {"packs": s.packs.view(), "index": P.index_view(s.packs), "max_mb": P.MAX_ZIP // (1024 * 1024)}


def _error(exc: Exception):
    if isinstance(exc, P.PackError):
        raise HTTPException(400, str(exc))
    raise HTTPException(502, f"Couldn't get that pack: {str(exc)[:160]}")


def _save(request: Request, s: Services, mutate) -> dict:
    from .admin import _save as save   # at call time: the settings page's save (checks, writes, reloads)
    return save(request, s, mutate)


def _set_off(request: Request, s: Services, pid: str, off: bool) -> dict:
    def m(store, _cfg):
        cur = dict(store.get("art_packs") or {})
        ids = [x for x in (cur.get("off") or []) if x != pid]
        cur["off"] = ids + [pid] if off else ids
        store["art_packs"] = cur
    return _save(request, s, m)


@router.put("/{pid}")
def turn(pid: str, body: dict, request: Request, s: Services = Depends(svc)):
    """Turn a pack on or off. Off: none of its pictures or rules are used, anywhere."""
    if not any(p["id"] == pid for p in s.packs.all):
        raise HTTPException(404, "No such pack.")
    return _set_off(request, s, pid, not bool(body.get("on")))


@router.post("/install/{pid}")
def install(pid: str, request: Request, s: Services = Depends(svc)):
    """Install (or update) a pack from the packs list (packs/index.json), checking its sha256."""
    try:
        m = P.install_from_index(pid, s.settings.demo)
    except Exception as exc:  # noqa: BLE001
        _error(exc)
    _set_off(request, s, m["id"], False)
    return {"ok": True, "id": m["id"], "name": m["name"]}


@router.post("/upload")
async def upload(file: UploadFile, request: Request, s: Services = Depends(svc)):
    """Install a pack from a zip on this computer."""
    data = await file.read(P.MAX_ZIP + 1)
    try:
        m = P.install_zip(data, s.settings.demo)
    except Exception as exc:  # noqa: BLE001
        _error(exc)
    _set_off(request, s, m["id"], False)
    return {"ok": True, "id": m["id"], "name": m["name"]}


@router.delete("/{pid}")
def remove(pid: str, request: Request, s: Services = Depends(svc)):
    try:
        P.remove(pid, s.settings.demo)
    except P.PackError as exc:
        raise HTTPException(400, str(exc))
    def m(store, _cfg):
        cur = dict(store.get("art_packs") or {})
        cur["off"] = [x for x in (cur.get("off") or []) if x != pid]
        store["art_packs"] = cur
    return _save(request, s, m)

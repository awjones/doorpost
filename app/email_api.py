"""Settings > Email updates, and the quick approve links in the daily email (app/email_updates.py).

The /api/email/link/* addresses need no PIN or sign-in: the link's secret is the
permission. They only take POSTs to change anything, so a mail service opening the link
to scan it approves nothing.
"""
from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import email_updates as eu
from .admin import _save
from .mailer import PROVIDERS, MailError
from .main import Services, _payload_cache, require_admin, svc

admin = APIRouter(prefix="/api/admin/email-updates", dependencies=[Depends(require_admin)])
public = APIRouter(prefix="/api/email")

EMAIL = re.compile(r"^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$")
TIME = re.compile(r"^\d{1,2}:\d{2}$")


def view(s: Services) -> dict:
    cfg = eu.config(s.settings)
    now = s.now()
    acct = eu.account(s.settings)
    return {
        "daily": cfg["daily"], "weekly": cfg["weekly"], "reminder": cfg["reminder"],
        "people": eu.people(s.settings),
        "account": {**{k: v for k, v in cfg["account"].items()}, "password_set": bool(s.settings.smtp_password),
                    "ready": acct.ready, "providers": list(PROVIDERS) + ["other"]},
        "frame_url": s.settings.frame_url,
        "new_week": {"day": s.settings.screen_time.new_week_day, "time": s.settings.screen_time.new_week_time},
        "screen_time_on": s.on("screen_time"),
        "upcoming": eu.upcoming(s, now),
        "log": eu.recent(s),
        "demo": s.settings.demo,
        "outbox": [{"to": m["to"], "subject": m["subject"]} for m in s.mailer.outbox[:5]] if s.settings.demo else [],
        "now": now.replace(tzinfo=None, microsecond=0).isoformat(),
    }


@admin.get("")
def get_email_updates(s: Services = Depends(svc)):
    return view(s)


def _flags(src: dict, defaults: dict) -> dict:
    out = {}
    for k, d in defaults.items():
        v = src.get(k, d)
        if isinstance(d, bool):
            out[k] = bool(v)
        elif k in ("time",):
            v = str(v or d)
            if not TIME.match(v):
                raise HTTPException(400, "Times look like 19:30.")
            out[k] = eu._hhmm(v, d)
        elif k == "day":
            if v not in eu.DAYS:
                raise HTTPException(400, "Pick a day of the week.")
            out[k] = v
        else:
            out[k] = v
    return out


@admin.put("")
def put_email_updates(body: dict, request: Request, s: Services = Depends(svc)):
    """The three emails and who gets them (the sending account is saved on its own)."""
    daily = _flags(body.get("daily") or {}, eu.DEFAULTS["daily"])
    weekly = _flags(body.get("weekly") or {}, eu.DEFAULTS["weekly"])
    reminder = _flags(body.get("reminder") or {}, eu.DEFAULTS["reminder"])
    parents = {n.lower() for n in eu.parent_names(s.settings)}
    people = []
    for p in body.get("people") or []:
        name = str(p.get("name") or "").strip()[:40]
        email = str(p.get("email") or "").strip()[:120]
        if not name:
            continue
        if email and not EMAIL.match(email):
            raise HTTPException(400, f"{name}'s email address doesn't look right.")
        other = name.lower() not in parents or bool(p.get("other"))
        people.append({"name": name, "email": email, "other": other, **{k: bool(p.get(k, True)) for k in eu.KINDS}})

    def m(store, cfg):
        cur = dict(store.get("email_updates") or {})
        cur.update({"daily": daily, "weekly": weekly, "reminder": reminder, "people": people})
        store["email_updates"] = cur
    return _save(request, s, m)


class AccountBody(BaseModel):
    provider: str = "gmail"
    host: str = ""
    port: int = 587
    security: str = "starttls"
    user: str = ""
    password: str = ""          # empty: keep the saved one
    from_name: str = ""
    from_address: str = ""
    forget_password: bool = False


@admin.put("/account")
def put_account(body: AccountBody, request: Request, s: Services = Depends(svc)):
    if body.provider not in (*PROVIDERS, "other"):
        raise HTTPException(400, "Pick Gmail, Outlook, iCloud or Other.")
    user = body.user.strip()
    if user and not EMAIL.match(user) and body.provider != "other":
        raise HTTPException(400, "The account is your full email address.")
    if body.from_address.strip() and not EMAIL.match(body.from_address.strip()):
        raise HTTPException(400, "The From address doesn't look right.")
    if body.provider == "other" and not body.host.strip():
        raise HTTPException(400, "Fill in the mail server (SMTP) address.")
    if not 1 <= body.port <= 65535:
        raise HTTPException(400, "The port is a number like 587.")

    def m(store, cfg):
        cur = dict(store.get("email_updates") or {})
        cur["account"] = {"provider": body.provider, "host": body.host.strip()[:120], "port": body.port,
                          "security": body.security if body.security in ("starttls", "ssl", "none") else "starttls",
                          "user": user[:120], "from_name": body.from_name.strip()[:60], "from_address": body.from_address.strip()[:120]}
        store["email_updates"] = cur
        sec = store.setdefault("secrets", {})
        if body.forget_password:
            sec.pop("smtp_password", None)
        elif body.password:
            sec["smtp_password"] = body.password.replace(" ", "") if body.provider == "gmail" else body.password
    return _save(request, s, m)


class TestBody(BaseModel):
    kind: str
    name: str


@admin.post("/test")
def send_test(body: TestBody, request: Request):
    s = request.app.state.services   # the newest settings (a save just before reloads them)
    person = next((p for p in eu.people(s.settings) if p["name"] == body.name), None)
    if not person or not person["email"]:
        raise HTTPException(400, "Add an email address for them first, then save.")
    if not s.settings.demo and not eu.account(s.settings).ready:
        raise HTTPException(400, "Set up the sending account first.")
    try:
        r = eu.send_test(s, body.kind, person, s.now())
    except (ValueError, MailError) as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True, **r, "demo": s.settings.demo}


@admin.get("/preview/{kind}")
def preview(kind: str, s: Services = Depends(svc)):
    if kind not in eu.KINDS:
        raise HTTPException(404)
    return HTMLResponse(eu.preview(s, kind, s.now()), headers={"Cache-Control": "no-store"})


@admin.get("/outbox/{n}")
def outbox(n: int, s: Services = Depends(svc)):
    """Demo mode: an email that would have gone out."""
    if not s.settings.demo or not 0 <= n < len(s.mailer.outbox):
        raise HTTPException(404)
    return HTMLResponse(s.mailer.outbox[n]["html"], headers={"Cache-Control": "no-store"})


# ---------------- the links in the daily email (no PIN: the link's secret is the permission) ----------------

class ApproveBody(BaseModel):
    items: Optional[list[int]] = None
    all: bool = False


class UndoBody(BaseModel):
    idx: int


@public.get("/link/{token}")
def link(token: str, s: Services = Depends(svc)):
    return eu.link_view(s, token)


@public.post("/link/{token}/approve")
def link_approve(token: str, body: ApproveBody, s: Services = Depends(svc)):
    v = eu.link_view(s, token)
    if v["state"] == "unknown":
        raise HTTPException(404, "This link isn't valid.")
    idxs = [i["idx"] for i in v["items"] if i["status"] == "waiting"] if body.all else (body.items or [])
    try:
        r = eu.link_approve(s, token, idxs)
    except eu.LinkError as exc:
        raise HTTPException(410, str(exc))
    _payload_cache["at"] = 0.0   # the frame shows it on its next check
    return r


@public.post("/link/{token}/undo")
def link_undo(token: str, body: UndoBody, s: Services = Depends(svc)):
    try:
        r = eu.link_undo(s, token, body.idx)
    except eu.LinkError as exc:
        raise HTTPException(409, str(exc))
    except Exception as exc:  # noqa: BLE001  (a chore error reads plainly)
        raise HTTPException(409, str(exc))
    _payload_cache["at"] = 0.0
    return r

"""Doorpost server.

Run:    uvicorn app.main:app --host 0.0.0.0 --port 8090
Demo:   FRAME_DEMO=1 uvicorn app.main:app --port 8090 --reload   (PIN 1234)
Add-on: see addon/ (runs the same app inside Home Assistant)
"""
from __future__ import annotations

import logging
from html import escape as html_escape
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import chores as chore_logic
from . import demo
from . import screentime as st
from .auth import PinGuard, hash_pin, session_name, sign_session, verify_session
from .cf_access import HEADER as ACCESS_HEADER
from .cf_access import AccessVerifier, display_name
from .calendar_feed import CalendarService
from .config import DATA_DIR, WEB_DIR, Settings, load_settings
from .db import Database
from .frame import build_payload, calendar_view
from .homeassistant import HomeAssistant
from . import frames as frame_profiles
from . import themes
from .lists import Lists
from .photos import FocusStore, PhotoLibrary
from .portraits import Portraits, people_of
from .special import HolidayFeed, SpecialDays
from . import packs as art_packs
from . import modules as mods
from .timeutil import now_in
from .weather import WeatherService, convert as convert_weather

log = logging.getLogger("family_frame")
COOKIE = "ff_parent"
FRAME_TOKEN_SECONDS = 120   # PIN unlock on the frame lasts two minutes
INGRESS_IP = "172.30.32.2"  # Home Assistant's sidebar proxy; HA has already signed the user in
KID_PHOTOS = DATA_DIR / "kid-photos"
SPECIAL_PHOTOS = DATA_DIR / "special-photos"
PORTRAITS = DATA_DIR / "portraits"


class Services:
    def __init__(self, settings: Settings, previous: Optional["Services"] = None):
        self.settings = settings
        self.packs = art_packs.load(settings.demo)   # the turned-on art packs (app/packs.py)
        self.db = Database(DATA_DIR / ("demo.db" if settings.demo else "frame.db"))
        self.calendar = CalendarService(settings, DATA_DIR / "calendar-cache")
        self.weather = WeatherService.from_settings(settings)
        self.home = HomeAssistant(settings.ha_url, settings.ha_token, settings.ha_entities,
                                  settings.ha_enabled and self.on("house"))
        self.photos = PhotoLibrary(settings.photos_folder, DATA_DIR / "photo-cache", settings.photo_sources,
                                   focus=FocusStore(self.db))
        self.lists = Lists(self.db, settings.lists)
        self.portraits = Portraits(PORTRAITS)
        self.holidays = HolidayFeed(settings.special.get("holiday_url", ""), holiday_cache(settings.special.get("holiday_url", "")))
        pins = list(settings.parent_pins) + ([("", settings.pin_hash)] if settings.pin_hash else [])
        if settings.demo and not pins:
            pins = [(name, hash_pin(pin)) for name, pin in demo.DEMO_PINS]
        self.pin = PinGuard(pins)
        from .email_updates import make_mailer
        self.mailer = previous.mailer if previous is not None else make_mailer(settings, DATA_DIR)   # demo outbox survives a save
        self.access = (AccessVerifier(settings.access_team_domain, settings.access_aud) if self.on("remote_access")
                       else AccessVerifier(None, None))
        self._fake_start: Optional[datetime] = None
        self._started: Optional[datetime] = None
        if previous is not None:  # settings were saved: keep what's still valid
            self._fake_start, self._started = previous._fake_start, previous._started
            self.photos.adopt(previous.photos)   # same folder: keep the index (re-reading 1,200 photos took ~12 s on the Pi)
            self.calendar.calendars = previous.calendar.calendars
            if previous.weather.same_setup(self.weather):
                self.weather = previous.weather   # keep the cached reading
            if previous.holidays.url == self.holidays.url:
                self.holidays = previous.holidays
            if previous.pin.stored_hash == self.pin.stored_hash or (
                    settings.demo and not settings.parent_pins and not settings.pin_hash):
                self.pin = previous.pin
            if (previous.access.team_domain, previous.access.aud) == (self.access.team_domain, self.access.aud):
                self.access = previous.access  # keep its cached signing keys

    def on(self, mid: str) -> bool:
        """Is this module turned on (Settings > Modules, app/modules.py)?"""
        return mods.is_on(self.settings, mid)

    @property
    def special(self) -> SpecialDays:
        if not self.on("special_days"):
            return mods.NoSpecialDays()
        cfg = self.settings.special if self.on("lords_day") else dict(self.settings.special, sundays=False)
        return SpecialDays(cfg, self.holidays, SPECIAL_PHOTOS, people=people_of(self.settings),
                           portrait=self.portrait_url, tz=self.settings.timezone, packs=self.packs)

    def portrait_url(self, person: dict) -> Optional[str]:
        """A person's photo; for a kid without one, an older face photo. None when they'd rather show their initial."""
        if person.get("use_initial") or not self.on("portraits"):
            return None
        url = self.portraits.url(person["slug"])
        if url:
            return url
        kid = next((k for k in self.settings.kids if k.id == person.get("kid")), None)
        return f"kids/{kid.id}.jpg?v={kid.photo}" if kid and kid.photo else None

    def google(self):
        """The family's Google sign-in (Photos Picker and Tasks share it; see app/google_auth.py)."""
        from .config import effective_config, read_store
        from .google_auth import GoogleAccount
        demo_mode = self.settings.demo
        cfg = effective_config(demo_mode)
        # Older setups kept the client ID under special_days.google_photos.
        cid = (cfg.get("google") or {}).get("client_id") or ((cfg.get("special_days") or {}).get("google_photos") or {}).get("client_id", "")
        secret = read_store(demo_mode).get("secrets", {}).get("google_client_secret", "")
        return GoogleAccount(DATA_DIR / ("google.demo.json" if demo_mode else "google.json"),
                             cid, secret, cfg.get("frame_url") or "", self.settings.secret)

    def google_photos(self):
        from .google_photos import GooglePhotos
        return GooglePhotos(self.google())

    def sync_google_tasks(self) -> None:
        """Every minute (and right after a change on the frame): Google Tasks <-> the frame's lists."""
        from .google_tasks import sync_now
        sync_now(self)

    def now(self) -> datetime:
        real = now_in(self.settings.timezone)
        if self._fake_start is None:
            return real
        # FRAME_NOW (testing/screenshots only): start the clock at that time and let it run.
        return self._fake_start + (real - self._started)

    def set_fake_now(self, value: str) -> None:
        from zoneinfo import ZoneInfo
        self._started = now_in(self.settings.timezone)
        self._fake_start = datetime.fromisoformat(value).replace(tzinfo=ZoneInfo(self.settings.timezone))

    def weather_now(self, now):
        if not self.on("weather"):
            return None
        if self.settings.demo:  # the sample weather, in the units chosen in Settings
            w = convert_weather(demo.DEMO_WEATHER, *self.weather.units())
        else:
            w = self.weather.get(now)
        if not w:
            return w
        cfg = self.weather.config or {}  # Settings > General: where wind shows, and 62° vs 62°F
        return dict(w, display={"wind": cfg.get("show_wind") or "panel", "letter": cfg.get("unit_letter") == "yes"})

    def home_status(self, now):
        if not self.on("house"):
            return []
        return demo.DEMO_HOME if self.settings.demo else self.home.status(now)

    def screen(self) -> dict:
        return st.summary(self.db, self.settings.screen_time, self.settings.kids, self.now())


def holiday_cache(url: str):
    import hashlib
    return DATA_DIR / "calendar-cache" / f"holidays-{hashlib.sha1(url.encode()).hexdigest()[:8]}.ics"


def reload_services(app: FastAPI) -> Services:
    """Rebuild everything from the saved settings (after an admin-panel save)."""
    old = app.state.services
    new = Services(load_settings(), previous=old)
    app.state.services = new
    def warm():
        new.calendar.refresh()
        if new.on("special_days"):
            new.holidays.refresh()
        if new.on("photos"):
            new.photos.scan()
    threading.Thread(target=warm, daemon=True).start()
    return new


def background_loop(app: FastAPI, stop: threading.Event) -> None:
    last_cal, last_svc = time.time(), app.state.services  # startup already read the calendars
    while not stop.is_set():
        s = app.state.services
        try:
            if s is not last_svc or time.time() - last_cal > s.settings.calendar_refresh_minutes * 60:
                s.calendar.refresh()
                if s.on("special_days"):
                    s.holidays.refresh()  # about once a day
                last_cal, last_svc = time.time(), s
            if s.on("photos"):  # a module that is off does no background work (app/modules.py)
                s.photos.maybe_rescan()
                s.photos.prepare_some(15)  # a few each minute; the Pi stays responsive
        except Exception:
            log.exception("background loop error")
        try:
            if s.on("lists"):
                s.sync_google_tasks()
        except Exception:
            log.exception("Google Tasks sync error")
        try:
            if s.on("email_updates"):
                from . import email_updates
                email_updates.tick(s)
        except Exception:
            log.exception("email updates error")
        stop.wait(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # its INFO lines include secret calendar addresses
    from . import compat, config as _config
    compat.upgrade(_config.DATA_DIR, os.environ.get("FRAME_DEMO", "").lower() in ("1", "true", "yes"))   # data from an older version
    settings = load_settings()
    if art_packs.seed_defaults(settings.demo):   # the Faith pack comes installed and on (once; removing it sticks)
        settings = load_settings()               # read again so modules that need the new pack (Lord's Day) see it
    services = Services(settings)
    if os.environ.get("FRAME_NOW"):
        services.set_fake_now(os.environ["FRAME_NOW"])
    app.state.services = services
    services.calendar.refresh()
    if services.on("special_days"):
        services.holidays.refresh()
    if services.on("photos"):
        if services.settings.demo and not os.environ.get("FRAME_PHOTOS_DIR"):   # a drawn landscape, so the Photos screen and photo looks have something
            from . import demo_photo
            demo_photo.ensure(services.settings.photos_folder)
        services.photos.scan()
    st.ensure_started(services.db, services.now())
    if services.settings.demo:
        demo.seed_week(services.db, services.settings, services.now())
        demo.seed_today(services.db, services.settings, services.now().date(), services.now())
        services.lists.seed_demo(services.now())
        from .google_tasks import seed_demo as seed_google_tasks
        seed_google_tasks(services.lists, services.now())
    stop = threading.Event()
    thread = threading.Thread(target=background_loop, args=(app, stop), daemon=True)
    thread.start()
    yield
    stop.set()


app = FastAPI(title="Doorpost", lifespan=lifespan)
# Compress what the Pi sends (the frame's data every 30 s, the Settings photo list); photos are already compressed.
from fastapi.middleware.gzip import GZipMiddleware  # noqa: E402
app.add_middleware(GZipMiddleware, minimum_size=1500, compresslevel=5)


@app.middleware("http")
async def module_guard(request: Request, call_next):
    """A module that is off (Settings > Modules) owns no addresses: they answer 404 (app/modules.py ROUTES)."""
    s = getattr(request.app.state, "services", None)
    off = mods.guard(request.url.path, s.settings) if s is not None else None
    if off:
        return JSONResponse({"detail": f"{mods.BY_ID[off]['name']} is turned off in Settings > Modules."}, status_code=404)
    return await call_next(request)


def svc(request: Request) -> Services:
    return request.app.state.services


def via_ingress(request: Request, s: Services) -> bool:
    """True when the request came through Home Assistant's sidebar (HA already checked the login)."""
    return s.settings.addon and request.client is not None and request.client.host == INGRESS_IP


def access_email(request: Request, s: Services) -> Optional[str]:
    """Signed in through Cloudflare Access, when it is set up (verified, not just trusted)."""
    return s.access.email(request.headers.get(ACCESS_HEADER))


def require_parent(request: Request, s: Services = Depends(svc)) -> str:
    """Who is acting, for the log: a first name when we know it."""
    email = access_email(request, s)
    if email:
        return display_name(email)
    if via_ingress(request, s):
        name = request.headers.get("X-Remote-User-Display-Name") or request.headers.get("X-Remote-User-Name")
        return f"{name} (Home Assistant)" if name else "Home Assistant"
    on_frame = bool(request.headers.get("X-Parent-Token"))
    name = session_name(s.settings.secret, request.headers.get("X-Parent-Token") or request.cookies.get(COOKIE))
    if name is None:
        raise HTTPException(401, "Parent PIN needed")
    return name or ("Parent (on the frame)" if on_frame else "Parent (phone)")


def require_admin(request: Request, s: Services = Depends(svc)) -> str:
    """Settings hold calendar addresses and logins. As an add-on they're only reachable
    from the Home Assistant sidebar; standalone, they need the parent PIN sign-in."""
    if via_ingress(request, s) or access_email(request, s):
        return "ingress"
    if s.settings.addon:
        raise HTTPException(403, "Open Settings from Doorpost in the Home Assistant sidebar "
                                 "(or through Cloudflare Access, if you set it up).")
    if not verify_session(s.settings.secret, request.cookies.get(COOKIE)):
        raise HTTPException(401, "Parent PIN needed")
    return "pin"


class PinBody(BaseModel):
    pin: str


# ---------------- frame ----------------

_payload_lock = threading.Lock()
_payload_cache: dict = {"at": 0.0, "svc": None, "data": None}


def frame_payload(s: Services, max_age: float = 15.0) -> dict:
    """Every screen polls every 30 s; build once and share it, never in parallel."""
    with _payload_lock:
        c = _payload_cache
        if c["svc"] is not s or time.time() - c["at"] > max_age:
            c["data"], c["at"], c["svc"] = build_payload(s), time.time(), s
            c["data"]["asset_version"] = _asset_version() + s.packs.signature + _themes_version(s)  # the frame reloads itself when this changes
            c["data"]["clock_verses"] = s.packs.clock_verses   # the bedtime clock's verses (faith pack)
        return c["data"]


@app.get("/api/frame")
def frame(frame: str = "", w: Optional[int] = None, h: Optional[int] = None, s: Services = Depends(svc)):
    """Everything a frame shows, narrowed to its profile (Settings > Frames). w, h: its screen size."""
    prof = frame_profiles.get(s.settings, frame)
    frame_profiles.note_seen(prof["id"], w, h)
    return mods.narrow(frame_profiles.apply(frame_payload(s), prof, s.settings, s.now()), s.settings)


@app.get("/api/frames")
def frame_list(s: Services = Depends(svc)):
    """The frame profiles, for the picker on a new frame (names and looks only)."""
    return {"frames": [{k: p[k] for k in ("id", "name", "look", "home", "screens")} for p in frame_profiles.live(s.settings)],
            "looks": [themes.public(t) for t in themes.enabled()]}


class NewFrame(BaseModel):
    name: str
    look: str = ""
    home: Optional[str] = None   # Today, Kids, Clock or Chores; None: the look's usual one (its theme.json)


@app.post("/api/parent/frames")
def new_frame(body: NewFrame, request: Request, s: Services = Depends(svc), _who: str = Depends(require_parent)):
    """'New frame here' on the frame's gear menu (after the parent PIN). Details are finished in Settings > Frames."""
    from .config import read_store, write_store
    name = body.name.strip()[:40]
    if not name:
        raise HTTPException(400, "Give the frame a name.")
    store = read_store(s.settings.demo)
    current = store.get("frames") or [dict(f) for f in s.settings.frames] or [dict(frame_profiles.DEFAULT)]
    ids = {p.get("id") for p in current}
    fid = frame_profiles.slug(name) or "frame"
    while fid in ids:
        fid += "-2"
    look = body.look if body.look in frame_profiles.LOOKS else frame_profiles.DEFAULT["look"]
    usual, screens = themes.new_frame_defaults(look, frame_profiles.SCREENS, frame_profiles.DEFAULT["screens"])
    home = body.home if body.home in frame_profiles.HOMES else (usual if usual in frame_profiles.HOMES else "today")
    store["frames"] = current + [{"id": fid, "name": name, "look": look, "home": home, "screens": screens}]
    write_store(store, s.settings.demo)
    reload_services(request.app)
    return {"ok": True, "id": fid}


@app.get("/api/photos")
def photo_list(s: Services = Depends(svc)):
    """The slideshow order for today; the frame asks only when /api/frame's photos_version changes."""
    return {"version": s.photos.version(), "photos": s.photos.listing()}


class ListAdd(BaseModel):
    title: str


@app.post("/api/lists/{list_id}/add")
def list_add(list_id: str, body: ListAdd, s: Services = Depends(svc)):
    """Add an item on the frame. It reaches Reminders the next time the Mac checks in (about 30 s)."""
    if not s.lists.can_add:
        raise HTTPException(403, "Adding from the frame is turned off in Settings > Lists.")
    try:
        item = s.lists.add(list_id, body.title, s.now())
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except KeyError:
        raise HTTPException(404, "That list isn't on the frame.")
    _payload_cache["at"] = 0
    _push_soon(s, list_id)
    return item


@app.post("/api/lists/item/{item_id}/toggle")
def list_toggle(item_id: str, s: Services = Depends(svc)):
    if not s.lists.can_check:
        raise HTTPException(403, "Checking off from the frame is turned off in Settings > Lists.")
    try:
        r = s.lists.toggle(item_id, s.now())
    except KeyError:
        raise HTTPException(404, "That item is gone.")
    _payload_cache["at"] = 0
    _push_soon(s, s.lists.list_of(item_id))
    return r


def _push_soon(s: Services, list_id: Optional[str]) -> None:
    """A change to a Google Tasks list goes to Google right away instead of at the next minute."""
    if list_id and s.lists.source_of(list_id) == "google":
        threading.Thread(target=s.sync_google_tasks, daemon=True).start()


@app.get("/api/calendar")
def calendar(view: str = "month", offset: int = 0, frame: str = "", s: Services = Depends(svc)):
    """Another week or month for the frame's back/forward buttons."""
    if view not in ("week", "rolling", "month") or not -24 <= offset <= 60:
        raise HTTPException(400, "view must be week, rolling or month; offset -24..60")
    now = s.now()
    return frame_profiles.for_calendar_page(calendar_view(s, view, offset, now.date(), now), frame_profiles.get(s.settings, frame))


@app.post("/api/chores/{chore_id}/claim")
def claim(chore_id: str, s: Services = Depends(svc)):
    try:
        status = chore_logic.claim(s.db, s.settings, chore_id, s.now().date(), s.now())
    except chore_logic.ChoreError as exc:
        raise HTTPException(404, str(exc))
    _payload_cache["at"] = 0.0
    return {"status": status}


@app.post("/api/parent/unlock")
def unlock(body: PinBody, response: Response, request: Request, s: Services = Depends(svc)):
    ok, msg, name = s.pin.check_who(body.pin)
    if not ok:
        return JSONResponse({"ok": False, "message": msg}, status_code=403)
    if request.query_params.get("remember") == "1":  # phone page: stay signed in for 30 days
        response.set_cookie(COOKIE, sign_session(s.settings.secret, name=name), max_age=30 * 86400,
                            httponly=True, samesite="strict")
        return {"ok": True, "name": name}
    return {"ok": True, "name": name,
            "token": sign_session(s.settings.secret, ttl_seconds=FRAME_TOKEN_SECONDS, name=name)}


@app.get("/api/parent/me")
def parent_me(request: Request, s: Services = Depends(svc)):
    email = access_email(request, s)
    name = display_name(email) if email else (session_name(s.settings.secret, request.cookies.get(COOKIE)) or None)
    return {"access": bool(email), "name": name,
            "can_admin": bool(email) or via_ingress(request, s) or not s.settings.addon}


@app.post("/api/parent/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE)
    return {"ok": True}


@app.get("/api/parent/summary")
def parent_summary(s: Services = Depends(svc), _who: str = Depends(require_parent)):
    today = s.now().date()
    kids = {k.id: k for k in s.settings.kids}
    rows = chore_logic.chores_for(s.db, s.settings, today) if s.on("chores") else []
    with s.db.connect() as conn:
        recent = [dict(r) for r in conn.execute(
            "SELECT * FROM ledger ORDER BY id DESC LIMIT 15").fetchall()]
    earlier = []
    if s.on("chores"):   # waiting since an earlier day this week: still approvable
        first = chore_logic.earliest_day(s.db, today)
        if first < today:
            earlier = chore_logic.waiting_since(s.db, s.settings, first, today - timedelta(days=1))
    def dressed(c):
        k = kids[c["kid"]]
        return dict(c, kid_name=k.name, color=k.color, initial=k.initial, photo=kid_photo_url(k))
    return {
        "date": today.isoformat(),
        "kids": [{"id": k.id, "name": k.name, "initial": k.initial, "color": k.color, "photo": kid_photo_url(k),
                  "chores": [c for c in rows if c["kid"] == k.id]} for k in s.settings.kids],
        "waiting": [dressed(c) for c in rows if c["status"] == "waiting"],
        "earlier": [dict(dressed(c), day_label=date.fromisoformat(c["day"]).strftime("%a")) for c in earlier if c["kid"] in kids],
        "recent": recent if s.on("chores") else [],
        "modules": sorted(mods.on_set(s.settings)),   # the phone page shows only the tabs that are on
    }


def _chore_day(s: Services, day: Optional[str]) -> date:
    """?day=YYYY-MM-DD for a chore still waiting from earlier this week; today when left out."""
    if not day:
        return s.now().date()
    try:
        return date.fromisoformat(day)
    except ValueError:
        raise HTTPException(400, "day must be YYYY-MM-DD")


@app.post("/api/parent/chores/{chore_id}/approve")
def approve(chore_id: str, day: Optional[str] = None, s: Services = Depends(svc), who: str = Depends(require_parent)):
    try:
        result = chore_logic.approve_on(s.db, s.settings, chore_id, _chore_day(s, day), s.now(), who)
    except chore_logic.ChoreError as exc:
        raise HTTPException(409, str(exc))
    _payload_cache["at"] = 0.0
    return {"ok": True, "approved": result}


@app.post("/api/parent/chores/{chore_id}/send-back")
def send_back(chore_id: str, day: Optional[str] = None, s: Services = Depends(svc), _who: str = Depends(require_parent)):
    _payload_cache["at"] = 0.0
    chore_logic.send_back(s.db, chore_id, _chore_day(s, day))
    return {"ok": True}


_forced = {"at": 0.0}


@app.post("/api/refresh-now")
def refresh_now(s: Services = Depends(svc)):
    """The frame's top-left hot corner: read the calendars again right now (at most once a minute,
    so a run of taps can't hammer Google or the Pi), then the frame pulls everything fresh."""
    fresh = time.time() - _forced["at"] > 60
    if fresh:
        _forced["at"] = time.time()
        s.calendar.refresh()
    _payload_cache["at"] = 0
    return {"ok": True, "fresh": fresh, "errors": s.calendar.errors}


@app.post("/api/parent/refresh")
def refresh(s: Services = Depends(svc), _who: str = Depends(require_parent)):
    s.calendar.refresh()
    s.photos.refresh_remote(force=True)
    s.photos.scan()
    return {"ok": True}


# ---------------- screen time (parents) ----------------

def _screen_error(exc: st.ScreenTimeError):
    raise HTTPException(409, str(exc))


@app.get("/api/parent/screen")
def parent_screen(s: Services = Depends(svc), who: str = Depends(require_parent)):
    d = s.screen()
    d["kids"] = [{"id": k.id, "name": k.name, "initial": k.initial, "color": k.color, "photo": kid_photo_url(k),
                  "minutes": d["kid_minutes"].get(k.id, 0), "bonus": d["kid_bonus"].get(k.id, 0)} for k in s.settings.kids]
    d["you"] = who
    return d


class AdjustBody(BaseModel):
    minutes: int
    kid: Optional[str] = None
    scope: str = "family"
    note: str = ""


@app.post("/api/parent/screen/good-day")
def screen_good_day(s: Services = Depends(svc), who: str = Depends(require_parent)):
    try:
        r = st.good_day(s.db, s.settings.screen_time, s.now(), who)
    except st.ScreenTimeError as exc:
        _screen_error(exc)
    _payload_cache["at"] = 0.0
    return {"ok": True, **r}


@app.post("/api/parent/screen/adjust")
def screen_adjust(body: AdjustBody, s: Services = Depends(svc), who: str = Depends(require_parent)):
    if body.kid and body.kid not in {k.id for k in s.settings.kids}:
        raise HTTPException(400, "No such kid.")
    try:
        r = st.adjust(s.db, s.now(), who, body.minutes, body.kid, body.scope, body.note)
    except st.ScreenTimeError as exc:
        _screen_error(exc)
    _payload_cache["at"] = 0.0
    return {"ok": True, **r}


@app.post("/api/parent/screen/{entry_id}/undo")
def screen_undo(entry_id: int, s: Services = Depends(svc), who: str = Depends(require_parent)):
    try:
        r = st.undo(s.db, entry_id, s.now(), who)
    except st.ScreenTimeError as exc:
        _screen_error(exc)
    _payload_cache["at"] = 0.0
    return {"ok": True, **r}


@app.post("/api/parent/screen/new-week")
def screen_new_week(s: Services = Depends(svc), who: str = Depends(require_parent)):
    r = st.new_week(s.db, s.settings.screen_time, s.now(), who, last_total=s.screen()["total"])
    _payload_cache["at"] = 0.0
    return {"ok": True, **r}


@app.get("/api/parent/screen/log")
def screen_log(weeks: int = 6, s: Services = Depends(svc), _who: str = Depends(require_parent)):
    return {"weeks": st.history(s.db, s.settings.kids, max(1, min(weeks, 26)))}


# ---------------- photos ----------------

def kid_photo_url(k) -> Optional[str]:
    s = getattr(app.state, "services", None)
    if s is not None and not s.on("portraits"):
        return None
    return f"kids/{k.id}.jpg?v={k.photo}" if k.photo else None


@app.get("/photos/{pid}.jpg")
def photo(pid: str, size: str = "", shape: str = "wide", s: Services = Depends(svc)):
    """shape=wide|tall|wide-hd|tall-hd: cropped for that frame. size=thumb: Settings grid. size=edit: the whole photo, for the focal-point editor."""
    from .photos import SHAPES
    path = s.photos.file_for(pid, shape=size if size in ("thumb", "edit") else shape if shape in SHAPES else "wide")
    if not path:
        raise HTTPException(404)
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "max-age=86400"})


@app.get("/kids/{kid_id}.jpg")
def kid_photo(kid_id: str, s: Services = Depends(svc)):
    if kid_id not in {k.id for k in s.settings.kids}:
        raise HTTPException(404)
    path = KID_PHOTOS / f"{kid_id}.jpg"
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "max-age=604800"})


@app.get("/special/{name}.jpg")
def special_photo(name: str):
    from .special import slug
    path = SPECIAL_PHOTOS / f"{slug(name)}.jpg"
    if not slug(name) or not path.exists():
        raise HTTPException(404)
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "max-age=3600"})


@app.get("/portraits/{key}.jpg")
def portrait_photo(key: str, s: Services = Depends(svc)):
    path = s.portraits.path(key)
    if not path:
        raise HTTPException(404)
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "max-age=604800"})


@app.get("/api/google/callback", response_class=HTMLResponse)
def google_callback(code: str = "", state: str = "", error: str = "", s: Services = Depends(svc)):
    """Google sends the parent back here after they allow Doorpost to use Google Photos and/or Google Tasks."""
    from .google_auth import FEATURE_NAMES, GoogleError
    g = s.google()
    msg = "Google is connected. You can close this tab."
    if error:
        msg = f"Google wasn't connected ({error})."
    elif not g.check_state(state):
        msg = "That sign-in link expired. Go back to Settings and press Connect again."
    else:
        try:
            got = g.finish(code)
            names = " and ".join(FEATURE_NAMES[f] for f in sorted(got))
            msg = f"Google is connected{' for ' + names if names else ''}. You can close this tab."
            threading.Thread(target=s.sync_google_tasks, daemon=True).start()
        except GoogleError as exc:
            msg = str(exc)
    import html as _html
    return (f'<!doctype html><meta name="viewport" content="width=device-width"><title>Google</title>'
            f'<body style="font:18px system-ui;padding:32px;background:#F6F1E7;color:#1F1B16"><p>{_html.escape(msg)}</p>'
            f'<p><a href="/admin">Back to Settings</a></p><script>setTimeout(function(){{ try {{ window.close(); }} catch (e) {{}} }}, 2500);</script></body>')


def require_upload_token(request: Request, s: Services = Depends(svc)) -> None:
    import hmac
    if not hmac.compare_digest(request.headers.get("X-Upload-Token", ""), s.settings.upload_token):
        raise HTTPException(401, "Wrong upload token (see Admin > Photos)")


@app.post("/api/photos/upload", dependencies=[Depends(require_upload_token)])
async def token_upload(file: UploadFile, source: str = "apple-favorites", s: Services = Depends(svc)):
    """Used by scripts/sync-apple-favorites.sh on the Mac."""
    try:
        name = s.photos.save_upload(file.filename or "photo.jpg", await file.read(), sub=source)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True, "saved": name}


class KeepBody(BaseModel):
    keep: list[str]


@app.post("/api/photos/prune", dependencies=[Depends(require_upload_token)])
def token_prune(body: KeepBody, source: str = "apple-favorites", s: Services = Depends(svc)):
    return {"ok": True, "removed": s.photos.prune(source, set(body.keep))}


class FacesBody(BaseModel):
    faces: dict[str, list[float]]


@app.post("/api/photos/faces", dependencies=[Depends(require_upload_token)])
def token_faces(body: FacesBody, source: str = "apple-favorites", s: Services = Depends(svc)):
    """The Mac sends where the faces are in each favorite (file name -> [x, y], fractions across and down).
    That's each photo's starting focal point; one set by hand in Settings wins over it."""
    from .photos import _safe_sub, stored_name
    s.photos.maybe_rescan(0)
    by_name = {p["name"]: pid for pid, p in s.photos._local.items()}
    changed = 0
    for fname, pt in body.faces.items():
        name = f"{_safe_sub(source)}/{stored_name(fname)}"
        if name not in by_name or len(pt) != 2:
            continue
        before = s.photos.focus.get(name)
        if before.get("faces") != [round(min(max(float(v), 0.0), 1.0), 4) for v in pt]:
            s.photos.focus.set(name, faces=pt)
            s.photos.drop_variants(by_name[name])
            changed += 1
    _payload_cache["at"] = 0
    return {"ok": True, "changed": changed}


@app.get("/api/portraits/wanted", dependencies=[Depends(require_upload_token)])
def portraits_wanted(s: Services = Depends(svc)):
    """For the Mac's sync: who needs a birthday portrait, the names Apple Photos may know them by, and what's there now."""
    idx = s.portraits.index()
    names = (s.settings.special or {}).get("portrait_names") or {}
    return [{**p, "photos_name": names.get(p["slug"], ""), "have": idx.get(p["slug"])} for p in people_of(s.settings)]


@app.post("/api/portraits/upload", dependencies=[Depends(require_upload_token)])
async def portraits_upload(file: UploadFile, slug: str, taken: str = "", ref: str = "",
                           fx: float = -1, fy: float = -1, fs: float = -1, cv: int = 0, s: Services = Depends(svc)):
    """The Mac's newest single-face photo of someone (Apple Photos knows who's who). Never replaces one picked by hand."""
    from .portraits import open_image, slug as pslug
    if pslug(slug) not in {p["slug"] for p in people_of(s.settings)}:
        raise HTTPException(404, "No one by that name in Settings.")
    try:
        im = open_image(await file.read())
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    face = (fx, fy, fs) if 0 <= fx <= 1 and 0 <= fy <= 1 and 0 < fs <= 1 else None
    return s.portraits.save(slug, im, "apple", taken=taken, face=face, ref=ref, auto=True, extra={"cv": cv})


@app.post("/api/lists/sync", dependencies=[Depends(require_upload_token)])
def lists_sync(body: dict, s: Services = Depends(svc)):
    """The Mac's Reminders helper checks in here (see docs/lists.md)."""
    r = s.lists.sync(body, s.now())
    if body.get("items") or body.get("applied"):
        _payload_cache["at"] = 0
    return r


@app.get("/healthz")
def health(s: Services = Depends(svc)):
    return {"ok": True, "demo": s.settings.demo, "addon": s.settings.addon,
            "calendars": list(s.calendar.calendars), "calendar_errors": s.calendar.errors}


# ---------------- admin panel ----------------

from .admin import router as admin_router  # noqa: E402  (needs the helpers above)
from .admin_providers import router as providers_router  # noqa: E402
from .modules_api import make_router as modules_router  # noqa: E402  (Settings > Modules)

app.include_router(admin_router)
app.include_router(providers_router)
app.include_router(modules_router(require_admin, svc))

from . import storage as storage_mod  # noqa: E402  (Settings > Overview storage card, frame heartbeats)

for _r in storage_mod.make_routers(require_admin, svc):
    app.include_router(_r)

from .art_packs_api import public as art_public, router as art_router  # noqa: E402

app.include_router(art_router)
app.include_router(art_public)

from .email_api import admin as email_admin_router, public as email_public_router  # noqa: E402  (Settings > Email updates)
app.include_router(email_admin_router)
app.include_router(email_public_router)
from .bible_api import router as bible_router  # noqa: E402  (Settings > Special days > Bible translation)

app.include_router(bible_router)

from . import admin_looks_api  # noqa: E402  (Settings look: /admin and /parent in a frame look, app/admin_looks.py)

app.include_router(admin_looks_api.make_router(require_admin, svc))


# ---------------- pages ----------------

def _asset_version() -> str:
    """Changes whenever any file under web/ changes, so the frame never runs stale JS/CSS."""
    import hashlib
    from . import overlay
    h = hashlib.sha1()
    for d in [WEB_DIR] + ([overlay.web_dir()] if overlay.web_dir() else []):   # local/web/ too (app/overlay.py)
        for p in sorted(d.rglob("*")):
            if p.is_file():
                h.update(f"{d.name}/{p.relative_to(d)}:{p.stat().st_mtime_ns}".encode())
    return h.hexdigest()[:10]


def _app_name(demo: bool) -> str:
    """app_name from frame.yaml (local/config first): what Settings calls itself. Empty: the default."""
    from .config import effective_config
    try:
        return str(effective_config(demo).get("app_name") or "").strip()[:40]
    except Exception:  # noqa: BLE001  (a page never fails over its title)
        return ""


def _page(name: str, request: Request) -> HTMLResponse:
    v = _asset_version()
    html = (WEB_DIR / name).read_text()
    for asset in ("static/css/frame.css", "static/js/icons.js", "static/js/app.js", "static/js/admin.js",
                  "static/css/kids.css", "static/js/kids.js", "static/css/modules.css", "static/js/looks.js", "static/js/look-options.js",
                  "static/css/admin-look.css", "static/js/admin-look.js", "static/js/email-admin.js"):
        html = html.replace(f'"{asset}"', f'"{asset}?v={v}"')
    html = html.replace('"art.js"', f'"art.js?v={request.app.state.services.packs.signature}"')  # the art packs' drawings
    html = html.replace('"themes.css"', f'"themes.css?v={_themes_version(request.app.state.services)}"')  # the looks (app/themes.py)
    html = html.replace('"themes.js"', f'"themes.js?v={_themes_version(request.app.state.services)}"')
    fam = html_escape(request.app.state.services.settings.family_name or "Our Family")   # the page title and header
    html = html.replace("<title>Our Family</title>", f"<title>{fam}</title>").replace('<div class="script">Our Family</div>', f'<div class="script">{fam}</div>')
    app_name = _app_name(request.app.state.services.settings.demo)   # Settings' own name (app_name in frame.yaml)
    if app_name:
        html = html.replace("<title>Doorpost · ", f"<title>{html_escape(app_name)} · ").replace(
            '<div class="script">Doorpost</div>', f'<div class="script">{html_escape(app_name)}</div>')
    # All links in the pages are relative. Inside the Home Assistant sidebar the app lives
    # under /api/hassio_ingress/<token>/, which HA tells us in X-Ingress-Path.
    base = (request.headers.get("X-Ingress-Path", "") if via_ingress(request, request.app.state.services) else "")
    html = html.replace("<head>", f'<head>\n<base href="{base}/">', 1)
    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})


def _themes_version(s: Services) -> str:
    return themes.signature(s.packs)


@app.get("/themes.css")
def themes_css(request: Request, s: Services = Depends(svc)):
    """Every enabled look's CSS and the Match-the-look picture rules, one file (themes/<id>/, app/themes.py)."""
    tag = f'"{_themes_version(s)}"'
    if request.headers.get("if-none-match") == tag:
        return Response(status_code=304, headers={"ETag": tag})
    return Response(themes.css(s.packs), media_type="text/css; charset=utf-8", headers={"ETag": tag, "Cache-Control": "no-cache"})


@app.get("/themes.js")
def themes_js(request: Request, s: Services = Depends(svc)):
    """Every enabled look's theme.js, one file (themes/<id>/theme.js; the API is web/js/looks.js)."""
    tag = f'"{_themes_version(s)}"'
    if request.headers.get("if-none-match") == tag:
        return Response(status_code=304, headers={"ETag": tag})
    return Response(themes.js(s.packs), media_type="application/javascript; charset=utf-8", headers={"ETag": tag, "Cache-Control": "no-cache"})


@app.get("/themes/{tid}/{rel:path}")
def theme_file(tid: str, rel: str):
    """A font or picture a look's theme.css points at."""
    hit = themes.theme_file(tid, rel)
    if not hit:
        raise HTTPException(404)
    return FileResponse(hit[0], media_type=hit[1], headers={"X-Content-Type-Options": "nosniff"})


@app.get("/")
def home_page(request: Request):
    # The Home Assistant sidebar opens the admin panel; the frame itself opens the frame.
    if via_ingress(request, request.app.state.services):
        return _look_page("admin.html", request, "admin")
    return _page("index.html", request)


@app.get("/frame")
def frame_page(request: Request):
    return _page("index.html", request)


@app.get("/frame/{fid}")
def frame_page_for(fid: str, request: Request):
    """A frame opened as a particular profile, e.g. /frame/kids (Settings > Frames shows each address)."""
    return _page("index.html", request)


@app.get("/parent")
def parent_page(request: Request):
    return _look_page("parent.html", request, "parent")


@app.get("/e/{token}")
def email_link_page(token: str, request: Request):
    """A quick approve button in the daily email. The page approves with a POST from its script
    (app/email_api.py), never on this GET: mail services open links on their own to scan them."""
    r = _look_page("email.html", request, "parent")
    r.headers["Referrer-Policy"] = "no-referrer"
    r.headers["X-Robots-Tag"] = "noindex"
    return r


ADMIN_PAGES = ("overview", "modules", "frames", "calendars", "special-days", "art-packs", "photos", "family", "kids", "chores", "lists", "screen-time", "email-updates", "house", "pins")


def _look_page(name: str, request: Request, page: str) -> HTMLResponse:
    """/admin and /parent, dressed in the Settings look (app/admin_looks_api.py)."""
    r = _page(name, request)
    return HTMLResponse(admin_looks_api.dress(r.body.decode(), request, page), headers={"Cache-Control": "no-cache"})


@app.get("/admin")
def admin_page(request: Request):
    return _look_page("admin.html", request, "admin")


@app.get("/admin/{section}")
def admin_section(section: str, request: Request):
    """Each Settings section has its own address; the page script shows the one in the URL."""
    if section not in ADMIN_PAGES:
        raise HTTPException(404)
    return _look_page("admin.html", request, "admin")


class _Static(StaticFiles):
    """web/, with the private overlay's local/web/ files winning over the same path (app/overlay.py)."""

    def lookup_path(self, path: str):
        from . import overlay
        lw = overlay.web_dir()
        self.all_directories = ([lw] if lw else []) + [WEB_DIR]
        return super().lookup_path(path)


app.mount("/static", _Static(directory=WEB_DIR), name="static")

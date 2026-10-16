"""A small read-only CalDAV client for private calendars (Apple iCloud, Fastmail, Nextcloud).

Three steps, all plain HTTP with httpx:
  1. Ask the server who we are (current-user-principal).
  2. Ask the principal where its calendars live (calendar-home-set).
  3. List the calendars there, then fetch events for a date window with a
     calendar-query REPORT.

The events come back as iCalendar text, so they are joined into one VCALENDAR
and go through the same parser and repeat-expansion as an .ics address.

Redirects are followed by hand so the Apple ID and app-specific password are
sent again on the new host (iCloud moves you to a pNN-caldav.icloud.com server,
and httpx drops the login on a cross-host redirect by design).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import httpx

ICLOUD_SERVER = "https://caldav.icloud.com"

NS = {"d": "DAV:", "c": "urn:ietf:params:xml:ns:caldav", "a": "http://apple.com/ns/ical/", "cs": "http://calendarserver.org/ns/"}

_PRINCIPAL = """<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:"><d:prop><d:current-user-principal/></d:prop></d:propfind>"""

_HOME = """<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
<d:prop><c:calendar-home-set/></d:prop></d:propfind>"""

_LIST = """<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav" xmlns:a="http://apple.com/ns/ical/">
<d:prop><d:resourcetype/><d:displayname/><a:calendar-color/><c:supported-calendar-component-set/></d:prop></d:propfind>"""

_QUERY = """<?xml version="1.0" encoding="utf-8"?>
<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
<d:prop><c:calendar-data/></d:prop>
<c:filter><c:comp-filter name="VCALENDAR"><c:comp-filter name="VEVENT">
<c:time-range start="{start}" end="{end}"/>
</c:comp-filter></c:comp-filter></c:filter></c:calendar-query>"""


def make_http() -> httpx.Client:
    """One place to build the HTTP client, so tests can swap in a fake server."""
    return httpx.Client(timeout=30, follow_redirects=True)


class CalDAVError(Exception):
    """A plain-English problem to show in Settings."""


def normalize_server(server: str) -> str:
    server = (server or "").strip() or ICLOUD_SERVER
    if server.startswith("webcal://"):
        server = "https://" + server[len("webcal://"):]
    if not server.startswith(("http://", "https://")):
        server = "https://" + server
    return server.rstrip("/") + "/"


class CalDAVClient:
    def __init__(self, server: str, username: str, password: str, http: Optional[httpx.Client] = None):
        if not username or not password:
            raise CalDAVError("Type the sign-in name and the app-specific password first.")
        self.server = normalize_server(server)
        self.auth = httpx.BasicAuth(username, password)
        self.http = http or make_http()

    # ---------- plumbing ----------

    def _request(self, method: str, url: str, body: str, depth: str) -> tuple[str, ET.Element]:
        headers = {"Depth": depth, "Content-Type": "application/xml; charset=utf-8"}
        for _ in range(6):
            resp = self.http.request(method, url, content=body.encode(), headers=headers, auth=self.auth,
                                     follow_redirects=False)
            if resp.status_code in (301, 302, 307, 308) and resp.headers.get("location"):
                url = urljoin(url, resp.headers["location"])
                continue
            break
        else:
            raise CalDAVError("The server kept redirecting. Check the server address.")
        if resp.status_code == 401:
            raise CalDAVError("Sign-in failed. Check the email and use an app-specific password, not your normal one.")
        if resp.status_code == 403:
            raise CalDAVError("The server said no (403). The password may have been revoked.")
        if resp.status_code == 404:
            raise CalDAVError("Not found (404). Check the server address.")
        if resp.status_code != 207:
            raise CalDAVError(f"The server answered {resp.status_code}, not a calendar list. Check the server address.")
        try:
            return url, ET.fromstring(resp.content)
        except ET.ParseError as exc:
            raise CalDAVError(f"The server's answer could not be read ({exc}).") from None

    @staticmethod
    def _href(root: ET.Element, prop: str) -> Optional[str]:
        el = root.find(f".//{prop}/d:href", NS)
        return el.text.strip() if el is not None and el.text else None

    # ---------- discovery ----------

    def principal(self) -> str:
        for start in (self.server, urljoin(self.server, "/.well-known/caldav")):
            try:
                url, root = self._request("PROPFIND", start, _PRINCIPAL, "0")
            except CalDAVError:
                if start == self.server:
                    continue  # some servers only answer at the well-known address
                raise
            href = self._href(root, "d:current-user-principal")
            if href:
                return urljoin(url, href)
        raise CalDAVError("The server did not say whose calendars these are. Check the server address.")

    def calendar_home(self) -> str:
        principal = self.principal()
        url, root = self._request("PROPFIND", principal, _HOME, "0")
        href = self._href(root, "c:calendar-home-set")
        if not href:
            raise CalDAVError("The server did not say where the calendars are.")
        return urljoin(url, href)

    def calendars(self) -> list[dict]:
        """Every calendar that can hold events: [{url, name, color}]."""
        home = self.calendar_home()
        url, root = self._request("PROPFIND", home, _LIST, "1")
        out = []
        for resp in root.findall("d:response", NS):
            href = resp.findtext("d:href", default="", namespaces=NS).strip()
            prop = _ok_prop(resp)
            if prop is None or prop.find("d:resourcetype/c:calendar", NS) is None:
                continue
            comps = prop.find("c:supported-calendar-component-set", NS)
            if comps is not None and len(comps) and not any(c.get("name") == "VEVENT" for c in comps):
                continue  # a Reminders/tasks list, not a calendar
            name = (prop.findtext("d:displayname", default="", namespaces=NS) or "").strip()
            color = (prop.findtext("a:calendar-color", default="", namespaces=NS) or "").strip()[:7]
            out.append({"url": urljoin(url, href), "name": name or href.rstrip("/").rsplit("/", 1)[-1],
                        "color": color if len(color) == 7 and color.startswith("#") else ""})
        out.sort(key=lambda c: c["name"].lower())
        return out

    # ---------- events ----------

    def fetch(self, calendar_url: str, start: datetime, end: datetime) -> bytes:
        """Events touching [start, end) as one iCalendar file (bytes)."""
        body = _QUERY.format(start=_utc(start), end=_utc(end))
        _url, root = self._request("REPORT", calendar_url, body, "1")
        return join_ics(el.text or "" for el in root.iterfind(".//c:calendar-data", NS))


def _ok_prop(resp: ET.Element) -> Optional[ET.Element]:
    for ps in resp.findall("d:propstat", NS):
        status = ps.findtext("d:status", default="", namespaces=NS)
        if " 200 " in f" {status} ":
            return ps.find("d:prop", NS)
    return None


def _utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def join_ics(parts) -> bytes:
    """Many one-event VCALENDARs into one, keeping each time zone once."""
    import icalendar
    out = icalendar.Calendar()
    out.add("prodid", "-//Doorpost//CalDAV//EN")
    out.add("version", "2.0")
    zones: dict[str, object] = {}
    events = []
    for text in parts:
        text = text.strip()
        if not text:
            continue
        cal = icalendar.Calendar.from_ical(text)
        for comp in cal.subcomponents:
            if comp.name == "VTIMEZONE":
                zones.setdefault(str(comp.get("TZID", "")), comp)
            else:
                events.append(comp)
    for comp in [*zones.values(), *events]:
        out.add_component(comp)
    return out.to_ical()

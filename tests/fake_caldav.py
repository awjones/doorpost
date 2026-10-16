"""A fake CalDAV server for tests (an httpx MockTransport, no network).

It behaves like iCloud: the first PROPFIND on caldav.icloud.com redirects to a
numbered partition host, the principal and home live under a user id, and the
home holds two calendars plus one Reminders list (tasks only).
"""
from __future__ import annotations

import base64

import httpx

USER, PASSWORD = "parent@example.com", "abcd-efgh-ijkl-mnop"
HOST = "https://p01-caldav.example.com"

FAMILY_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VTIMEZONE
TZID:America/New_York
BEGIN:STANDARD
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
TZOFFSETFROM:-0400
TZOFFSETTO:-0500
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
TZOFFSETFROM:-0500
TZOFFSETTO:-0400
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
UID:piano-1
DTSTART;TZID=America/New_York:20260903T160000
DTEND;TZID=America/New_York:20260903T163000
RRULE:FREQ=WEEKLY;BYDAY=TH
SUMMARY:Piano lesson (Child 1)
END:VEVENT
END:VCALENDAR
"""

PICNIC_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
UID:picnic-1
DTSTART;VALUE=DATE:20261017
DTEND;VALUE=DATE:20261018
SUMMARY:Park picnic
END:VEVENT
END:VCALENDAR
"""


def _ms(*responses: str) -> str:
    return ('<?xml version="1.0"?><d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav" '
            'xmlns:a="http://apple.com/ns/ical/">' + "".join(responses) + "</d:multistatus>")


def _resp(href: str, prop: str) -> str:
    return (f"<d:response><d:href>{href}</d:href><d:propstat><d:prop>{prop}</d:prop>"
            "<d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>")


def _cal(href, name, color, comps):
    comp = "".join(f'<c:comp name="{c}"/>' for c in comps)
    return _resp(href, f"<d:resourcetype><d:collection/><c:calendar/></d:resourcetype><d:displayname>{name}</d:displayname>"
                       f"<a:calendar-color>{color}</a:calendar-color><c:supported-calendar-component-set>{comp}</c:supported-calendar-component-set>")


class FakeCalDAV:
    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.down = False

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.down:
            return httpx.Response(503)
        auth = request.headers.get("authorization", "")
        if auth != "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode():
            return httpx.Response(401)
        url, method = str(request.url), request.method
        if url.startswith("https://caldav.icloud.com"):
            return httpx.Response(301, headers={"location": HOST + request.url.path})
        path = request.url.path
        if method == "PROPFIND" and path == "/":
            return httpx.Response(207, text=_ms(_resp("/", "<d:current-user-principal><d:href>/123/principal/</d:href></d:current-user-principal>")))
        if method == "PROPFIND" and path == "/123/principal/":
            return httpx.Response(207, text=_ms(_resp(path, f"<c:calendar-home-set><d:href>{HOST}/123/calendars/</d:href></c:calendar-home-set>")))
        if method == "PROPFIND" and path == "/123/calendars/":
            assert request.headers["depth"] == "1"
            return httpx.Response(207, text=_ms(
                _resp(path, "<d:resourcetype><d:collection/></d:resourcetype>"),
                _cal("/123/calendars/home/", "Home", "#2E4A7AFF", ["VEVENT"]),
                _cal("/123/calendars/tasks/", "Reminders", "#FF0000FF", ["VTODO"]),
                _cal("/123/calendars/kids/", "Kids", "#2F6B5EFF", ["VEVENT", "VTODO"]),
            ))
        if method == "REPORT" and path == "/123/calendars/home/":
            body = request.content.decode()
            assert "time-range" in body and "VEVENT" in body
            return httpx.Response(207, text=_ms(
                f'<d:response><d:href>{path}piano.ics</d:href><d:propstat><d:prop><c:calendar-data>{FAMILY_ICS}</c:calendar-data></d:prop>'
                "<d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>",
                f'<d:response><d:href>{path}picnic.ics</d:href><d:propstat><d:prop><c:calendar-data>{PICNIC_ICS}</c:calendar-data></d:prop>'
                "<d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>",
            ))
        return httpx.Response(404)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self), follow_redirects=True)

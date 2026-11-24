"""A best guess at the way a ship sails between two points without crossing land (the cruise ship tracker's map).

The land is the same Natural Earth outline the frame draws (web/img/caribbean.svg, in map units:
x=(lon+98)*cos22*30, y=(33-lat)*30). The ship's way is the shortest line through a hand-picked set
of open-water points (the straits and passages cruise ships use: Florida Straits, the Providence
Channels, Crooked Island and Windward Passages, the Yucatán Channel, and so on), using only legs
that don't cross land. A port sits on the shore, so the last few miles into a port aren't checked.
"""
from __future__ import annotations

import heapq
import logging
import math
import re
from functools import lru_cache
from typing import Optional

from .config import WEB_DIR

log = logging.getLogger("family_frame.searoute")

K = math.cos(math.radians(22))

# (lat, lon) in open water. Any that turn out to be on land are dropped when the map loads.
WAYPOINTS = [
    # Florida and the Gulf side
    (25.75, -79.95), (25.3, -79.9), (24.9, -80.2), (24.35, -81.0), (24.15, -82.0), (23.9, -83.2), (23.4, -84.3), (24.6, -84.5),
    # Bahamas: Northwest and Northeast Providence Channels, Exuma Sound, down the east side to the Crooked Island Passage
    (26.15, -79.2), (26.05, -78.5), (25.95, -77.85), (25.8, -77.1), (25.75, -76.55), (25.3, -76.05), (24.6, -75.75), (24.1, -76.2),
    (23.95, -75.05), (23.3, -74.55), (22.75, -74.45), (22.2, -74.25), (21.4, -73.95), (21.6, -72.6), (21.3, -71.4),
    # Old Bahama and Santaren Channels (north coast of Cuba)
    (23.6, -79.55), (23.2, -78.9), (22.7, -77.9), (22.3, -76.9),
    # Windward Passage and south of Cuba to Jamaica and the Caymans
    (20.6, -73.95), (20.0, -73.85), (19.5, -74.3), (19.0, -75.3), (18.75, -76.4), (18.7, -77.2), (18.75, -77.9), (18.9, -78.7),
    (19.2, -79.6), (19.55, -80.4), (19.35, -81.6), (19.0, -81.0), (18.6, -80.0), (17.6, -77.0), (17.2, -76.0),
    # Toward Cozumel and the Yucatán Channel
    (19.7, -83.0), (20.0, -84.6), (20.1, -86.3), (20.25, -86.75), (21.0, -86.2), (21.7, -85.9), (22.4, -85.6),
    # North of Hispaniola, Puerto Rico and the east (so other trips route too)
    (20.3, -72.0), (20.2, -70.5), (19.9, -69.0), (18.9, -67.9), (18.4, -67.6), (18.75, -66.2), (17.7, -66.0), (17.6, -64.9),
    (18.6, -64.6), (17.0, -68.5), (16.8, -71.0), (17.2, -73.5), (16.5, -78.0), (17.0, -82.0), (17.5, -85.0), (16.8, -86.6),
]

# Shallows a cruise ship goes around, which the land outline doesn't show (lines, lat/lon).
SHOALS = [
    [(25.25, -80.35), (24.95, -80.6), (24.7, -81.0), (24.6, -81.6), (24.55, -82.0)],      # Florida Keys
    [(25.75, -79.28), (25.55, -78.8), (25.45, -78.2), (25.6, -77.85)],                      # Bimini to the Berry Islands (Great Bahama Bank)
    [(25.75, -79.28), (25.0, -79.3), (24.2, -79.45), (23.6, -79.0)],                        # the bank's west edge
]

PORT_TRIM = 5.0     # map units (~18 km) at a port end that may cross the shore
SHIP_TRIM = 1.2     # ~4 km at the ship's end (a position near the coast)


def xy(lat: float, lon: float) -> tuple:
    return ((lon + 98.0) * K * 30.0, (33.0 - lat) * 30.0)


def latlon(p: tuple) -> tuple:
    return (33.0 - p[1] / 30.0, p[0] / (K * 30.0) - 98.0)


@lru_cache(maxsize=1)
def _land() -> list:
    """The land rings, each [(x, y)...] with its bounding box."""
    try:
        d = re.search(r'\sd="([^"]+)"', (WEB_DIR / "img" / "caribbean.svg").read_text()).group(1)
    except (OSError, AttributeError):
        log.warning("searoute: no land outline; routes will be straight lines")
        return []
    rings = []
    for line in SHOALS:   # a there-and-back ring: blocks crossing, has no inside
        pts = [xy(la, lo) for la, lo in line]
        pts = pts + pts[-2:0:-1]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        rings.append((pts, (min(xs), min(ys), max(xs), max(ys))))
    for part in d.split("M")[1:]:
        pts = [tuple(map(float, xy_.split(","))) for xy_ in part.replace("Z", " ").split()]
        if len(pts) >= 3:
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            rings.append((pts, (min(xs), min(ys), max(xs), max(ys))))
    return rings


def on_land(p: tuple) -> bool:
    x, y = p
    for pts, (x0, y0, x1, y1) in _land():
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        inside, j = False, len(pts) - 1
        for i in range(len(pts)):
            xi, yi = pts[i]
            xj, yj = pts[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
        if inside:
            return True
    return False


def _cross(a, b, c, d) -> bool:
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return (o(a, b, c) > 0) != (o(a, b, d) > 0) and (o(c, d, a) > 0) != (o(c, d, b) > 0)


def clear(a: tuple, b: tuple, trim_a: float = 0.0, trim_b: float = 0.0) -> bool:
    """True when the leg a→b doesn't cross land (ignoring the first trim_a and last trim_b map units)."""
    L = math.dist(a, b)
    if L <= trim_a + trim_b:
        return True
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    a2, b2 = (a[0] + ux * trim_a, a[1] + uy * trim_a), (b[0] - ux * trim_b, b[1] - uy * trim_b)
    bx0, by0, bx1, by1 = min(a2[0], b2[0]), min(a2[1], b2[1]), max(a2[0], b2[0]), max(a2[1], b2[1])
    for pts, (x0, y0, x1, y1) in _land():
        if x1 < bx0 or x0 > bx1 or y1 < by0 or y0 > by1:
            continue
        for i in range(len(pts)):
            if _cross(a2, b2, pts[i - 1], pts[i]):
                return False
    return True


@lru_cache(maxsize=1)
def _graph() -> tuple:
    nodes = [xy(la, lo) for la, lo in WAYPOINTS]
    wet = [p for p in nodes if not on_land(p)]
    if len(wet) < len(nodes):
        log.info("searoute: %d waypoints on land, dropped", len(nodes) - len(wet))
    edges = {i: [] for i in range(len(wet))}
    for i in range(len(wet)):
        for j in range(i + 1, len(wet)):
            if math.dist(wet[i], wet[j]) < 260 and clear(wet[i], wet[j]):
                d = math.dist(wet[i], wet[j])
                edges[i].append((j, d))
                edges[j].append((i, d))
    return wet, edges


@lru_cache(maxsize=256)
def route(a: tuple, b: tuple, trim_a: float = SHIP_TRIM, trim_b: float = PORT_TRIM) -> list:
    """The way from a to b by sea, as a list of map points starting with a and ending with b."""
    a, b = (round(a[0], 1), round(a[1], 1)), (round(b[0], 1), round(b[1], 1))
    if not _land() or clear(a, b, trim_a, trim_b):
        return [a, b]
    wet, edges = _graph()
    n = len(wet)
    A, B = n, n + 1
    links = {A: [], B: []}
    for i, p in enumerate(wet):
        if clear(a, p, trim_a, 0):
            links[A].append((i, math.dist(a, p)))
        if clear(p, b, 0, trim_b):
            links[i] = [(B, math.dist(p, b))]
    dist, prev, heap = {A: 0.0}, {}, [(0.0, A)]
    while heap:
        d, u = heapq.heappop(heap)
        if u == B:
            break
        if d > dist.get(u, 1e18):
            continue
        for v, w in (links[A] if u == A else edges.get(u, []) + links.get(u, [])):
            nd = d + w
            if nd < dist.get(v, 1e18):
                dist[v], prev[v] = nd, u
                heapq.heappush(heap, (nd, v))
    if B not in prev:
        return [a, b]
    path, u = [b], B
    while u in prev:
        u = prev[u]
        path.append(a if u == A else wet[u])
    return path[::-1]


def length(path: list) -> float:
    return sum(math.dist(path[i - 1], path[i]) for i in range(1, len(path)))


def along(path: list, f: float) -> tuple:
    """The point a fraction f (0..1) of the way along the path."""
    want, i = max(0.0, min(1.0, f)) * length(path), 1
    while i < len(path):
        seg = math.dist(path[i - 1], path[i])
        if want <= seg or i == len(path) - 1:
            k = min(1.0, want / seg) if seg else 1.0
            return (path[i - 1][0] + (path[i][0] - path[i - 1][0]) * k, path[i - 1][1] + (path[i][1] - path[i - 1][1]) * k)
        want -= seg
        i += 1
    return path[-1]

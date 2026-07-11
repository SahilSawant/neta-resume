"""Load the 543 Lok Sabha constituencies (bundled boundary set) into the DB + build nearest-neighbour edges.

Reads web/src/data/pc-boundaries.json (a FeatureCollection of MultiPolygons with pc_id/st_name/pc_name/…),
upserts a canonical `constituency` row per PC with a rough centroid, then rebuilds `constituency_adjacency`
as each PC's K nearest neighbours by centroid distance (same-state preferred). Reference geography, so no
per-row provenance. Idempotent: upsert on pc_id, adjacency rebuilt per constituency.

    uv run neta constituencies
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from sqlalchemy import text

from neta_core.db.engine import session_scope

_BOUNDARIES = Path(__file__).resolve().parents[4] / "web" / "src" / "data" / "pc-boundaries.json"
_NEAREST_K = 6
_NONALNUM = re.compile(r"[^A-Za-z0-9]+")


def normalize_pc_name(name: str) -> str:
    """Upper + non-alphanumerics folded to single spaces, so 'Kangra' / 'KANGRA' and
    'NAINITAL-UDHAMSINGH NAGAR' / 'Nainital-Udhamsingh Nagar' collapse to one key."""
    return _NONALNUM.sub(" ", name or "").strip().upper()


def _iter_coords(geometry: dict):
    """Yield every (lng, lat) vertex of a Polygon / MultiPolygon geometry."""
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    rings = coords if gtype == "Polygon" else [ring for poly in coords for ring in poly]
    for ring in rings:
        for pt in ring:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                yield float(pt[0]), float(pt[1])


def _centroid(geometry: dict) -> tuple[float | None, float | None]:
    """Rough centroid: mean of all boundary vertices. Good enough for nearest-neighbour ranking."""
    xs, ys, n = 0.0, 0.0, 0
    for lng, lat in _iter_coords(geometry):
        xs += lng
        ys += lat
        n += 1
    return (ys / n, xs / n) if n else (None, None)  # (lat, lng)


def _haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def run() -> None:
    data = json.loads(_BOUNDARIES.read_text())
    features = data.get("features", data)
    print(f"[constituencies] {len(features)} features from {_BOUNDARIES.name}")

    rows = []
    for f in features:
        p = f.get("properties", {})
        pc_id = p.get("pc_id")
        pc_name = p.get("pc_name")
        state = (p.get("st_name") or "").strip().upper()
        if pc_id is None or not pc_name or not state:
            continue
        lat, lng = _centroid(f.get("geometry") or {})
        rows.append({
            "pc_id": int(pc_id),
            "pc_no": p.get("pc_no"),
            "state_name": state,
            "pc_name": pc_name.strip(),
            "pc_name_normalized": normalize_pc_name(pc_name),
            "pc_name_hi": p.get("pc_name_hi"),
            "pc_category": p.get("pc_category"),
            "wikidata_qid": p.get("wikidata_qid"),
            "center_lat": lat,
            "center_lng": lng,
        })

    with session_scope() as s:
        for r in rows:
            s.execute(
                text("""
                INSERT INTO constituency (pc_id, pc_no, state_name, pc_name, pc_name_normalized,
                                          pc_name_hi, pc_category, wikidata_qid, center_lat, center_lng)
                VALUES (:pc_id, :pc_no, :state_name, :pc_name, :pc_name_normalized,
                        :pc_name_hi, :pc_category, :wikidata_qid, :center_lat, :center_lng)
                ON CONFLICT (pc_id) DO UPDATE SET
                    pc_no = EXCLUDED.pc_no, state_name = EXCLUDED.state_name, pc_name = EXCLUDED.pc_name,
                    pc_name_normalized = EXCLUDED.pc_name_normalized, pc_name_hi = EXCLUDED.pc_name_hi,
                    pc_category = EXCLUDED.pc_category, wikidata_qid = EXCLUDED.wikidata_qid,
                    center_lat = EXCLUDED.center_lat, center_lng = EXCLUDED.center_lng
                """),
                r,
            )
        # id lookup for adjacency
        id_by_pc = {pc: cid for pc, cid in s.execute(text("SELECT pc_id, id FROM constituency")).all()}
        located = [r for r in rows if r["center_lat"] is not None]

        edges = 0
        for r in located:
            here = (r["center_lat"], r["center_lng"])
            scored = [
                (_haversine(here, (o["center_lat"], o["center_lng"])), o["state_name"] == r["state_name"], o)
                for o in located if o["pc_id"] != r["pc_id"]
            ]
            # same-state first, then nearest overall
            scored.sort(key=lambda t: (not t[1], t[0]))
            neighbours = scored[:_NEAREST_K]
            cid = id_by_pc[r["pc_id"]]
            s.execute(text("DELETE FROM constituency_adjacency WHERE constituency_id = :c"), {"c": cid})
            for rank, (_dist, _same, o) in enumerate(neighbours, start=1):
                s.execute(
                    text("INSERT INTO constituency_adjacency (constituency_id, neighbor_id, rank) "
                         "VALUES (:c, :n, :r) ON CONFLICT DO NOTHING"),
                    {"c": cid, "n": id_by_pc[o["pc_id"]], "r": rank},
                )
                edges += 1

    print(f"[constituencies] upserted {len(rows)} constituencies, {edges} adjacency edges "
          f"({len(rows) - len(located)} without geometry)")

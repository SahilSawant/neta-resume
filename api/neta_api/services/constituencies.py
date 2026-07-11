"""Constituency Report Card — read-time aggregate.

v1 draws entirely on EXISTING neta data: each Lok Sabha constituency is joined to its sitting MP (via a
normalised name+state match to the current-term office_term) and that MP's declared facts become the
constituency's "representation" indicators — declared assets, pending criminal cases, House attendance,
questions asked — each compared to the state average, the national average, and a percentile across all
constituencies. Descriptive only (never a value judgment); "missing ≠ zero" → unmatched/unreported render null.

The 4-indicator base is computed for ALL 543 constituencies in one query (cheap) so averages/percentiles are
a simple pass in Python. External socio-economic indicators (literacy/roads/schemes) land in Phase 2 via
constituency_metric and are merged here later.
"""

from __future__ import annotations

from statistics import mean

from sqlalchemy import text
from sqlalchemy.orm import Session

# Indicators whose value is "more is simply more" — we report a neutral percentile, no better/worse framing.
_NUMERIC = ("assets", "pending_cases", "attendance_pct", "questions")

_BASE_SQL = """
SELECT c.id AS cid, c.pc_id, c.pc_no, c.pc_name, c.pc_name_hi, c.state_name, c.pc_category, c.wikidata_qid,
       mp.person_id, p.display_name AS mp_name,
       (SELECT pt.canonical_name FROM party_affiliation pa JOIN party pt ON pt.id = pa.party_id
        WHERE pa.person_id = mp.person_id AND pa.is_current LIMIT 1) AS party,
       la.total_assets AS assets,
       (SELECT count(*) FROM criminal_case cc WHERE cc.affidavit_id = la.aff_id AND NOT cc.is_convicted)
         AS pending_cases,
       (SELECT count(*) FROM criminal_case cc WHERE cc.affidavit_id = la.aff_id AND cc.is_convicted)
         AS convictions,
       mp.attendance_pct,
       (SELECT pa2.questions_asked FROM parliamentary_activity pa2
        JOIN term_cycle tc2 ON tc2.id = pa2.term_cycle_id
        WHERE pa2.person_id = mp.person_id AND tc2.number = :cyc LIMIT 1) AS questions
FROM constituency c
LEFT JOIN LATERAL (
    SELECT ot.id AS ot_id, ot.person_id, ot.attendance_pct
    FROM office_term ot
    JOIN term_cycle tc ON tc.id = ot.term_cycle_id
    JOIN house h ON h.id = tc.house_id
    WHERE h.code = 'LS' AND tc.number = :cyc
      AND nr_norm(ot.constituency) = c.pc_name_normalized
      AND nr_canon_state(ot.ls_state_code) = nr_canon_state(c.state_name)
    ORDER BY ot.id LIMIT 1
) mp ON true
LEFT JOIN person p ON p.id = mp.person_id
LEFT JOIN LATERAL (
    SELECT a.id AS aff_id, a.total_assets
    FROM affidavit a WHERE a.person_id = mp.person_id
    ORDER BY a.filed_year DESC NULLS LAST, a.id DESC LIMIT 1
) la ON true
ORDER BY c.pc_id
"""


def _num(v):
    return float(v) if v is not None else None


def _row_metrics(r) -> dict:
    return {
        "assets": _num(r.assets),
        "pending_cases": _num(r.pending_cases),
        "attendance_pct": _num(r.attendance_pct),
        "questions": _num(r.questions),
    }


def _percentile(values: list[float], v: float) -> float:
    """Share of constituencies (with data) whose value is ≤ v, as 0–100. Neutral — not a ranking of merit."""
    if not values:
        return 0.0
    return round(100.0 * sum(1 for x in values if x <= v) / len(values), 1)


def list_constituencies(db: Session) -> list[dict]:
    rows = db.execute(
        text("SELECT pc_id, pc_name, pc_name_hi, state_name, pc_category FROM constituency ORDER BY state_name, pc_name")
    ).all()
    return [
        {"pc_id": r.pc_id, "pc_name": r.pc_name, "pc_name_hi": r.pc_name_hi,
         "state_name": r.state_name, "pc_category": r.pc_category}
        for r in rows
    ]


def report_card(db: Session, pc_id: int, cycle_number: int = 18) -> dict | None:
    rows = db.execute(text(_BASE_SQL), {"cyc": cycle_number}).all()
    by_pc = {r.pc_id: r for r in rows}
    target = by_pc.get(pc_id)
    if target is None:
        return None

    metrics_by_cid = {r.cid: _row_metrics(r) for r in rows}
    state_of = {r.cid: r.state_name for r in rows}
    tgt_m = metrics_by_cid[target.cid]

    # national + state pools per indicator (non-null only)
    def pool(indicator: str, state: str | None = None) -> list[float]:
        return [m[indicator] for cid, m in metrics_by_cid.items()
                if m[indicator] is not None and (state is None or state_of[cid] == state)]

    comparisons = {}
    for ind in _NUMERIC:
        v = tgt_m[ind]
        nat = pool(ind)
        st = pool(ind, target.state_name)
        comparisons[ind] = {
            "value": v,
            "state_avg": round(mean(st), 2) if st else None,
            "national_avg": round(mean(nat), 2) if nat else None,
            "percentile": _percentile(nat, v) if v is not None else None,
            "coverage": len(nat),
        }

    # nearby (adjacency) with a headline
    nearby = db.execute(
        text("""
        SELECT c2.pc_id, c2.pc_name, c2.state_name, a.rank
        FROM constituency c1
        JOIN constituency_adjacency a ON a.constituency_id = c1.id
        JOIN constituency c2 ON c2.id = a.neighbor_id
        WHERE c1.pc_id = :pc ORDER BY a.rank LIMIT 5
        """),
        {"pc": pc_id},
    ).all()
    nearby_out = []
    for n in nearby:
        nr = by_pc.get(n.pc_id)
        nm = metrics_by_cid.get(nr.cid) if nr else None
        nearby_out.append({
            "pc_id": n.pc_id, "pc_name": n.pc_name, "state_name": n.state_name,
            "mp_name": nr.mp_name if nr else None,
            "assets": nm["assets"] if nm else None,
            "pending_cases": nm["pending_cases"] if nm else None,
        })

    return {
        "pc_id": target.pc_id,
        "pc_name": target.pc_name,
        "pc_name_hi": target.pc_name_hi,
        "state_name": target.state_name,
        "pc_category": target.pc_category,
        "wikidata_qid": target.wikidata_qid,
        "mp_person_id": target.person_id,
        "mp_name": target.mp_name,
        "party": target.party,
        "convictions": int(target.convictions) if target.convictions is not None else None,
        "cycle": f"LS{cycle_number}",
        "comparisons": comparisons,
        "nearby": nearby_out,
    }

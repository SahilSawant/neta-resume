"""Backfill office_term.ls_state_code for existing Lok Sabha terms — from cached MyNeta HTML, no network.

The MyNeta parser extracts the constituency's state (e.g. "SIKAR (RAJASTHAN)") but earlier ingests
discarded it. The state still lives in the cached candidate page (source_ref.raw_payload_ref), so we
re-parse it. Each LS office_term uses its OWN cached candidate page when it has one (winner / Tier-2
terms); roster-only terms (sansad source, no MyNeta page) fall back to the person's affidavit snapshot
for the same election cycle.

Run from ingestion/ after applying migration 0010:  uv run python scripts/backfill_ls_state.py
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from neta_core.config import settings
from neta_core.db.engine import session_scope
from neta_sources.myneta.parser import parse_candidate

CACHE = Path(settings.raw_cache_dir)


def main():
    with session_scope() as s:
        rows = s.execute(text(
            """
            SELECT ot.id,
                   sr_own.raw_payload_ref AS own_ref,
                   sr_aff.raw_payload_ref AS aff_ref
            FROM office_term ot
            JOIN house h ON h.id = ot.house_id
            JOIN term_cycle tc ON tc.id = ot.term_cycle_id
            LEFT JOIN source_ref sr_own
                   ON sr_own.id = ot.source_ref_id AND sr_own.raw_payload_ref IS NOT NULL
            LEFT JOIN LATERAL (
                SELECT sr.raw_payload_ref
                FROM affidavit a JOIN source_ref sr ON sr.id = a.source_ref_id
                WHERE a.person_id = ot.person_id AND a.election_cycle = tc.eci_election_id
                  AND sr.raw_payload_ref IS NOT NULL
                LIMIT 1
            ) sr_aff ON true
            WHERE h.code = 'LS' AND ot.ls_state_code IS NULL
            """)).all()

    print(f"[ls-state] {len(rows)} LS office_terms missing state")
    updated, no_source, no_state = 0, 0, 0
    for r in rows:
        ref = r.own_ref or r.aff_ref
        if not ref:
            no_source += 1
            continue
        snap = CACHE / ref
        if not snap.exists():
            no_source += 1
            continue
        parsed = parse_candidate(snap.read_text(encoding="utf-8", errors="ignore"))
        if not parsed.state:
            no_state += 1
            continue
        with session_scope() as s:
            s.execute(text("UPDATE office_term SET ls_state_code = :st WHERE id = :id"),
                      {"st": parsed.state.strip(), "id": r.id})
        updated += 1
    print(f"[ls-state] set state on {updated}; {no_source} had no cached source; {no_state} parsed no state")


if __name__ == "__main__":
    main()

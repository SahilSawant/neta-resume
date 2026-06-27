"""Backfill affidavit data for LS members MyNeta omitted from its winners summary.

These ~77 members exist on MyNeta only on their per-constituency candidate page (not the winners list).
For each roster-only LS person we resolve their constituency -> MyNeta constituency_id -> candidate list,
match the winner by name, then write that candidate's affidavit + criminal data onto the EXISTING person
(creating a MyNeta source_ref for provenance). No new persons -> no duplicates.
"""

from __future__ import annotations

import difflib
import re

from sqlalchemy import text

from neta_ingest.config import settings
from neta_ingest.db.engine import session_scope
from neta_ingest.sources.myneta import client as myneta
from neta_ingest.sources.myneta.parser import ParsedCandidate
from neta_ingest.transform.sections import rollup_severity

CYCLE = "LS2024"

# A few winners whose MyNeta name is formatted too differently to auto-match safely; verified by hand
# against the constituency candidate list. Keyed by normalized constituency -> MyNeta candidate_id.
OVERRIDES = {
    "SATARA": "4320",        # Shrimant Chh Udayanraje Pratapsinhamaharaj Bhonsle
    "NARASARAOPET": "5116",  # Lavu Srikrishna Devarayalu
    "ANANTAPUR": "5097",     # Ambica G Lakshminarayana Valmiki
}


_TITLES = {"dr", "shri", "smt", "kumari", "km", "adv", "prof", "mr", "mrs", "ms", "com", "chh",
           "maharaj", "alias", "thiru", "selvi", "md", "mohd", "capt", "col", "justice", "ku"}


def _name_tokens(s: str) -> set[str]:
    return {t for t in re.sub(r"[^a-z ]", " ", s.lower()).split() if len(t) > 1 and t not in _TITLES}


def _strip(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def _resolve_constituency(const_map: dict[str, str], stripped: dict[str, str], constituency: str) -> str | None:
    norm = myneta._norm_const(constituency)
    if norm in const_map:
        return const_map[norm]
    if _strip(norm) in stripped:
        return stripped[_strip(norm)]
    close = difflib.get_close_matches(norm, const_map.keys(), n=1, cutoff=0.84)
    return const_map[close[0]] if close else None


def run() -> None:
    const_map = myneta.fetch_constituency_map(CYCLE)
    stripped = {_strip(k): v for k, v in const_map.items()}
    print(f"[missing] MyNeta constituency map: {len(const_map)} constituencies")

    with session_scope() as s:
        house_id = s.execute(text("SELECT id FROM house WHERE code='LS'")).scalar()
        term_cycle_id = s.execute(
            text("SELECT id FROM term_cycle WHERE house_id=:h AND number=18"), {"h": house_id}
        ).scalar()
        missing = s.execute(
            text(
                """
                SELECT p.id, p.display_name, p.normalized_name, ot.constituency
                FROM office_term ot
                JOIN term_cycle tc ON tc.id = ot.term_cycle_id
                JOIN house h ON h.id = tc.house_id
                JOIN person p ON p.id = ot.person_id
                WHERE h.code='LS' AND tc.number=18 AND ot.constituency IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM affidavit a WHERE a.person_id = p.id)
                """
            )
        ).all()
    print(f"[missing] {len(missing)} LS members without affidavit data")

    enriched = 0
    unresolved: list[str] = []
    for person in missing:
        override = OVERRIDES.get(myneta._norm_const(person.constituency))
        if override:
            candidate_id = override
        else:
            cons_id = _resolve_constituency(const_map, stripped, person.constituency)
            if not cons_id:
                unresolved.append(f"{person.display_name} ({person.constituency}) — constituency not on MyNeta")
                continue
            candidate_id = _match_candidate(cons_id, person.normalized_name, person.display_name)
        if not candidate_id:
            unresolved.append(f"{person.display_name} ({person.constituency}) — no name match among candidates")
            continue
        parsed, raw_rel = myneta.fetch_candidate(candidate_id, CYCLE)
        with session_scope() as s:
            _write_affidavit(s, parsed, person.id, candidate_id, raw_rel, house_id, term_cycle_id)
        enriched += 1
        print(f"  [{enriched}] {person.display_name} ({person.constituency}) -> cand {candidate_id} "
              f"assets={parsed.total_assets:,} cases={len(parsed.criminal_cases)}")

    print(f"[missing] enriched {enriched} member(s) with affidavit data; {len(unresolved)} unresolved")
    for u in unresolved:
        print("   · " + u)


def _match_candidate(constituency_id: str, normalized_name: str, display_name: str) -> str | None:
    """Find the candidate in a constituency whose name matches our person (exact, else token-subset)."""
    from neta_ingest.transform.names import normalize_name

    cands = myneta.fetch_constituency_candidates(constituency_id, CYCLE)
    want_tokens = _name_tokens(display_name)
    best: str | None = None
    best_ratio = 0.0
    for cand_id, cand_name in cands:
        if normalize_name(cand_name) == normalized_name:
            return cand_id
        ct = _name_tokens(cand_name)
        # token-subset either direction (handles initials / honorific / ordering differences)
        if want_tokens and ct and (want_tokens <= ct or ct <= want_tokens) and len(want_tokens & ct) >= 2:
            return cand_id
        # fuzzy fallback on the de-titled token strings; keep the best above a safe threshold
        ratio = difflib.SequenceMatcher(None, " ".join(sorted(want_tokens)), " ".join(sorted(ct))).ratio()
        if ratio > best_ratio and ratio >= 0.80:
            best, best_ratio = cand_id, ratio
    return best


def _scalar(s, sql: str, **p):
    return s.execute(text(sql), p).scalar()


def _write_affidavit(s, c: ParsedCandidate, person_id: int, candidate_id: str, raw_rel: str,
                     house_id: int, term_cycle_id: int) -> None:
    source_id = _scalar(s, "SELECT id FROM source WHERE code='myneta'")
    source_url = myneta.candidate_url(candidate_id, CYCLE)
    source_ref_id = _scalar(
        s,
        """
        INSERT INTO source_ref (source_id, native_id, native_url, raw_name, raw_payload_ref, person_id)
        VALUES (:sid, :nid, :url, :name, :raw, :pid)
        ON CONFLICT (source_id, native_id) DO UPDATE
          SET native_url = EXCLUDED.native_url, person_id = EXCLUDED.person_id, fetched_at = now()
        RETURNING id
        """,
        sid=source_id, nid=candidate_id, url=source_url, name=c.name, raw=raw_rel, pid=person_id,
    )
    # fill birth year / education if missing
    if c.age:
        s.execute(text("UPDATE person SET birth_year = COALESCE(birth_year, :by) WHERE id = :pid"),
                  {"by": 2024 - c.age, "pid": person_id})

    # clear any prior affidavit/cases for this source_ref, then (re)insert — idempotent
    s.execute(text("DELETE FROM case_charge WHERE criminal_case_id IN "
                   "(SELECT id FROM criminal_case WHERE source_ref_id=:sr)"), {"sr": source_ref_id})
    for tbl in ("criminal_case", "affidavit"):
        s.execute(text(f"DELETE FROM {tbl} WHERE source_ref_id=:sr"), {"sr": source_ref_id})

    affidavit_id = _scalar(
        s,
        """
        INSERT INTO affidavit
          (person_id, source_ref_id, election_cycle, house_id, filed_year, age, education,
           total_assets, total_liabilities, movable_assets, immovable_assets, self_income, income_year, raw_url)
        VALUES (:pid,:sr,:cycle,:hid,2024,:age,:edu,:assets,:liab,:mov,:immov,:income,:iyear,:url)
        RETURNING id
        """,
        pid=person_id, sr=source_ref_id, cycle=CYCLE, hid=house_id, age=c.age, edu=c.education,
        assets=c.total_assets, liab=c.total_liabilities, mov=c.movable_assets, immov=c.immovable_assets,
        income=c.self_income, iyear=c.income_year, url=source_url,
    )
    for case in c.criminal_cases:
        severities = [
            _scalar(s, "SELECT base_severity FROM legal_section WHERE code_system=:cs AND section_number=:sn",
                    cs=code, sn=num)
            for code, num in case.sections
        ]
        severity = rollup_severity(severities)
        status = "convicted" if case.is_convicted else ("framed_charges" if case.charges_framed else "pending")
        case_id = _scalar(
            s,
            """
            INSERT INTO criminal_case
              (person_id, affidavit_id, source_ref_id, case_number, court, filed_year, status,
               is_convicted, severity, severity_rule_version, description)
            VALUES (:pid,:aid,:sr,:cn,:court,2024,:st,:conv,:sev,:ver,:desc) RETURNING id
            """,
            pid=person_id, aid=affidavit_id, sr=source_ref_id, cn=case.fir_number, court=case.court,
            st=status, conv=case.is_convicted, sev=severity, ver=settings.severity_rule_version,
            desc=case.raw_sections,
        )
        for code, num in case.sections:
            section_id = _scalar(s, "SELECT id FROM legal_section WHERE code_system=:cs AND section_number=:sn",
                                 cs=code, sn=num)
            s.execute(
                text("INSERT INTO case_charge (criminal_case_id, section_id, raw_section_text) "
                     "VALUES (:cid,:sid,:raw)"),
                {"cid": case_id, "sid": section_id, "raw": f"{code} {num}"},
            )

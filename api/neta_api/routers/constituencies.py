"""/constituencies routes — the Constituency Report Card.

A Lok Sabha constituency's representation profile (its sitting MP's declared facts) compared to state /
national averages and nearby constituencies. Read-time aggregate, cached by the web's 1-hour ISR.
Descriptive framing only; unmatched/unreported values render as '—' (missing ≠ zero).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from neta_api.deps import get_db
from neta_api.schemas import ConstituencyReportCard, ConstituencySummary
from neta_api.services import constituencies as svc

router = APIRouter(prefix="/constituencies", tags=["constituencies"])


@router.get("", response_model=list[ConstituencySummary])
def list_constituencies(db: Session = Depends(get_db)) -> list[ConstituencySummary]:
    """The 543 Lok Sabha constituencies (index for search / linking)."""
    return [ConstituencySummary(**c) for c in svc.list_constituencies(db)]


@router.get("/{pc_id}/report-card", response_model=ConstituencyReportCard)
def report_card(pc_id: int, db: Session = Depends(get_db)) -> ConstituencyReportCard:
    """The report card for one constituency (by pc_id): MP representation indicators vs state/national/nearby."""
    data = svc.report_card(db, pc_id=pc_id)
    if data is None:
        raise HTTPException(status_code=404, detail="constituency not found")
    return ConstituencyReportCard(**data)

"""
routes/vitals.py — manual vitals entry + history (PostgreSQL).
"""

from fastapi import APIRouter, HTTPException
from app.models.vitals import VitalsInput, VitalsDB
from app.services.vitals_service import save_vitals_to_db, get_latest_vitals, get_vitals_history

router = APIRouter(prefix="/patient", tags=["Vitals"])


def _parse_bp(bp_str: str) -> tuple[int | None, int | None]:
    try:
        parts = bp_str.strip().split("/")
        return int(parts[0]), int(parts[1])
    except Exception:
        return None, None


@router.post("/{mrno}/vitals")
def add_vitals(mrno: int, data: VitalsInput):
    bp_sys, bp_dia = _parse_bp(data.blood_pressure) if data.blood_pressure else (None, None)

    vitals_db = VitalsDB(
        mrno=mrno,
        body_temperature=int(data.temperature) if data.temperature else None,
        heart_rate=data.heart_rate,
        respiratory_rate=data.respiratory_rate,
        bp_systolic=bp_sys,
        bp_diastolic=bp_dia,
        weight_kg=data.weight,
        height_cm=data.height,
        oxygen_level=data.oxygen_level,
        recorded_by="manual",
        notes=data.notes,
    )

    try:
        row_id = save_vitals_to_db(vitals_db)
        return {"status": "success", "message": f"Vitals saved for MR {mrno}", "id": row_id}
    except Exception as e:
        raise HTTPException(500, f"Failed to save vitals: {e}")


@router.get("/{mrno}/vitals")
def get_vitals(mrno: int):
    history = get_vitals_history(mrno)
    if not history:
        return {"status": "success", "message": "No vitals recorded yet", "vitals_history": []}
    return {
        "status": "success",
        "mrno": mrno,
        "total_visits": len(history),
        "vitals_history": history,
    }


@router.get("/{mrno}/vitals/latest")
def get_latest(mrno: int):
    vitals = get_latest_vitals(mrno)
    if not vitals:
        raise HTTPException(404, f"No vitals found for MR {mrno}")
    return {"status": "success", "vitals": vitals}
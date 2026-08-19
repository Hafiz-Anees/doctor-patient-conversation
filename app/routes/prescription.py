"""
routes/prescription.py — generate prescription from a session's summary.
"""

from fastapi import APIRouter, Form, HTTPException

from app.services.prescription_service import extract_raw_medications, build_prescription
from app.utils.session_store import require_session, require_summary, update_session

router = APIRouter(prefix="/prescription", tags=["Prescription"])


@router.post("/generate/{session_id}")
async def generate_prescription(session_id: str):
    """
    Generate enriched prescription from session summary.
    Requires /doctor/summary or /nurse/summary to have been called first.
    """
    session        = require_session(session_id)
    structured_note = require_summary(session_id)

    raw_meds     = await extract_raw_medications(structured_note)
    prescription = build_prescription(structured_note, raw_meds, session_id)

    update_session(session_id, {"prescription": prescription})

    return {
        "status":     "success",
        "session_id": session_id,
        **prescription,
    }


@router.get("/session/{session_id}")
def get_prescription(session_id: str):
    session = require_session(session_id)
    rx = session.get("prescription")
    if not rx:
        raise HTTPException(400, "No prescription generated yet. Call /prescription/generate first.")
    return {"status": "success", "session_id": session_id, **rx}

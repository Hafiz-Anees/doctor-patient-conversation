"""
routes/patient.py — patient demographics from registration.patient (PostgreSQL).

Read-only here: patient registration is owned by the HMIS registration module,
so create/update/delete are intentionally not exposed from this API to avoid
writing into the shared registration.patient table.
"""

from fastapi import APIRouter, HTTPException
from core.database import pg_cursor, VITALS_SCHEMA

router = APIRouter(prefix="/patient", tags=["Patient"])

PATIENT_COLS = ("mrno, patient_name, age, gender, marital_status, "
                "cnic, passport, contact_no, address, status")


@router.get("/by-mrno/{mrno}")
def get_patient(mrno: int):
    with pg_cursor() as cur:
        cur.execute(
            f"SELECT {PATIENT_COLS} FROM {VITALS_SCHEMA}.patient WHERE mrno = %s LIMIT 1",
            (mrno,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, f"No patient found for mrno {mrno}")
    return {"status": "success", "patient": dict(row)}


@router.get("/search/{query}")
def search_patients(query: str):
    """Search by patient_name, cnic, contact_no, or exact mrno."""
    like = f"%{query}%"
    with pg_cursor() as cur:
        cur.execute(
            f"""SELECT {PATIENT_COLS} FROM {VITALS_SCHEMA}.patient
                WHERE patient_name ILIKE %s
                   OR cnic ILIKE %s
                   OR contact_no ILIKE %s
                   OR CAST(mrno AS TEXT) = %s
                ORDER BY mrno DESC
                LIMIT 20""",
            (like, like, like, query),
        )
        rows = cur.fetchall()
    return {"status": "success", "total": len(rows),
            "patients": [dict(r) for r in rows]}
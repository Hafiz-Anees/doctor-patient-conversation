"""
routes/analytics.py — simple usage analytics (PostgreSQL).

Sessions / record counts come from the nurse_audio_recordings and
doctor_audio_recordings tables. Per-medicine analytics are approximated from
the doctor prescription JSON, since prescriptions are stored as a JSON blob on
the doctor row (not one row per drug).
"""

from fastapi import APIRouter
from core.database import pg_cursor

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/sessions/today")
def sessions_today():
    sql_nurse = ("SELECT COUNT(*) AS c FROM public.nurse_audio_recordings "
                 "WHERE created_at::date = CURRENT_DATE")
    sql_doc = ("SELECT COUNT(*) AS c FROM public.doctor_audio_recordings "
               "WHERE created_at::date = CURRENT_DATE")
    with pg_cursor() as cur:
        cur.execute(sql_nurse)
        nurse_count = cur.fetchone()["c"]
        cur.execute(sql_doc)
        doctor_count = cur.fetchone()["c"]
    return {
        "status": "success",
        "nurse_sessions": nurse_count,
        "doctor_sessions": doctor_count,
        "total_sessions": nurse_count + doctor_count,
    }


@router.get("/records/count/{mrno}")
def patient_record_count(mrno: int):
    with pg_cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS c FROM public.doctor_audio_recordings WHERE mrno = %s",
            (mrno,),
        )
        count = cur.fetchone()["c"]
    return {"status": "success", "mrno": mrno, "total_records": count}


@router.get("/prescriptions/today")
def prescriptions_today():
    """How many finalized prescriptions were generated today."""
    sql = ("SELECT COUNT(*) AS c FROM public.doctor_audio_recordings "
           "WHERE prescription IS NOT NULL AND created_at::date = CURRENT_DATE")
    with pg_cursor() as cur:
        cur.execute(sql)
        count = cur.fetchone()["c"]
    return {"status": "success", "prescriptions_today": count}


@router.get("/top-medicines")
def top_medicines(limit: int = 10):
    """
    Approximate top medicines by scanning prescription JSON on doctor rows.
    Looks at prescription -> 'prescription_table' -> each row's 'drug_name'.
    """
    with pg_cursor() as cur:
        cur.execute(
            "SELECT prescription FROM public.doctor_audio_recordings "
            "WHERE prescription IS NOT NULL"
        )
        rows = cur.fetchall()

    counts: dict[str, int] = {}
    for r in rows:
        pres = r["prescription"] or {}
        table = pres.get("prescription_table", []) if isinstance(pres, dict) else []
        for item in table:
            name = (item or {}).get("drug_name")
            if name:
                counts[name] = counts.get(name, 0) + 1

    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return {
        "status": "success",
        "top_medicines": [{"drug_name": n, "count": c} for n, c in top],
    }
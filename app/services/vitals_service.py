"""
vitals_service.py — vitals extraction + storage in registration.patient_vitals.

Matches the REAL table columns:
  body_temperature, heart_rate, respiratory_rate, bp_systolic, bp_diastolic,
  spo2, blood_glucose, pain_score, avpu_score,
  audio_recording_id, nurse_audio_id, doctor_audio_id
(weight_kg / height_cm do NOT exist in this table.)
"""

import json
import google.generativeai as genai
from typing import Optional

from core.config import GEMINI_MODEL
from core.database import pg_cursor, VITALS_SCHEMA
from models.vitals import VitalsExtracted, VitalsDB


# ── AI extraction ─────────────────────────────────────────────────────────────
async def extract_vitals_from_transcript(transcript: str) -> VitalsExtracted:
    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = f"""
You are a clinical data extractor. Read this nurse-patient conversation and extract
ONLY vitals that are EXPLICITLY stated with a number (or an explicit AVPU letter).

Return ONLY a valid JSON object with exactly these keys:
{{
  "body_temperature": <integer Fahrenheit or null>,
  "heart_rate": <integer bpm or null>,
  "respiratory_rate": <integer breaths/min or null>,
  "bp_systolic": <integer mmHg or null>,
  "bp_diastolic": <integer mmHg or null>,
  "spo2": <float percentage or null>,
  "blood_glucose": <float or null>,
  "pain_score": <integer 0-10 or null>,
  "avpu_score": <"A"|"V"|"P"|"U" or null>
}}

CRITICAL RULES — DO NOT GUESS OR INVENT:
- If a vital is NOT explicitly stated with a number in the conversation, you MUST return null for it.
- Do NOT estimate, infer, or fabricate any value. No "typical" or "normal" values.
- Subjective descriptions ("racing heart", "feels hot", "hard to breathe") are NOT numeric vitals → leave null.
- "pain on a scale of X to ten" style answers → pain_score = that number.
- If blood pressure is "120/80", bp_systolic=120, bp_diastolic=80.
- Convert Celsius to Fahrenheit only if a numeric temperature is given.
- Return ONLY the JSON, no markdown, no explanation.

Conversation:
---
{transcript}
---
"""
    response = model.generate_content(prompt)
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return VitalsExtracted(**json.loads(raw))
    except Exception:
        return VitalsExtracted()


# ── Database operations (registration schema) ─────────────────────────────────
def save_vitals_to_db(vitals: VitalsDB) -> int:
    payload = vitals.model_dump() if hasattr(vitals, "model_dump") else vitals.dict()
    for k in ("audio_recording_id", "nurse_audio_id", "doctor_audio_id"):
        payload.setdefault(k, None)

    sql = f"""
        INSERT INTO {VITALS_SCHEMA}.patient_vitals (
            mrno, entry_date, body_temperature, heart_rate, respiratory_rate,
            bp_systolic, bp_diastolic, spo2, blood_glucose, pain_score, avpu_score,
            audio_recording_id, nurse_audio_id, doctor_audio_id
        ) VALUES (
            %(mrno)s, NOW(), %(body_temperature)s, %(heart_rate)s,
            %(respiratory_rate)s, %(bp_systolic)s, %(bp_diastolic)s,
            %(spo2)s, %(blood_glucose)s, %(pain_score)s, %(avpu_score)s,
            %(audio_recording_id)s, %(nurse_audio_id)s, %(doctor_audio_id)s
        )
        RETURNING sr_no
    """
    with pg_cursor() as cur:
        cur.execute(sql, payload)
        row = cur.fetchone()
        return row["sr_no"] if row else -1


def get_latest_vitals(mrno: int) -> Optional[dict]:
    sql = f"""
        SELECT * FROM {VITALS_SCHEMA}.patient_vitals
        WHERE mrno = %s ORDER BY entry_date DESC LIMIT 1
    """
    with pg_cursor() as cur:
        cur.execute(sql, (mrno,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_vitals_history(mrno: int, limit: int = 20) -> list[dict]:
    sql = f"""
        SELECT * FROM {VITALS_SCHEMA}.patient_vitals
        WHERE mrno = %s ORDER BY entry_date DESC LIMIT %s
    """
    with pg_cursor() as cur:
        cur.execute(sql, (mrno, limit))
        return [dict(r) for r in cur.fetchall()]


def vitals_extracted_to_db(
    extracted: VitalsExtracted,
    mrno: int,
    session_id: str,
    recorded_by: str = "nurse",
    nurse_audio_id: Optional[int] = None,
    doctor_audio_id: Optional[int] = None,
) -> VitalsDB:
    # audio_recording_id mirrors whichever audio row produced this vitals
    audio_recording_id = nurse_audio_id if nurse_audio_id is not None else doctor_audio_id
    return VitalsDB(
        mrno=mrno,
        body_temperature=extracted.body_temperature,
        heart_rate=extracted.heart_rate,
        respiratory_rate=extracted.respiratory_rate,
        bp_systolic=extracted.bp_systolic,
        bp_diastolic=extracted.bp_diastolic,
        spo2=extracted.spo2,
        blood_glucose=extracted.blood_glucose,
        pain_score=extracted.pain_score,
        avpu_score=extracted.avpu_score,
        session_id=session_id,
        recorded_by=recorded_by,
        audio_recording_id=audio_recording_id,
        nurse_audio_id=nurse_audio_id,
        doctor_audio_id=doctor_audio_id,
    )


# Vital columns the doctor may update (fixed whitelist -> safe SQL identifiers)
_VITAL_COLS = [
    "body_temperature", "heart_rate", "respiratory_rate",
    "bp_systolic", "bp_diastolic", "spo2", "blood_glucose",
    "pain_score", "avpu_score",
]


def update_doctor_vitals_on_nurse_row(
    mrno: int,
    doctor_audio_id: Optional[int],
    extracted: VitalsExtracted,
    nurse_audio_id: Optional[int] = None,
) -> dict:
    """
    Doctor visit: find the nurse's vitals row for this patient/visit and UPDATE it
    in place — set doctor_audio_id and fill ONLY the vitals the doctor explicitly
    stated (never overwrite an existing value with NULL).

    Row is located by nurse_audio_id when known, else the latest row for this mrno
    that still has doctor_audio_id NULL. If no nurse row exists, a new row is
    created so the doctor's data isn't lost.
    """
    fields = extracted.model_dump() if hasattr(extracted, "model_dump") else dict(extracted)
    mentioned = {k: v for k, v in fields.items() if k in _VITAL_COLS and v is not None}

    with pg_cursor() as cur:
        if nurse_audio_id is not None:
            cur.execute(
                f"""SELECT sr_no FROM {VITALS_SCHEMA}.patient_vitals
                    WHERE mrno = %s AND nurse_audio_id = %s
                    ORDER BY sr_no DESC LIMIT 1""",
                (mrno, nurse_audio_id),
            )
        else:
            cur.execute(
                f"""SELECT sr_no FROM {VITALS_SCHEMA}.patient_vitals
                    WHERE mrno = %s AND doctor_audio_id IS NULL
                          AND nurse_audio_id IS NOT NULL
                    ORDER BY sr_no DESC LIMIT 1""",
                (mrno,),
            )
        row = cur.fetchone()

        if row:
            sr_no = row["sr_no"]
            set_parts = ["doctor_audio_id = %(doctor_audio_id)s"]
            params = {"doctor_audio_id": doctor_audio_id, "sr_no": sr_no}
            for k, v in mentioned.items():
                set_parts.append(f"{k} = %({k})s")
                params[k] = v
            cur.execute(
                f"UPDATE {VITALS_SCHEMA}.patient_vitals "
                f"SET {', '.join(set_parts)} WHERE sr_no = %(sr_no)s",
                params,
            )
            return {
                "action": "updated_nurse_row", "sr_no": sr_no,
                "doctor_audio_id": doctor_audio_id,
                "vitals_updated": list(mentioned.keys()),
            }

    # Fallback: no nurse row found -> create a fresh row tagged with doctor_audio_id
    vitals_db = vitals_extracted_to_db(
        extracted, mrno, session_id="", recorded_by="doctor",
        doctor_audio_id=doctor_audio_id,
    )
    new_sr = save_vitals_to_db(vitals_db)
    return {
        "action": "no_nurse_row_inserted_new", "sr_no": new_sr,
        "doctor_audio_id": doctor_audio_id,
        "vitals_updated": list(mentioned.keys()),
    }


# """
# vitals_service.py — vitals extraction + storage in registration.patient_vitals.

# Matches the REAL table columns:
#   body_temperature, heart_rate, respiratory_rate, bp_systolic, bp_diastolic,
#   spo2, blood_glucose, pain_score, avpu_score,
#   audio_recording_id, nurse_audio_id, doctor_audio_id
# (weight_kg / height_cm do NOT exist in this table.)
# """

# import json
# import google.generativeai as genai
# from typing import Optional

# from core.config import GEMINI_MODEL
# from core.database import pg_cursor, VITALS_SCHEMA
# from models.vitals import VitalsExtracted, VitalsDB


# # ── AI extraction ─────────────────────────────────────────────────────────────
# async def extract_vitals_from_transcript(transcript: str) -> VitalsExtracted:
#     model = genai.GenerativeModel(GEMINI_MODEL)
#     prompt = f"""
# You are a clinical data extractor. Read this nurse-patient conversation and extract
# ONLY vitals that are EXPLICITLY stated with a number (or an explicit AVPU letter).

# Return ONLY a valid JSON object with exactly these keys:
# {{
#   "body_temperature": <integer Fahrenheit or null>,
#   "heart_rate": <integer bpm or null>,
#   "respiratory_rate": <integer breaths/min or null>,
#   "bp_systolic": <integer mmHg or null>,
#   "bp_diastolic": <integer mmHg or null>,
#   "spo2": <float percentage or null>,
#   "blood_glucose": <float or null>,
#   "pain_score": <integer 0-10 or null>,
#   "avpu_score": <"A"|"V"|"P"|"U" or null>
# }}

# CRITICAL RULES — DO NOT GUESS OR INVENT:
# - If a vital is NOT explicitly stated with a number in the conversation, you MUST return null for it.
# - Do NOT estimate, infer, or fabricate any value. No "typical" or "normal" values.
# - Subjective descriptions ("racing heart", "feels hot", "hard to breathe") are NOT numeric vitals → leave null.
# - "pain on a scale of X to ten" style answers → pain_score = that number.
# - If blood pressure is "120/80", bp_systolic=120, bp_diastolic=80.
# - Convert Celsius to Fahrenheit only if a numeric temperature is given.
# - Return ONLY the JSON, no markdown, no explanation.

# Conversation:
# ---
# {transcript}
# ---
# """
#     response = model.generate_content(prompt)
#     raw = response.text.strip().replace("```json", "").replace("```", "").strip()
#     try:
#         return VitalsExtracted(**json.loads(raw))
#     except Exception:
#         return VitalsExtracted()


# # ── Database operations (registration schema) ─────────────────────────────────
# def save_vitals_to_db(vitals: VitalsDB) -> int:
#     payload = vitals.model_dump() if hasattr(vitals, "model_dump") else vitals.dict()
#     for k in ("audio_recording_id", "nurse_audio_id", "doctor_audio_id"):
#         payload.setdefault(k, None)

#     sql = f"""
#         INSERT INTO {VITALS_SCHEMA}.patient_vitals (
#             mrno, body_temperature, heart_rate, respiratory_rate,
#             bp_systolic, bp_diastolic, spo2, blood_glucose, pain_score, avpu_score,
#             audio_recording_id, nurse_audio_id, doctor_audio_id
#         ) VALUES (
#             %(mrno)s, %(body_temperature)s, %(heart_rate)s,
#             %(respiratory_rate)s, %(bp_systolic)s, %(bp_diastolic)s,
#             %(spo2)s, %(blood_glucose)s, %(pain_score)s, %(avpu_score)s,
#             %(audio_recording_id)s, %(nurse_audio_id)s, %(doctor_audio_id)s
#         )
#         RETURNING sr_no
#     """
#     with pg_cursor() as cur:
#         cur.execute(sql, payload)
#         row = cur.fetchone()
#         return row["sr_no"] if row else -1


# def get_latest_vitals(mrno: int) -> Optional[dict]:
#     sql = f"""
#         SELECT * FROM {VITALS_SCHEMA}.patient_vitals
#         WHERE mrno = %s ORDER BY entry_date DESC LIMIT 1
#     """
#     with pg_cursor() as cur:
#         cur.execute(sql, (mrno,))
#         row = cur.fetchone()
#         return dict(row) if row else None


# def get_vitals_history(mrno: int, limit: int = 20) -> list[dict]:
#     sql = f"""
#         SELECT * FROM {VITALS_SCHEMA}.patient_vitals
#         WHERE mrno = %s ORDER BY entry_date DESC LIMIT %s
#     """
#     with pg_cursor() as cur:
#         cur.execute(sql, (mrno, limit))
#         return [dict(r) for r in cur.fetchall()]


# def vitals_extracted_to_db(
#     extracted: VitalsExtracted,
#     mrno: int,
#     session_id: str,
#     recorded_by: str = "nurse",
#     nurse_audio_id: Optional[int] = None,
#     doctor_audio_id: Optional[int] = None,
# ) -> VitalsDB:
#     # audio_recording_id mirrors whichever audio row produced this vitals
#     audio_recording_id = nurse_audio_id if nurse_audio_id is not None else doctor_audio_id
#     return VitalsDB(
#         mrno=mrno,
#         body_temperature=extracted.body_temperature,
#         heart_rate=extracted.heart_rate,
#         respiratory_rate=extracted.respiratory_rate,
#         bp_systolic=extracted.bp_systolic,
#         bp_diastolic=extracted.bp_diastolic,
#         spo2=extracted.spo2,
#         blood_glucose=extracted.blood_glucose,
#         pain_score=extracted.pain_score,
#         avpu_score=extracted.avpu_score,
#         session_id=session_id,
#         recorded_by=recorded_by,
#         audio_recording_id=audio_recording_id,
#         nurse_audio_id=nurse_audio_id,
#         doctor_audio_id=doctor_audio_id,
#     )


# # Vital columns the doctor may update (fixed whitelist -> safe SQL identifiers)
# _VITAL_COLS = [
#     "body_temperature", "heart_rate", "respiratory_rate",
#     "bp_systolic", "bp_diastolic", "spo2", "blood_glucose",
#     "pain_score", "avpu_score",
# ]


# def update_doctor_vitals_on_nurse_row(
#     mrno: int,
#     doctor_audio_id: Optional[int],
#     extracted: VitalsExtracted,
#     nurse_audio_id: Optional[int] = None,
# ) -> dict:
#     """
#     Doctor visit: find the nurse's vitals row for this patient/visit and UPDATE it
#     in place — set doctor_audio_id and fill ONLY the vitals the doctor explicitly
#     stated (never overwrite an existing value with NULL).

#     Row is located by nurse_audio_id when known, else the latest row for this mrno
#     that still has doctor_audio_id NULL. If no nurse row exists, a new row is
#     created so the doctor's data isn't lost.
#     """
#     fields = extracted.model_dump() if hasattr(extracted, "model_dump") else dict(extracted)
#     mentioned = {k: v for k, v in fields.items() if k in _VITAL_COLS and v is not None}

#     with pg_cursor() as cur:
#         if nurse_audio_id is not None:
#             cur.execute(
#                 f"""SELECT sr_no FROM {VITALS_SCHEMA}.patient_vitals
#                     WHERE mrno = %s AND nurse_audio_id = %s
#                     ORDER BY sr_no DESC LIMIT 1""",
#                 (mrno, nurse_audio_id),
#             )
#         else:
#             cur.execute(
#                 f"""SELECT sr_no FROM {VITALS_SCHEMA}.patient_vitals
#                     WHERE mrno = %s AND doctor_audio_id IS NULL
#                           AND nurse_audio_id IS NOT NULL
#                     ORDER BY sr_no DESC LIMIT 1""",
#                 (mrno,),
#             )
#         row = cur.fetchone()

#         if row:
#             sr_no = row["sr_no"]
#             set_parts = ["doctor_audio_id = %(doctor_audio_id)s"]
#             params = {"doctor_audio_id": doctor_audio_id, "sr_no": sr_no}
#             for k, v in mentioned.items():
#                 set_parts.append(f"{k} = %({k})s")
#                 params[k] = v
#             cur.execute(
#                 f"UPDATE {VITALS_SCHEMA}.patient_vitals "
#                 f"SET {', '.join(set_parts)} WHERE sr_no = %(sr_no)s",
#                 params,
#             )
#             return {
#                 "action": "updated_nurse_row", "sr_no": sr_no,
#                 "doctor_audio_id": doctor_audio_id,
#                 "vitals_updated": list(mentioned.keys()),
#             }

#     # Fallback: no nurse row found -> create a fresh row tagged with doctor_audio_id
#     vitals_db = vitals_extracted_to_db(
#         extracted, mrno, session_id="", recorded_by="doctor",
#         doctor_audio_id=doctor_audio_id,
#     )
#     new_sr = save_vitals_to_db(vitals_db)
#     return {
#         "action": "no_nurse_row_inserted_new", "sr_no": new_sr,
#         "doctor_audio_id": doctor_audio_id,
#         "vitals_updated": list(mentioned.keys()),
#     }

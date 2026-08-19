"""
patient_service.py — extract demographics from a transcript and save them into
registration.patient.

Rules (per requirements):
- Demographics are extracted ONLY from what is explicitly spoken in the
  conversation (strict anti-hallucination). Fields not mentioned stay None.
- mrno is provided by the session (same mrno used in patient_vitals /
  nurse_audio_recordings / doctor_audio_recordings). mrno is NOT an identity
  column, so we insert it directly.
- If mrno does NOT exist  -> INSERT a new row (mrno + only the mentioned fields).
- If mrno already EXISTS  -> UPDATE only the fields that were mentioned this
  visit (a returning patient). Fields not mentioned are left untouched (we never
  overwrite an existing value with NULL).
"""

import json
from typing import Optional

import google.generativeai as genai

from core.config import GEMINI_MODEL
from core.database import pg_cursor, VITALS_SCHEMA  # VITALS_SCHEMA == "registration"

# The exact columns we may write to registration.patient (mrno handled separately).
# This is a FIXED whitelist — used to build SQL safely (no user-controlled names).
# NOTE: "clinic" is NOT extracted from the transcript; it is passed in from the
# session (set at session-start). It's listed here only so the upsert SQL allows it.
PATIENT_FIELDS = [
    "patient_name", "age", "gender", "marital_status",
    "cnic", "passport", "contact_no", "address", "status", "clinic",
]


async def extract_demographics(transcript: str) -> dict:
    """Return demographic fields explicitly stated in the transcript; else None."""
    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = f"""
You are a clinical data extractor. Read this patient conversation and extract ONLY
the demographic details that are EXPLICITLY stated by the patient or clinician.

Return ONLY a valid JSON object with exactly these keys:
{{
  "patient_name": <string or null>,
  "age": <integer or null>,
  "gender": <"Male" | "Female" | "Other" or null>,
  "marital_status": <"Married" | "Unmarried" | "Divorced" | "Widowed" or null>,
  "cnic": <string or null>,
  "passport": <string or null>,
  "contact_no": <string or null>,
  "address": <string or null>,
  "status": <"Y" | "N" or null>
}}

CRITICAL RULES — DO NOT GUESS OR INVENT:
- If a field is NOT explicitly stated in the conversation, you MUST return null.
- Do NOT infer gender from a name. Do NOT infer marital status, address, or any
  field that was not actually spoken.
- "age" must be an integer only if an explicit age/number was stated.
- "status" is almost never spoken; return null unless clearly stated.
- Return ONLY the JSON object, no markdown, no extra text.

Conversation:
---
{transcript}
---
"""
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
    except Exception:
        return {}

    cleaned: dict = {}
    for k in PATIENT_FIELDS:
        v = data.get(k)
        if v in (None, "", "null", "None"):
            continue
        if k == "age":
            try:
                v = int(str(v).strip())
            except (ValueError, TypeError):
                continue
        else:
            v = str(v).strip()
            if not v:
                continue
        cleaned[k] = v
    return cleaned


def patient_exists(mrno: int) -> bool:
    with pg_cursor() as cur:
        cur.execute(
            f"SELECT 1 FROM {VITALS_SCHEMA}.patient WHERE mrno = %s LIMIT 1", (mrno,)
        )
        return cur.fetchone() is not None


def upsert_patient_demographics(mrno: int, demo: dict) -> dict:
    """
    Insert a new patient row, or update only the mentioned fields of an existing
    one. Returns a small status dict for the API response.
    """
    if not mrno:
        return {"action": "skipped", "reason": "no mrno"}

    # keep only whitelisted, non-empty fields
    mentioned = {k: v for k, v in demo.items() if k in PATIENT_FIELDS}

    with pg_cursor() as cur:
        cur.execute(
            f"SELECT 1 FROM {VITALS_SCHEMA}.patient WHERE mrno = %s LIMIT 1", (mrno,)
        )
        exists = cur.fetchone() is not None

        if exists:
            if not mentioned:
                return {"action": "exists_no_change", "mrno": mrno, "fields": []}
            set_clause = ", ".join(f"{k} = %({k})s" for k in mentioned)
            cur.execute(
                f"UPDATE {VITALS_SCHEMA}.patient SET {set_clause} WHERE mrno = %(mrno)s",
                {**mentioned, "mrno": mrno},
            )
            return {"action": "updated", "mrno": mrno, "fields": list(mentioned.keys())}

        # new patient -> insert mrno + mentioned fields (rest default/NULL)
        cols = ["mrno"] + list(mentioned.keys())
        placeholders = ", ".join(f"%({c})s" for c in cols)
        cur.execute(
            f"INSERT INTO {VITALS_SCHEMA}.patient ({', '.join(cols)}) "
            f"VALUES ({placeholders})",
            {"mrno": mrno, **mentioned},
        )
        return {"action": "inserted", "mrno": mrno, "fields": list(mentioned.keys())}


async def extract_and_save_demographics(
    mrno: int, transcript: str, clinic: Optional[str] = None
) -> dict:
    """Extract demographics from transcript then upsert. clinic (from the session,
    not the transcript) is written alongside if provided. Best-effort."""
    demo = await extract_demographics(transcript)
    if clinic:
        demo["clinic"] = str(clinic).strip()
    result = upsert_patient_demographics(mrno, demo)
    result["extracted"] = demo
    return result
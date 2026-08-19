"""
summary_service.py — transcript → structured JSON note via Gemini.

Note: demographics pre-fill from MongoDB has been removed. Demographics now come
only from the conversation. To re-enable DB pre-fill later, wire
_get_patient_context() to registration.patient via pg_cursor().
"""

import json
import google.generativeai as genai
from typing import Optional

from core.config import GEMINI_MODEL
from core.database import pg_cursor, VITALS_SCHEMA

genai.configure()


def _get_patient_context(mrno: int) -> tuple[dict, dict]:
    """Pull demographics from registration.patient by mrno. Best-effort."""
    patient_info: dict = {}
    if not mrno:
        return patient_info, {}
    try:
        with pg_cursor() as cur:
            cur.execute(
                f"""SELECT mrno, patient_name, age, gender, marital_status,
                           cnic, passport, contact_no, address
                    FROM {VITALS_SCHEMA}.patient
                    WHERE mrno = %s LIMIT 1""",
                (mrno,),
            )
            row = cur.fetchone()
            if row:
                patient_info = dict(row)
    except Exception as e:
        print(f"⚠️ patient lookup failed: {e}")
    return patient_info, {}


def _build_demographics_block(p: dict) -> str:
    if not p:
        return ""
    return f"""
Pre-filled patient demographics from database (use as defaults;
override if the conversation mentions different values):
- Patient Name   : {p.get('patient_name', '')}
- Age            : {p.get('age', '')}
- Gender         : {p.get('gender', '')}
- Marital Status : {p.get('marital_status', '')}
- CNIC           : {p.get('cnic', '')}
- Contact        : {p.get('contact_no', '')}
- Address        : {p.get('address', '')}
"""


def _build_vitals_block(vitals_info: dict) -> str:
    if not vitals_info:
        return ""
    sys = vitals_info.get("bp_systolic")
    dia = vitals_info.get("bp_diastolic")
    bp = f"{sys}/{dia}" if sys and dia else vitals_info.get("blood_pressure", "")
    return f"""
Latest recorded vitals (use if conversation doesn't update them):
- Blood Pressure   : {bp}
- Heart Rate       : {vitals_info.get('heart_rate', '')} bpm
- Temperature      : {vitals_info.get('body_temperature') or vitals_info.get('temperature', '')} F
- Weight           : {vitals_info.get('weight_kg') or vitals_info.get('weight', '')} kg
- Height           : {vitals_info.get('height_cm') or vitals_info.get('height', '')} cm
- Oxygen Level     : {vitals_info.get('oxygen_level', '')} %
- Respiratory Rate : {vitals_info.get('respiratory_rate', '')} breaths/min
"""


NURSE_SUMMARY_KEYS = """
- "Patient Name"
- "Age"
- "Gender"
- "Date of Birth"
- "Contact Number"
- "Address"
- "Blood Group"
- "Chief Complaints"
- "Symptoms Details"
- "Vitals": {
    "Blood Pressure": "",
    "Heart Rate": "",
    "Temperature": "",
    "Weight": "",
    "Height": "",
    "Oxygen Level": "",
    "Respiratory Rate": ""
  }
- "Allergies"
- "Chronic Conditions"
- "Nurse Observations"
- "Patient Reported History"
"""

DOCTOR_SUMMARY_KEYS = """
- "Patient Name"
- "Age"
- "Gender"
- "Chief Complaints"
- "Symptoms Details"
- "Physical Findings"
- "Social History"
- "Family History"
- "Past Medical History"
- "Medications"
- "Allergies/Immunizations"
- "Preliminary Diagnosis"
- "Final Diagnosis"
- "Treatment Plan"
- "Doctor Comments"
- "Relevant Negatives"
- "Vitals": {
    "Blood Pressure": "",
    "Heart Rate": "",
    "Temperature": "",
    "Weight": "",
    "Height": "",
    "Oxygen Level": "",
    "Respiratory Rate": ""
  }
- "Order Entry": {
    "Lab Tests": [],
    "Imaging": [],
    "Procedures": [],
    "Referrals": [],
    "Medications Ordered": []
  }
"""


async def generate_summary(
    transcript: str,
    target_language: str = "English",
    role: str = "doctor",
    emr_id: str = "",
    mrno: int = 0,
    pre_filled_vitals: Optional[dict] = None,
) -> dict:
    model = genai.GenerativeModel(GEMINI_MODEL)

    patient_info, _ = _get_patient_context(mrno)
    demographics_block = _build_demographics_block(patient_info)
    vitals_block = _build_vitals_block(pre_filled_vitals or {})

    keys_section = NURSE_SUMMARY_KEYS if role == "nurse" else DOCTOR_SUMMARY_KEYS

    prompt = f"""
Analyze this {'nurse-patient' if role == 'nurse' else 'doctor-patient'} conversation
and convert it into a structured JSON medical note.

All text values must be in {target_language}.

=== CRITICAL ANTI-HALLUCINATION RULES (MUST FOLLOW) ===
1. Use ONLY information that is EXPLICITLY stated in the conversation (or in the
   pre-filled demographics/vitals blocks below, if present).
2. NEVER invent, estimate, assume, or fill in "typical"/"normal" clinical values.
3. If a field is NOT mentioned in the conversation, set it to "" (empty string)
   or [] (empty list). Do NOT guess.
4. VITALS SPECIAL RULE: For the "Vitals" object, ONLY fill a field if an ACTUAL
   NUMERIC value for it was explicitly spoken in the conversation (e.g. "blood
   pressure is 120 over 80", "temperature is 101", "oxygen is 95 percent").
   - Subjective descriptions are NOT vitals. "racing heart", "feels hot",
     "trouble breathing", "lightheaded" → these are symptoms, NOT numeric vitals.
     Leave the corresponding Vitals field as "".
   - If NO numeric vitals were spoken at all, every field inside "Vitals" must be "".
   - Do NOT copy a pain score (e.g. "7-8/10") into any Vitals field.
5. A symptom being present does NOT let you infer a vital. Only transcribe numbers
   that were actually said.

{demographics_block}
{vitals_block}

Required JSON keys:
{keys_section}

{'Extra instructions for Order Entry (doctor notes only):' if role == 'doctor' else ''}
{'- Lab Tests: every test mentioned (CBC, LFTs, etc.)' if role == 'doctor' else ''}
{'- Imaging: X-Ray, MRI, CT, Ultrasound, etc.' if role == 'doctor' else ''}
{'- Procedures: ECG, Biopsy, Endoscopy, etc.' if role == 'doctor' else ''}
{'- Referrals: specialty referrals (Cardiology, Neurology, etc.)' if role == 'doctor' else ''}
{'- Medications Ordered: every medicine with dose if mentioned' if role == 'doctor' else ''}

Conversation:
---
{transcript}
---

Return ONLY the JSON object, no markdown fences, no extra text.
"""
    response = model.generate_content(prompt)
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Failed to parse summary JSON", "raw_note": raw}


async def translate_transcript(text: str, source_language: str,
                               target_language: str) -> str:
    if source_language.lower() == target_language.lower():
        return text
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(
        f"Translate the following {source_language} text into {target_language}. "
        f"Return only the translation:\n\n{text}"
    )
    return response.text.strip()
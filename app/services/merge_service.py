"""
merge_service.py

Merges nurse summary + doctor summary into one complete medical record.
Persistence is on public.doctor_audio_recordings (no Mongo). The merged note is
stored in that row's `summary` column at finalize time by routes/doctor.
"""

import json
import uuid
from datetime import datetime, timezone

import google.generativeai as genai

from app.core.config import GEMINI_MODEL
from app.core.database import get_doctor_record_by_session, get_doctor_records_by_mrno

genai.configure()


async def merge_summaries(
    nurse_summary: dict,
    doctor_summary: dict,
    mrno: int,
    nurse_session_id: str,
    doctor_session_id: str,
) -> dict:
    """AI merge. Returns {record_id, merged_record, ...}. Does NOT persist itself."""
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = f"""
You are a clinical documentation specialist.
You have two summaries for the SAME patient visit:

NURSE SUMMARY (initial assessment, vitals, chief complaints):
{json.dumps(nurse_summary, indent=2)}

DOCTOR SUMMARY (examination, diagnosis, treatment plan, orders):
{json.dumps(doctor_summary, indent=2)}

Merge them into ONE complete medical record JSON.

Rules:
1. Patient demographics — use nurse values (confirmed first); doctor overrides if different.
2. Vitals — prefer doctor's if updated during consultation, else nurse's.
3. Chief Complaints / Symptoms — combine both without duplication.
4. Physical Findings, Social History, Family History — from doctor summary.
5. Nurse Observations / Nurse Notes — include as "Nurse Notes" section.
6. Diagnosis (Preliminary + Final) — from doctor summary.
7. Treatment Plan, Doctor Comments — from doctor summary.
8. Order Entry (Labs, Imaging, Procedures, Referrals, Medications) — from doctor summary.
9. Allergies — merge both lists, remove duplicates.
10. Keep ALL fields from both summaries; never drop data.

Return ONLY the merged JSON object, no markdown fences, no extra text.
"""
    response = model.generate_content(prompt)
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        merged = json.loads(raw)
    except json.JSONDecodeError:
        merged = {
            "error": "Merge JSON parse failed",
            "nurse_summary": nurse_summary,
            "doctor_summary": doctor_summary,
        }

    # Visit Summary is generated in a SEPARATE call, from the already-merged
    # (real) data only — this keeps the style example below from ever being
    # able to leak into Patient Name / Age / Chief Complaints / etc.

    if "error" not in merged:
        merged["Visit Summary"] = await _generate_visit_summary(merged, nurse_summary, doctor_summary)


    return {
        "record_id": doctor_session_id or str(uuid.uuid4()),
        "mrno": mrno,
        "nurse_session_id": nurse_session_id,
        "doctor_session_id": doctor_session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "final",
        "merged_record": merged,
    }


async def _generate_visit_summary(merged_note: dict, nurse_summary: dict, doctor_summary: dict) -> str:
    """
    Writes the short human-readable paragraph — as a SEPARATE call, using only
    the already-merged, already-correct data. Weighted so the doctor's own
    assessment of THIS visit dominates the summary, with the nurse's intake
    notes used only as light supporting context.
    """
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = f"""
Below is REAL, already-finalized patient data for one visit, split by who
recorded it. Use ONLY these facts. Do not invent, guess, or borrow any
name/number/complaint from anywhere else.

DOCTOR'S NOTES (this is the current clinical visit — this should drive
roughly 70% of the summary's content and emphasis):
{json.dumps(doctor_summary, indent=2)}

NURSE'S INTAKE NOTES (background/context only — should make up roughly 30%
of the summary, used to add brief context, not to lead any sentence):
{json.dumps(nurse_summary, indent=2)}

FULL MERGED RECORD (for any fact not clearly attributed above):
{json.dumps(merged_note, indent=2)}

Write ONE paragraph, strictly between 50 and 60 words, in plain flowing
sentences (no bullet points, no field labels). Structure:
  a) Patient's name, age, gender, and chief complaint, with duration if
     mentioned.
  b) Vitals folded into one sentence — but ONLY vitals that actually have a
     value. If a vital is missing, silently drop it; if ALL vitals are
     missing, skip this sentence entirely.
  c) Diagnosis and/or plan in plain language, drawn mainly from the doctor's
     notes. If no diagnosis has been reached yet, say evaluation is ongoing.

The doctor's clinical assessment and findings should be the main substance of
the paragraph. Nurse intake details (lifestyle, history, initial complaint
wording) should appear only briefly, in service of the doctor's picture — not
as separate, equally-weighted content.

CRITICAL: The two examples below are for STYLE ONLY — sentence rhythm and
tone. Their names, ages, numbers, and complaints are fictional placeholders
and are COMPLETELY UNRELATED to the real data above. Never copy any word,
number, or fact from these examples into your output.

Example A (when most fields are present):
"Patient Zubaid Example, a 52-year-old male, presented with abdominal pain
for three days. His vital signs were stable with BP 128/82 mmHg, heart rate
76 bpm, and temperature 99°F. Further evaluation is recommended to identify
the underlying cause and plan treatment."

Example B (when vitals/diagnosis are missing — showing graceful omission):
"Patient Aisha Placeholder, a 30-year-old female, presented with fatigue and
headache for one week. No formal vitals were recorded during this visit.
Further assessment is recommended to determine the cause and guide next
steps."

Return ONLY the paragraph text — no quotes, no labels, no markdown.
"""
    response = model.generate_content(prompt)
    return response.text.strip().strip('"')

def get_medical_record(record_id: str) -> dict | None:
    """record_id == doctor session_id (see merge_summaries / finalize)."""
    return get_doctor_record_by_session(record_id)


def get_patient_records(mrno: int) -> list[dict]:
    return get_doctor_records_by_mrno(mrno)
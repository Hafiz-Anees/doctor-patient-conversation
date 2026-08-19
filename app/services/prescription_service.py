"""
prescription_service.py

Extracts medications from a structured summary, enriches them from local code
tables, matches lab tests, and builds the full prescription payload.

Persistence: the returned prescription dict is stored on the doctor audio row
(doctor_audio_recordings.prescription) by routes/doctor.finalize. No Mongo.
"""

import json
from datetime import datetime, timezone

import google.generativeai as genai

from core.config import GEMINI_MODEL
from tools.prescription_engine import enrich_prescription, format_prescription_table
from tools.lab_tests import match_lab_test_from_text

genai.configure()


async def extract_raw_medications(structured_note: dict) -> list[dict]:
    model = genai.GenerativeModel(GEMINI_MODEL)
    extraction_prompt = f"""
From this structured patient note, extract ALL medications mentioned anywhere.
Check: "Medications", "Order Entry > Medications Ordered", "Treatment Plan", "Doctor Comments".

Return a JSON array. Each item must have exactly:
- "drug_name"  : brand or generic name (string)
- "strength"   : e.g. "500mg" (string, "" if unknown)
- "dosage"     : e.g. "1 tablet" (string, "" if unknown)
- "frequency"  : doctor's exact words e.g. "morning and evening" (string)
- "duration"   : e.g. "5 days" (string, "" if unknown)
- "route"      : e.g. "by mouth" (string, "" if unknown)
- "quantity"   : e.g. "10 tablets" (string, "" if unknown)

Rules:
- Include vitamins, supplements, OTC drugs
- Copy frequency/route in doctor's exact words — do NOT abbreviate
- If no frequency given → "as directed"
- If list is empty → return []
- Return ONLY the JSON array, no markdown

Structured Note:
{json.dumps(structured_note, indent=2)}
"""
    response = model.generate_content(extraction_prompt)
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(raw)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


def build_prescription(
    structured_note: dict,
    raw_medications: list[dict],
    session_id: str,
) -> dict:
    """Enrich medications + match lab tests. Returns the prescription dict."""
    enriched   = enrich_prescription(raw_medications)
    table_rows = format_prescription_table(enriched)

    order_entry   = structured_note.get("Order Entry", {})
    raw_lab_tests = order_entry.get("Lab Tests", [])

    matched_labs, unmatched_labs = [], []
    for test_name in raw_lab_tests:
        matched = match_lab_test_from_text(test_name)
        entry = {
            "lab_code": matched["code"] if matched else "UNKNOWN",
            "name":     matched["name"] if matched else test_name,
            "category": matched["category"] if matched else "",
            "raw_text": test_name,
        }
        (matched_labs if matched else unmatched_labs).append(entry)

    header = {
        "patient_name":    structured_note.get("Patient Name", ""),
        "age":             str(structured_note.get("Age", "")),
        "gender":          structured_note.get("Gender", ""),
        "contact":         structured_note.get("Contact Number", ""),
        "diagnosis":       structured_note.get("Final Diagnosis", "")
                           or structured_note.get("Preliminary Diagnosis", ""),
        "doctor_comments": structured_note.get("Doctor Comments", ""),
        "date":            datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

    return {
        "prescription_header":   header,
        "total_medications":     len(table_rows),
        "prescription_table":    table_rows,
        "lab_tests_ordered":     matched_labs + unmatched_labs,
        "imaging_ordered":       order_entry.get("Imaging", []),
        "procedures_ordered":    order_entry.get("Procedures", []),
        "referrals":             order_entry.get("Referrals", []),
    }


# """
# prescription_service.py

# Extracts medications from a structured summary,
# enriches them from local code tables, matches lab tests,
# and builds the full prescription payload.
# """

# import json
# from datetime import datetime, timezone

# import google.generativeai as genai

# from core.config import GEMINI_MODEL
# from core.database import prescriptions_col

# # These files must exist in your project root / tools/
# # We import them from tools/ package
# from tools.prescription_engine import enrich_prescription, format_prescription_table
# from tools.lab_tests import match_lab_test_from_text

# genai.configure()


# async def extract_raw_medications(structured_note: dict) -> list[dict]:
#     """Ask Gemini to pull every medication from the note as structured JSON."""
#     model = genai.GenerativeModel(GEMINI_MODEL)

#     extraction_prompt = f"""
# From this structured patient note, extract ALL medications mentioned anywhere.
# Check: "Medications", "Order Entry > Medications Ordered", "Treatment Plan", "Doctor Comments".

# Return a JSON array. Each item must have exactly:
# - "drug_name"  : brand or generic name (string)
# - "strength"   : e.g. "500mg" (string, "" if unknown)
# - "dosage"     : e.g. "1 tablet" (string, "" if unknown)
# - "frequency"  : doctor's exact words e.g. "morning and evening" (string)
# - "duration"   : e.g. "5 days" (string, "" if unknown)
# - "route"      : e.g. "by mouth" (string, "" if unknown)
# - "quantity"   : e.g. "10 tablets" (string, "" if unknown)

# Rules:
# - Include vitamins, supplements, OTC drugs
# - Copy frequency/route in doctor's exact words — do NOT abbreviate
# - If no frequency given → "as directed"
# - If list is empty → return []
# - Return ONLY the JSON array, no markdown

# Structured Note:
# {json.dumps(structured_note, indent=2)}
# """
#     response = model.generate_content(extraction_prompt)
#     raw = response.text.strip().replace("```json", "").replace("```", "").strip()
#     try:
#         result = json.loads(raw)
#         return result if isinstance(result, list) else []
#     except json.JSONDecodeError:
#         return []


# def build_prescription(
#     structured_note: dict,
#     raw_medications: list[dict],
#     session_id: str,
# ) -> dict:
#     """
#     Enrich medications + match lab tests.
#     Returns the full prescription response dict.
#     Also saves prescription rows to MongoDB.
#     """
#     # ── Enrich medications ────────────────────────────────────────────────────
#     enriched   = enrich_prescription(raw_medications)
#     table_rows = format_prescription_table(enriched)

#     # ── Match lab tests ───────────────────────────────────────────────────────
#     order_entry    = structured_note.get("Order Entry", {})
#     raw_lab_tests  = order_entry.get("Lab Tests", [])

#     matched_labs   = []
#     unmatched_labs = []
#     for test_name in raw_lab_tests:
#         matched = match_lab_test_from_text(test_name)
#         entry = {
#             "lab_code": matched["code"]  if matched else "UNKNOWN",
#             "name":     matched["name"]  if matched else test_name,
#             "category": matched["category"] if matched else "",
#             "raw_text": test_name,
#         }
#         (matched_labs if matched else unmatched_labs).append(entry)

#     all_labs = matched_labs + unmatched_labs

#     # ── Header ────────────────────────────────────────────────────────────────
#     header = {
#         "patient_name":    structured_note.get("Patient Name", ""),
#         "age":             str(structured_note.get("Age", "")),
#         "gender":          structured_note.get("Gender", ""),
#         "contact":         structured_note.get("Contact Number", ""),
#         "diagnosis":       structured_note.get("Final Diagnosis", "")
#                            or structured_note.get("Preliminary Diagnosis", ""),
#         "doctor_comments": structured_note.get("Doctor Comments", ""),
#         "date":            datetime.now(timezone.utc).strftime("%Y-%m-%d"),
#     }

#     # ── Persist to MongoDB ────────────────────────────────────────────────────
#     for item in table_rows:
#         prescriptions_col.insert_one({
#             "session_id":    session_id,
#             "patient_name":  header["patient_name"],
#             "medicine_code": item.get("medicine_code"),
#             "drug_name":     item["drug_name"],
#             "ordered_at":    datetime.now(timezone.utc).isoformat(),
#         })

#     return {
#         "prescription_header":   header,
#         "total_medications":     len(table_rows),
#         "prescription_table":    table_rows,
#         "lab_tests_ordered":     all_labs,
#         "imaging_ordered":       order_entry.get("Imaging", []),
#         "procedures_ordered":    order_entry.get("Procedures", []),
#         "referrals":             order_entry.get("Referrals", []),
#     }

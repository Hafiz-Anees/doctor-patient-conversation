"""
coding_service.py — generate ICD, HCC, and E/M codes from a structured note.
"""

import json
import google.generativeai as genai
from app.core.config import GEMINI_MODEL

genai.configure()


async def generate_medical_codes(structured_note: dict) -> dict:
    """
    Returns:
      {
        "ICD_Codes": [{"code": ..., "description": ...}, ...],
        "HCC_Codes": [...],
        "EM_Codes":  [...]
      }
    """
    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = f"""
You are a certified medical coder (CPC).
Based on the structured patient note below, generate standardized medical codes.

Return a JSON object with exactly three keys:
- "ICD_Codes" : list of {{"code": "string", "description": "string"}}
- "HCC_Codes" : list of {{"code": "string", "description": "string"}}
- "EM_Codes"  : list of {{"code": "string", "description": "string"}}

Rules:
- Use ICD-10-CM codes (format: X00.0)
- HCC codes from CMS-HCC model v28
- E/M codes from CPT (99202-99215 for office visits)
- If no relevant code for a category → return []
- Return ONLY the JSON, no markdown

Structured Note:
{json.dumps(structured_note, indent=2)}
"""
    response = model.generate_content(prompt)
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "ICD_Codes": [],
            "HCC_Codes": [],
            "EM_Codes":  [],
            "error":     "Failed to parse codes",
            "raw":       raw,
        }

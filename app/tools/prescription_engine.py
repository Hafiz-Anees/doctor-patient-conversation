"""
tools/prescription_engine.py

Enriches raw medication lists with codes from local reference tables.
No AI used — pure lookup.
"""

from tools.medicine_codes import get_medicine_by_name, search_medicines
from tools.frequency_codes import match_frequency_from_text
from tools.route_codes import match_route_from_text


def enrich_prescription_item(item: dict) -> dict:
    """
    Enrich a single medication dict with medicine_code, freq_code, route_code.
    """
    drug_name = item.get("drug_name", "")

    # 1. Medicine code lookup
    med = get_medicine_by_name(drug_name) or (search_medicines(drug_name) or [None])[0]
    medicine_code = med["code"] if med else "UNKNOWN"
    strength      = item.get("strength") or (med.get("strength", "") if med else "")

    # 2. Frequency code lookup
    freq_text  = item.get("frequency", "as directed")
    freq_match = match_frequency_from_text(freq_text)
    freq_code  = freq_match["code"] if freq_match else freq_text

    # 3. Route code lookup
    route_text  = item.get("route", "")
    route_match = match_route_from_text(route_text) if route_text else None
    route_code  = route_match["code"] if route_match else route_text

    return {
        **item,
        "medicine_code": medicine_code,
        "strength":      strength,
        "freq_code":     freq_code,
        "route_code":    route_code,
    }


def enrich_prescription(medications: list[dict]) -> list[dict]:
    return [enrich_prescription_item(m) for m in medications]


def format_prescription_table(enriched: list[dict]) -> list[dict]:
    """Format enriched medications into clean table rows."""
    rows = []
    for item in enriched:
        rows.append({
            "medicine_code": item.get("medicine_code", "UNKNOWN"),
            "drug_name":     item.get("drug_name", ""),
            "strength":      item.get("strength", ""),
            "dosage":        item.get("dosage", ""),
            "freq_code":     item.get("freq_code", ""),
            "frequency":     item.get("frequency", ""),
            "route_code":    item.get("route_code", ""),
            "route":         item.get("route", ""),
            "duration":      item.get("duration", ""),
            "quantity":      item.get("quantity", ""),
        })
    return rows

"""
tools/medicine_codes.py

Replace the MEDICINE_CODES list below with your full medicine catalogue.
Each entry must have at minimum: code, name, strength (optional).
"""

MEDICINE_CODES: list[dict] = [
    {"code": "MED-001", "name": "Paracetamol",     "strength": "500mg",    "aliases": ["acetaminophen", "panadol", "tylenol"]},
    {"code": "MED-002", "name": "Amoxicillin",     "strength": "500mg",    "aliases": ["amoxil"]},
    {"code": "MED-003", "name": "Ibuprofen",        "strength": "400mg",    "aliases": ["brufen", "advil", "nurofen"]},
    {"code": "MED-004", "name": "Metformin",        "strength": "500mg",    "aliases": ["glucophage"]},
    {"code": "MED-005", "name": "Atorvastatin",     "strength": "10mg",     "aliases": ["lipitor"]},
    {"code": "MED-006", "name": "Omeprazole",       "strength": "20mg",     "aliases": ["losec", "prilosec"]},
    {"code": "MED-007", "name": "Amlodipine",       "strength": "5mg",      "aliases": ["norvasc"]},
    {"code": "MED-008", "name": "Lisinopril",       "strength": "5mg",      "aliases": ["zestril", "prinivil"]},
    {"code": "MED-009", "name": "Ciprofloxacin",    "strength": "500mg",    "aliases": ["cipro"]},
    {"code": "MED-010", "name": "Azithromycin",     "strength": "250mg",    "aliases": ["zithromax", "z-pack"]},
    {"code": "MED-011", "name": "Salbutamol",       "strength": "100mcg",   "aliases": ["albuterol", "ventolin"]},
    {"code": "MED-012", "name": "Prednisolone",     "strength": "5mg",      "aliases": ["pred", "prednisone"]},
    {"code": "MED-013", "name": "Pantoprazole",     "strength": "40mg",     "aliases": ["protonix", "pantoloc"]},
    {"code": "MED-014", "name": "Cetirizine",       "strength": "10mg",     "aliases": ["zyrtec", "reactine"]},
    {"code": "MED-015", "name": "Vitamin D3",       "strength": "1000IU",   "aliases": ["cholecalciferol", "vit d"]},
]


def get_medicine_by_code(code: str) -> dict | None:
    for m in MEDICINE_CODES:
        if m["code"].lower() == code.lower():
            return m
    return None


def get_medicine_by_name(name: str) -> dict | None:
    name_l = name.lower().strip()
    for m in MEDICINE_CODES:
        if m["name"].lower() == name_l:
            return m
        if name_l in [a.lower() for a in m.get("aliases", [])]:
            return m
    return None


def search_medicines(query: str) -> list[dict]:
    q = query.lower().strip()
    results = []
    for m in MEDICINE_CODES:
        searchable = m["name"].lower() + " " + " ".join(m.get("aliases", []))
        if q in searchable:
            results.append(m)
    return results

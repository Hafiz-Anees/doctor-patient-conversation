"""
tools/route_codes.py — medication administration route abbreviations.
"""

ROUTE_CODES: list[dict] = [
    {"code": "PO",  "label": "By Mouth (Oral)",    "aliases": ["by mouth", "orally", "oral", "po", "swallow"]},
    {"code": "SL",  "label": "Sublingual",          "aliases": ["sublingual", "under the tongue", "sl"]},
    {"code": "IV",  "label": "Intravenous",         "aliases": ["intravenous", "iv", "into the vein", "intravenously"]},
    {"code": "IM",  "label": "Intramuscular",       "aliases": ["intramuscular", "im", "into the muscle", "intramuscularly"]},
    {"code": "SC",  "label": "Subcutaneous",        "aliases": ["subcutaneous", "sc", "sub-cut", "under the skin"]},
    {"code": "TOP", "label": "Topical",             "aliases": ["topical", "apply topically", "on the skin", "externally"]},
    {"code": "INH", "label": "Inhalation",          "aliases": ["inhaled", "inhalation", "by inhaler", "nasal spray", "puff"]},
    {"code": "REC", "label": "Rectal",              "aliases": ["rectal", "rectally", "suppository"]},
    {"code": "OPH", "label": "Ophthalmic (Eye)",    "aliases": ["eye drops", "ophthalmic", "into the eye", "ocular"]},
    {"code": "OTI", "label": "Otic (Ear)",          "aliases": ["ear drops", "otic", "into the ear"]},
    {"code": "NAS", "label": "Nasal",               "aliases": ["nasal", "nose drops", "into the nose"]},
    {"code": "TD",  "label": "Transdermal (Patch)", "aliases": ["patch", "transdermal", "skin patch"]},
]


def get_route_by_code(code: str) -> dict | None:
    for r in ROUTE_CODES:
        if r["code"].lower() == code.lower():
            return r
    return None


def match_route_from_text(text: str) -> dict | None:
    t = text.lower().strip()
    for r in ROUTE_CODES:
        if any(alias in t for alias in r["aliases"]):
            return r
    return None

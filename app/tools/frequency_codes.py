"""
tools/frequency_codes.py — medication frequency abbreviations.
"""

FREQUENCY_CODES: list[dict] = [
    {"code": "OD",  "label": "Once Daily",          "aliases": ["once daily", "once a day", "daily", "od", "every day"]},
    {"code": "BD",  "label": "Twice Daily",          "aliases": ["twice daily", "twice a day", "morning and evening", "morning & evening", "bd", "bid"]},
    {"code": "TDS", "label": "Three Times Daily",    "aliases": ["three times daily", "three times a day", "tds", "tid", "thrice daily"]},
    {"code": "QID", "label": "Four Times Daily",     "aliases": ["four times daily", "four times a day", "qid"]},
    {"code": "QHS", "label": "At Bedtime",           "aliases": ["at bedtime", "at night", "only at night", "at sleep time", "nocte", "hs"]},
    {"code": "QAM", "label": "Every Morning",        "aliases": ["every morning", "in the morning", "qam", "morning only"]},
    {"code": "PRN", "label": "As Needed",            "aliases": ["as needed", "when needed", "as required", "prn", "sos"]},
    {"code": "Q4H", "label": "Every 4 Hours",        "aliases": ["every 4 hours", "every four hours", "q4h", "4 hourly"]},
    {"code": "Q6H", "label": "Every 6 Hours",        "aliases": ["every 6 hours", "every six hours", "q6h", "6 hourly"]},
    {"code": "Q8H", "label": "Every 8 Hours",        "aliases": ["every 8 hours", "every eight hours", "q8h", "8 hourly"]},
    {"code": "Q12H","label": "Every 12 Hours",       "aliases": ["every 12 hours", "every twelve hours", "q12h", "12 hourly"]},
    {"code": "QW",  "label": "Once Weekly",          "aliases": ["once weekly", "once a week", "weekly", "qw"]},
    {"code": "STAT","label": "Immediately",          "aliases": ["immediately", "right now", "stat", "at once", "now"]},
    {"code": "AC",  "label": "Before Meals",         "aliases": ["before meals", "before food", "before eating", "ac"]},
    {"code": "PC",  "label": "After Meals",          "aliases": ["after meals", "after food", "after eating", "pc", "with food"]},
]


def get_frequency_by_code(code: str) -> dict | None:
    for f in FREQUENCY_CODES:
        if f["code"].lower() == code.lower():
            return f
    return None


def match_frequency_from_text(text: str) -> dict | None:
    t = text.lower().strip()
    for f in FREQUENCY_CODES:
        if any(alias in t for alias in f["aliases"]):
            return f
    return None

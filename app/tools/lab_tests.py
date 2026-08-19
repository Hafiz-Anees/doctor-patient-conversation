"""
tools/lab_tests.py — lab test catalogue with category + aliases for matching.
"""

LAB_TESTS: list[dict] = [
    # ── Hematology ────────────────────────────────────────────────────────────
    {"code": "LAB-001", "name": "Complete Blood Count",         "category": "Hematology",   "aliases": ["cbc", "fbc", "full blood count", "haemogram"]},
    {"code": "LAB-002", "name": "Erythrocyte Sedimentation Rate","category": "Hematology",  "aliases": ["esr", "sed rate"]},
    {"code": "LAB-003", "name": "Peripheral Blood Smear",       "category": "Hematology",   "aliases": ["pbs", "blood film", "blood smear"]},
    {"code": "LAB-004", "name": "Prothrombin Time",             "category": "Hematology",   "aliases": ["pt", "inr", "pt/inr", "coagulation"]},
    {"code": "LAB-005", "name": "Activated Partial Thromboplastin Time", "category": "Hematology", "aliases": ["aptt", "ptt"]},

    # ── Biochemistry ─────────────────────────────────────────────────────────
    {"code": "LAB-010", "name": "Fasting Blood Sugar",          "category": "Biochemistry", "aliases": ["fbs", "fasting glucose", "blood sugar fasting"]},
    {"code": "LAB-011", "name": "Random Blood Sugar",           "category": "Biochemistry", "aliases": ["rbs", "random glucose", "blood sugar random"]},
    {"code": "LAB-012", "name": "HbA1c",                        "category": "Biochemistry", "aliases": ["hba1c", "glycated haemoglobin", "glycosylated hemoglobin"]},
    {"code": "LAB-013", "name": "Liver Function Tests",         "category": "Biochemistry", "aliases": ["lfts", "lft", "liver function", "liver panel"]},
    {"code": "LAB-014", "name": "Renal Function Tests",         "category": "Biochemistry", "aliases": ["rfts", "rft", "kidney function", "kidney panel", "bun creatinine"]},
    {"code": "LAB-015", "name": "Lipid Profile",                "category": "Biochemistry", "aliases": ["lipids", "lipid panel", "cholesterol", "triglycerides"]},
    {"code": "LAB-016", "name": "Uric Acid",                    "category": "Biochemistry", "aliases": ["uric acid", "serum urate"]},
    {"code": "LAB-017", "name": "Serum Electrolytes",           "category": "Biochemistry", "aliases": ["electrolytes", "sodium", "potassium", "chloride", "na k cl"]},
    {"code": "LAB-018", "name": "C-Reactive Protein",           "category": "Biochemistry", "aliases": ["crp", "c reactive protein"]},

    # ── Thyroid ───────────────────────────────────────────────────────────────
    {"code": "LAB-020", "name": "Thyroid Function Tests",       "category": "Thyroid",      "aliases": ["tfts", "tft", "thyroid panel", "thyroid profile"]},
    {"code": "LAB-021", "name": "TSH",                          "category": "Thyroid",      "aliases": ["tsh", "thyroid stimulating hormone"]},
    {"code": "LAB-022", "name": "Free T3",                      "category": "Thyroid",      "aliases": ["ft3", "free t3", "triiodothyronine"]},
    {"code": "LAB-023", "name": "Free T4",                      "category": "Thyroid",      "aliases": ["ft4", "free t4", "thyroxine"]},

    # ── Urine ─────────────────────────────────────────────────────────────────
    {"code": "LAB-030", "name": "Urine Routine Examination",    "category": "Urine",        "aliases": ["urine re", "urinalysis", "urine routine", "urine analysis", "ure"]},
    {"code": "LAB-031", "name": "Urine Culture & Sensitivity",  "category": "Urine",        "aliases": ["urine c/s", "urine culture", "ucs", "urine cs"]},
    {"code": "LAB-032", "name": "24-Hour Urine Protein",        "category": "Urine",        "aliases": ["24hr urine protein", "urine protein 24h"]},

    # ── Microbiology ─────────────────────────────────────────────────────────
    {"code": "LAB-040", "name": "Blood Culture & Sensitivity",  "category": "Microbiology", "aliases": ["blood culture", "blood c/s", "bcs"]},
    {"code": "LAB-041", "name": "Throat Swab C/S",              "category": "Microbiology", "aliases": ["throat swab", "throat culture"]},
    {"code": "LAB-042", "name": "Sputum C/S",                   "category": "Microbiology", "aliases": ["sputum culture", "sputum c/s"]},
    {"code": "LAB-043", "name": "Stool Routine Examination",    "category": "Microbiology", "aliases": ["stool re", "stool routine", "stool analysis"]},

    # ── Serology / Hepatitis ──────────────────────────────────────────────────
    {"code": "LAB-050", "name": "Hepatitis B Surface Antigen",  "category": "Serology",     "aliases": ["hbsag", "hepatitis b", "hep b"]},
    {"code": "LAB-051", "name": "Anti-HCV",                     "category": "Serology",     "aliases": ["anti hcv", "hepatitis c", "hep c", "hcv"]},
    {"code": "LAB-052", "name": "HIV 1 & 2",                    "category": "Serology",     "aliases": ["hiv", "hiv test", "hiv 1 2", "aids test"]},
    {"code": "LAB-053", "name": "VDRL / RPR",                   "category": "Serology",     "aliases": ["vdrl", "rpr", "syphilis", "tpha"]},

    # ── Cardiac ───────────────────────────────────────────────────────────────
    {"code": "LAB-060", "name": "Troponin I",                   "category": "Cardiac",      "aliases": ["troponin", "troponin i", "cardiac enzymes"]},
    {"code": "LAB-061", "name": "CK-MB",                        "category": "Cardiac",      "aliases": ["ck mb", "creatine kinase mb", "cardiac mb"]},
    {"code": "LAB-062", "name": "BNP / NT-proBNP",             "category": "Cardiac",      "aliases": ["bnp", "nt probnp", "brain natriuretic"]},

    # ── Hormones ──────────────────────────────────────────────────────────────
    {"code": "LAB-070", "name": "Serum Prolactin",              "category": "Hormones",     "aliases": ["prolactin", "prl"]},
    {"code": "LAB-071", "name": "Testosterone",                 "category": "Hormones",     "aliases": ["testosterone", "total testosterone"]},
    {"code": "LAB-072", "name": "FSH",                          "category": "Hormones",     "aliases": ["fsh", "follicle stimulating hormone"]},
    {"code": "LAB-073", "name": "LH",                           "category": "Hormones",     "aliases": ["lh", "luteinizing hormone"]},

    # ── Vitamins & Minerals ───────────────────────────────────────────────────
    {"code": "LAB-080", "name": "Serum Vitamin D",              "category": "Vitamins",     "aliases": ["vitamin d", "25 ohd", "vit d", "25-hydroxyvitamin d"]},
    {"code": "LAB-081", "name": "Serum Vitamin B12",            "category": "Vitamins",     "aliases": ["vitamin b12", "vit b12", "cobalamin", "b12"]},
    {"code": "LAB-082", "name": "Serum Ferritin",               "category": "Vitamins",     "aliases": ["ferritin", "serum ferritin"]},
    {"code": "LAB-083", "name": "Serum Iron & TIBC",            "category": "Vitamins",     "aliases": ["iron studies", "serum iron", "tibc", "iron profile"]},
    {"code": "LAB-084", "name": "Serum Calcium",                "category": "Vitamins",     "aliases": ["calcium", "serum ca", "ca level"]},

    # ── Covid / Infectious ────────────────────────────────────────────────────
    {"code": "LAB-090", "name": "COVID-19 PCR",                 "category": "Infectious",   "aliases": ["covid pcr", "covid-19 pcr", "sars cov 2 pcr", "rt pcr"]},
    {"code": "LAB-091", "name": "Malaria Antigen / Smear",      "category": "Infectious",   "aliases": ["malaria", "malaria test", "malaria rdt", "malaria smear"]},
    {"code": "LAB-092", "name": "Dengue NS1 / IgM / IgG",      "category": "Infectious",   "aliases": ["dengue", "dengue test", "ns1", "dengue serology"]},
    {"code": "LAB-093", "name": "Typhoid Widal Test",           "category": "Infectious",   "aliases": ["widal", "typhoid test", "widal test"]},
]


def get_all_categories() -> list[str]:
    seen = []
    for t in LAB_TESTS:
        if t["category"] not in seen:
            seen.append(t["category"])
    return seen


def get_tests_by_category(category: str) -> list[dict]:
    return [t for t in LAB_TESTS if t["category"].lower() == category.lower()]


def get_lab_test_by_code(code: str) -> dict | None:
    for t in LAB_TESTS:
        if t["code"].lower() == code.lower():
            return t
    return None


def match_lab_test_from_text(text: str) -> dict | None:
    t = text.lower().strip()
    for test in LAB_TESTS:
        searchable = test["name"].lower() + " " + " ".join(test["aliases"])
        if t in searchable or any(alias in t for alias in test["aliases"]):
            return test
    return None

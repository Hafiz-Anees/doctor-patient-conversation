import os
from dotenv import load_dotenv

load_dotenv()

print("DEBUG POSTGRES_URI =", os.getenv("POSTGRES_URI"))
print("DEBUG GEMINI_API_KEY exists =", bool(os.getenv("GEMINI_API_KEY")))

# ── Gemini ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = "gemini-2.5-flash"

# ── PostgreSQL ────────────────────────────────────────────────────────────────
POSTGRES_URI: str = os.getenv("POSTGRES_URI", "")

# ── Auth ──────────────────────────────────────────────────────────────────────
SECRET_KEY: str = os.getenv("SECRET_KEY", "changeme-secret-key")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8

# ── Hardcoded demo credentials (replace with DB users later) ──────────────────
DEMO_USERS = {
    "emrchain@gmail.com": {"password": "emr1234",    "role": "admin",  "name": "Admin User"},
    "nurse@emrchain.com": {"password": "nurse1234",  "role": "nurse",  "name": "Nurse Demo"},
    "doctor@emrchain.com": {"password": "doctor1234", "role": "doctor", "name": "Dr. Demo"},
}

# ── Sanity checks ─────────────────────────────────────────────────────────────
if not POSTGRES_URI:
    print("⚠️ POSTGRES_URI missing in .env; PostgreSQL features will be disabled")

if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY missing in .env; transcription/summary will fail")


# import os
# from dotenv import load_dotenv

# load_dotenv()


# print("DEBUG MONGO_URI =", os.getenv("MONGO_URI"))
# print("DEBUG MONGO_DB_NAME =", os.getenv("MONGO_DB_NAME"))
# print("DEBUG POSTGRES_URI =", os.getenv("POSTGRES_URI"))
# print("DEBUG GEMINI_API_KEY exists =", bool(os.getenv("GEMINI_API_KEY")))

# # ── Gemini ────────────────────────────────────────────────────────────────────
# GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
# GEMINI_MODEL: str = "gemini-2.0-flash"

# # ── MongoDB ───────────────────────────────────────────────────────────────────
# MONGO_URI: str = os.getenv("MONGO_URI", "")
# MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "doctor_patient_app")

# # ── PostgreSQL ────────────────────────────────────────────────────────────────
# POSTGRES_URI: str = os.getenv("POSTGRES_URI", "")

# # ── Auth ──────────────────────────────────────────────────────────────────────
# SECRET_KEY: str = os.getenv("SECRET_KEY", "changeme-secret-key")
# ALGORITHM: str = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8

# # ── Hardcoded demo credentials (replace with DB users later) ──────────────────
# DEMO_USERS = {
#     "emrchain@gmail.com": {
#         "password": "emr1234",
#         "role": "admin",
#         "name": "Admin User",
#     },
#     "nurse@emrchain.com": {
#         "password": "nurse1234",
#         "role": "nurse",
#         "name": "Nurse Demo",
#     },
#     "doctor@emrchain.com": {
#         "password": "doctor1234",
#         "role": "doctor",
#         "name": "Dr. Demo",
#     },
# }

# if not MONGO_URI:
#     raise ValueError("MONGO_URI missing in .env")

# if not POSTGRES_URI:
#     print("⚠️ POSTGRES_URI missing in .env; PostgreSQL features will be disabled")

# if not GEMINI_API_KEY:
#     print("⚠️ GEMINI_API_KEY missing in .env")
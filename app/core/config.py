import os
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("gemini-2.5-flash","")
POSTGRES_URI: str = os.getenv("POSTGRES_URI", "")

# -------------Sanity checks --------------
if not POSTGRES_URI:
    print("⚠️ POSTGRES_URI missing in .env; PostgreSQL features will be disabled")

if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY missing in .env; transcription/summary will fail")



# ── Auth ─────────────────
SECRET_KEY: str = os.getenv("SECRET_KEY", "changeme-secret-key")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8




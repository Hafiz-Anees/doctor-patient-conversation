from app.core.middleware import HideEmptyFieldsMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import ping_postgres, bootstrap_postgres
from app.core.config import GEMINI_API_KEY
from app.routes.patient import router as patient_router
from app.routes.vitals import router as vitals_router
from app.routes.nurse import router as nurse_router
from app.routes.doctor import router as doctor_router
from app.routes.transcription import router as transcription_router
from app.routes.prescription import router as prescription_router

import google.generativeai as genai # type: ignore
genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI(
    title="HIMS DOCTOR - PATIENT CONVERSATION",
    description=("Medical transcription, vitals extraction, summary generation."),
    docs_url="/docs",
)

app.add_middleware(HideEmptyFieldsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patient_router)
app.include_router(vitals_router)
app.include_router(nurse_router)
app.include_router(doctor_router)
app.include_router(transcription_router)
app.include_router(prescription_router)


@app.on_event("startup")
def on_startup():
    print("\n🚀 EMRChain Backend starting...\n")

    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY missing in .env")
    else:
        print("✅ Gemini API key loaded")

    if ping_postgres():
        print("✅ PostgreSQL connected")
        bootstrap_postgres()
    else:
        print("⚠️ PostgreSQL not available")

@app.get("/")
def root():
    return {
        "message": "HIMS DOCTER-PATIENT CONVERSATION",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "postgres": ping_postgres(),
        "gemini": bool(GEMINI_API_KEY),
    }



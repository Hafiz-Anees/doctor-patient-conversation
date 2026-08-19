from app.core.middleware import HideEmptyFieldsMiddleware
#docstring
"""
main.py — EMRChain Backend entry point (PostgreSQL only).

Run with:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import ping_postgres, bootstrap_postgres
from app.core.config import GEMINI_API_KEY

from app.routes.auth import router as auth_router
from app.routes.patient import router as patient_router
from app.routes.vitals import router as vitals_router
from app.routes.nurse import router as nurse_router
from app.routes.doctor import router as doctor_router
from app.routes.transcription import router as transcription_router
from app.routes.prescription import router as prescription_router
from app.routes.analytics import router as analytics_router
from app.routes.lab_tests import router as lab_tests_router

import google.generativeai as genai # type: ignore
genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI(
    title="EMRChain Medical Backend",
    version="2.0",
    description=(
        "Medical transcription, vitals extraction, summary generation, "
        "prescription, and coding API. Nurse → doctor → merge flow."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(HideEmptyFieldsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(patient_router)
app.include_router(vitals_router)
app.include_router(nurse_router)
app.include_router(doctor_router)
app.include_router(transcription_router)
app.include_router(prescription_router)
app.include_router(analytics_router)
app.include_router(lab_tests_router)


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

    print("\n📖 API docs: http://localhost:8000/docs\n")


@app.get("/")
def root():
    return {
        "message": "EMRChain Medical Backend v2.0",
        "status": "running",
        "docs": "/docs",
        "flow": {
            "1_nurse": "POST /nurse/start-session → POST /nurse/record/{id} → POST /nurse/summary/{id}",
            "2_doctor": "GET /doctor/patient-brief/{mrno} → POST /doctor/start-session → POST /doctor/record/{id} → POST /doctor/summary/{id}",
            "3_merge": "POST /doctor/finalize/{session_id}",
        },
    }


@app.get("/health")
def health():
    return {
        "postgres": ping_postgres(),
        "gemini": bool(GEMINI_API_KEY),
    }


# """
# main.py — EMRChain Backend entry point.

# Run with:
#     uvicorn main:app --reload --port 8000

# Environment variables (put in .env):
#     GEMINI_API_KEY=...
#     MONGO_URI=...
#     POSTGRES_URI=...
#     SECRET_KEY=...
# """
# """
# main.py — EMRChain Backend entry point.
# """

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# from core.database import (
#     ping_mongo, ping_postgres, bootstrap_postgres,
#     frequencies_col, routes_col,
# )
# from core.config import GEMINI_API_KEY
# from tools.frequency_codes import FREQUENCY_CODES
# from tools.route_codes import ROUTE_CODES

# from routes.auth import router as auth_router
# from routes.patient import router as patient_router
# from routes.vitals import router as vitals_router
# from routes.nurse import router as nurse_router
# from routes.doctor import router as doctor_router
# from routes.transcription import router as transcription_router
# from routes.prescription import router as prescription_router
# from routes.analytics import router as analytics_router
# from routes.lab_tests import router as lab_tests_router

# import google.generativeai as genai
# genai.configure(api_key=GEMINI_API_KEY)

# app = FastAPI(
#     title="EMRChain Medical Backend",
#     version="2.0",
#     description=(
#         "Complete medical transcription, vitals extraction, "
#         "summary generation, prescription, and coding API. "
#         "Supports nurse → doctor → merge flow with BLE/Wi-Fi device integration."
#     ),
#     docs_url="/docs",
#     redoc_url="/redoc",
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# app.include_router(auth_router)
# app.include_router(patient_router)
# app.include_router(vitals_router)
# app.include_router(nurse_router)
# app.include_router(doctor_router)
# app.include_router(transcription_router)
# app.include_router(prescription_router)
# app.include_router(analytics_router)
# app.include_router(lab_tests_router)


# @app.on_event("startup")
# def on_startup():
#     print("\n🚀 EMRChain Backend starting...\n")

#     if not GEMINI_API_KEY:
#         print("❌ GEMINI_API_KEY missing in .env")
#     else:
#         print("✅ Gemini API key loaded")

#     if ping_mongo():
#         print("✅ MongoDB connected")
#         _seed_reference_tables()
#     else:
#         print("❌ MongoDB connection failed")

#     if ping_postgres():
#         print("✅ PostgreSQL connected")
#         bootstrap_postgres()
#     else:
#         print("⚠️ PostgreSQL not available (vitals will be PostgreSQL-disabled)")

#     print("\n📖 API docs: http://localhost:8000/docs\n")


# def _seed_reference_tables():
#     freq_count = frequencies_col.count_documents({})
#     if freq_count == 0:
#         frequencies_col.insert_many(FREQUENCY_CODES)
#         print(f"✅ {len(FREQUENCY_CODES)} frequency codes seeded")
#     else:
#         print(f"⚠️ Frequencies already seeded ({freq_count} records)")

#     route_count = routes_col.count_documents({})
#     if route_count == 0:
#         routes_col.insert_many(ROUTE_CODES)
#         print(f"✅ {len(ROUTE_CODES)} route codes seeded")
#     else:
#         print(f"⚠️ Routes already seeded ({route_count} records)")


# @app.get("/")
# def root():
#     return {
#         "message": "EMRChain Medical Backend v2.0",
#         "status": "running",
#         "docs": "/docs",
#         "flow": {
#             "1_nurse": "POST /nurse/start-session → POST /nurse/record/{id} → POST /nurse/summary/{id}",
#             "2_doctor": "GET /doctor/patient-brief/{mrno} → POST /doctor/start-session → POST /doctor/record/{id} → POST /doctor/summary/{id}",
#             "3_merge": "POST /doctor/finalize/{session_id}",
#         },
#     }


# @app.get("/health")
# def health():
#     return {
#         "mongo": ping_mongo(),
#         "postgres": ping_postgres(),
#         "gemini": bool(GEMINI_API_KEY),
#     }
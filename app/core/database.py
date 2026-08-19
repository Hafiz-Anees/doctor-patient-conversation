"""
database.py — PostgreSQL only.  (MongoDB removed.)

Storage layout
--------------
registration.patient_vitals     → vitals (raw SQL via psycopg2)
public.nurse_audio_recordings   → nurse audio + transcription + summary
public.doctor_audio_recordings  → doctor audio + transcription + summary + prescription + icd_codes
"""

import psycopg2
import psycopg2.extras
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import POSTGRES_URI
from core.models import Base, NurseAudioRecording, DoctorAudioRecording

print("Loaded POSTGRES_URI:", POSTGRES_URI)

VITALS_SCHEMA = "registration"   # vitals live here, NOT public

# ── SQLAlchemy (audio tables) ─────────────────────────────────────────────────
try:
    engine = create_engine(POSTGRES_URI)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print("✅ SQLAlchemy engine initialized")
except Exception as e:
    engine = None
    SessionLocal = None
    print(f"⚠️ SQLAlchemy engine failed: {e}")


# ── Raw psycopg2 (vitals) ─────────────────────────────────────────────────────
def get_pg_connection():
    conn = psycopg2.connect(POSTGRES_URI)
    conn.autocommit = False
    return conn


@contextmanager
def pg_cursor():
    conn = get_pg_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ping_postgres() -> bool:
    try:
        with pg_cursor() as cur:
            cur.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL ping failed: {e}")
        return False


# ── Schema bootstrap ──────────────────────────────────────────────────────────
PATIENT_VITALS_DDL = f"""
CREATE TABLE IF NOT EXISTS {VITALS_SCHEMA}.patient_vitals (
    id               SERIAL PRIMARY KEY,
    mrno             INTEGER NOT NULL,
    sr_no            INTEGER,
    entry_date       TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    body_temperature INTEGER,
    heart_rate       INTEGER,
    respiratory_rate INTEGER,
    bp_systolic      INTEGER,
    bp_diastolic     INTEGER,
    weight_kg        NUMERIC(5,1),
    height_cm        NUMERIC(5,1),
    oxygen_level     NUMERIC(4,1),
    session_id       TEXT,
    recorded_by      TEXT DEFAULT 'nurse',
    notes            TEXT,
    nurse_audio_id   INTEGER,
    doctor_audio_id  INTEGER,
    created_at       TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
"""

VITALS_AUDIO_COLS_DDL = f"""
ALTER TABLE {VITALS_SCHEMA}.patient_vitals
    ADD COLUMN IF NOT EXISTS nurse_audio_id  INTEGER,
    ADD COLUMN IF NOT EXISTS doctor_audio_id INTEGER;
"""


def bootstrap_postgres():
    """Create/upgrade tables. Safe to run on every startup."""
    try:
        with pg_cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {VITALS_SCHEMA}")
            cur.execute(PATIENT_VITALS_DDL)
            cur.execute(VITALS_AUDIO_COLS_DDL)
        if engine:
            Base.metadata.create_all(bind=engine)   # public audio tables
            print("✅ PostgreSQL tables ready (vitals + nurse/doctor audio)")
        else:
            print("⚠️ SQLAlchemy engine missing — audio tables not created")
    except Exception as e:
        print(f"⚠️ PostgreSQL bootstrap error: {e}")


# ── Nurse audio helpers ───────────────────────────────────────────────────────
def save_nurse_audio(session_id: str, mrno: int, audio_bytes: bytes = None,
                     file_name: str = "nurse_recording.wav",
                     content_type: str = "audio/wav") -> int:
    """Create a nurse row and store the raw audio bytes."""
    if not SessionLocal:
        raise Exception("SQLAlchemy not initialized")
    db = SessionLocal()
    try:
        rec = NurseAudioRecording(
            session_id=session_id, mrno=mrno, audio_data=audio_bytes,
            file_name=file_name,
            file_size=len(audio_bytes) if audio_bytes else None,
            content_type=content_type,
        )
        db.add(rec); db.commit(); db.refresh(rec)
        return rec.id
    except Exception:
        db.rollback(); raise
    finally:
        db.close()


def update_nurse_audio(audio_id: int, **fields) -> bool:
    """Patch transcription / summary / language on a nurse row."""
    if not SessionLocal or audio_id is None:
        return False
    db = SessionLocal()
    try:
        rec = db.query(NurseAudioRecording).get(audio_id)
        if not rec:
            return False
        for k, v in fields.items():
            if hasattr(rec, k):
                setattr(rec, k, v)
        db.commit()
        return True
    except Exception:
        db.rollback(); raise
    finally:
        db.close()


def get_latest_nurse_record_by_mrno(mrno: int) -> dict | None:
    """Most recent nurse row for a patient (used by doctor patient-brief / finalize)."""
    if not SessionLocal:
        return None
    db = SessionLocal()
    try:
        rec = (db.query(NurseAudioRecording)
                 .filter(NurseAudioRecording.mrno == mrno)
                 .order_by(NurseAudioRecording.created_at.desc())
                 .first())
        if not rec:
            return None
        return {
            "id": rec.id, "session_id": rec.session_id, "mrno": rec.mrno,
            "language": rec.language, "transcription": rec.transcription,
            "summary": rec.summary, "created_at": str(rec.created_at),
        }
    finally:
        db.close()


# ── Doctor audio helpers ──────────────────────────────────────────────────────
def save_doctor_audio(session_id: str, mrno: int, audio_bytes: bytes = None,
                      nurse_session_id: str = "",
                      file_name: str = "doctor_recording.wav",
                      content_type: str = "audio/wav") -> int:
    """Create a doctor row and store the raw audio bytes."""
    if not SessionLocal:
        raise Exception("SQLAlchemy not initialized")
    db = SessionLocal()
    try:
        rec = DoctorAudioRecording(
            session_id=session_id, mrno=mrno, nurse_session_id=nurse_session_id,
            audio_data=audio_bytes, file_name=file_name,
            file_size=len(audio_bytes) if audio_bytes else None,
            content_type=content_type,
        )
        db.add(rec); db.commit(); db.refresh(rec)
        return rec.id
    except Exception:
        db.rollback(); raise
    finally:
        db.close()


def update_doctor_audio(audio_id: int, **fields) -> bool:
    """Patch transcription / summary / prescription / icd_codes / language."""
    if not SessionLocal or audio_id is None:
        return False
    db = SessionLocal()
    try:
        rec = db.query(DoctorAudioRecording).get(audio_id)
        if not rec:
            return False
        for k, v in fields.items():
            if hasattr(rec, k):
                setattr(rec, k, v)
        db.commit()
        return True
    except Exception:
        db.rollback(); raise
    finally:
        db.close()


def _doctor_row_to_record(rec: DoctorAudioRecording) -> dict:
    return {
        "record_id": rec.session_id,
        "id": rec.id,
        "session_id": rec.session_id,
        "mrno": rec.mrno,
        "nurse_session_id": rec.nurse_session_id,
        "language": rec.language,
        "transcription": rec.transcription,
        "summary": rec.summary,
        "merged_summary": rec.merged_summary,
        "prescription": rec.prescription,
        "icd_codes": rec.icd_codes,
        "created_at": str(rec.created_at),
    }


def get_doctor_record_by_session(session_id: str) -> dict | None:
    if not SessionLocal:
        return None
    db = SessionLocal()
    try:
        rec = (db.query(DoctorAudioRecording)
                 .filter(DoctorAudioRecording.session_id == session_id)
                 .order_by(DoctorAudioRecording.created_at.desc())
                 .first())
        return _doctor_row_to_record(rec) if rec else None
    finally:
        db.close()


def get_doctor_records_by_mrno(mrno: int, limit: int = 20) -> list[dict]:
    if not SessionLocal:
        return []
    db = SessionLocal()
    try:
        rows = (db.query(DoctorAudioRecording)
                  .filter(DoctorAudioRecording.mrno == mrno)
                  .order_by(DoctorAudioRecording.created_at.desc())
                  .limit(limit).all())
        return [_doctor_row_to_record(r) for r in rows]
    finally:
        db.close()



# """
# database.py — single place for all DB connections.

# MongoDB  → transcriptions, sessions, prescriptions, summaries
# PostgreSQL → patient_vitals (structured medical data with real types)
# """

# from pymongo import MongoClient
# from pymongo.server_api import ServerApi
# from pymongo.database import Database
# import psycopg2
# import psycopg2.extras
# from contextlib import contextmanager
# from core.config import MONGO_URI, MONGO_DB_NAME, POSTGRES_URI

# # ── MongoDB ───────────────────────────────────────────────────────────────────
# from core.config import POSTGRES_URI

# # ✅ ADD THESE NEW IMPORTS
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, Session
# from core.models import Base, AudioRecording

# print("Loaded POSTGRES_URI:", POSTGRES_URI)

# _mongo_client: MongoClient | None = None


# def get_mongo_client() -> MongoClient:
#     global _mongo_client
#     if _mongo_client is None:
#         _mongo_client = MongoClient(MONGO_URI, server_api=ServerApi("1"))
#     return _mongo_client


# def get_mongo_db() -> Database:
#     return get_mongo_client()[MONGO_DB_NAME]


# def ping_mongo() -> bool:
#     try:
#         get_mongo_client().admin.command("ping")
#         return True
#     except Exception as e:
#         print(f"❌ MongoDB ping failed: {e}")
#         return False


# # Convenience handles (used across the app like: from core.database import mongo_db)
# mongo_db = get_mongo_db()

# transcriptions_col   = mongo_db["transcriptions"]
# sessions_col         = mongo_db["sessions"]          # nurse & doctor sessions
# prescriptions_col    = mongo_db["prescriptions"]
# medical_records_col  = mongo_db["medical_records"]   # final merged records
# patients_col         = mongo_db["patients"]
# frequencies_col      = mongo_db["frequencies"]
# routes_col           = mongo_db["routes"]

# # ✅ ADD SQLAlchemy engine setup (add after your existing pg_cursor function)
# try:
#     engine = create_engine(POSTGRES_URI)
#     SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#     print("✅ SQLAlchemy engine initialized")
# except Exception as e:
#     engine = None
#     SessionLocal = None
#     print(f"⚠️ SQLAlchemy engine failed: {e}")

# # ── PostgreSQL ────────────────────────────────────────────────────────────────

# def get_pg_connection():
#     """Return a raw psycopg2 connection. Caller must close."""
#     conn = psycopg2.connect(POSTGRES_URI)
#     conn.autocommit = False
#     return conn


# @contextmanager
# def pg_cursor():
#     """Context manager: yields a DictCursor, commits on exit, rolls back on error."""
#     conn = get_pg_connection()
#     try:
#         with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
#             yield cur
#         conn.commit()
#     except Exception:
#         conn.rollback()
#         raise
#     finally:
#         conn.close()


# def ping_postgres() -> bool:
#     try:
#         with pg_cursor() as cur:
#             cur.execute("SELECT 1")
#         return True
#     except Exception as e:
#         print(f"❌ PostgreSQL ping failed: {e}")
#         return False


# # ── Schema bootstrap (run once on startup) ───────────────────────────────────

# PATIENT_VITALS_DDL = """
# CREATE TABLE IF NOT EXISTS patient_vitals (
#     id               SERIAL PRIMARY KEY,
#     mrno             INTEGER NOT NULL,
#     sr_no            INTEGER,
#     entry_date       TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
#     body_temperature INTEGER,          -- Fahrenheit
#     heart_rate       INTEGER,          -- bpm
#     respiratory_rate INTEGER,          -- breaths/min
#     bp_systolic      INTEGER,
#     bp_diastolic     INTEGER,
#     weight_kg        NUMERIC(5,1),
#     height_cm        NUMERIC(5,1),
#     oxygen_level     NUMERIC(4,1),     -- percentage
#     session_id       TEXT,
#     recorded_by      TEXT DEFAULT 'nurse',
#     notes            TEXT,
#     created_at       TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
# );
# """

# NURSE_SESSIONS_DDL = """
# CREATE TABLE IF NOT EXISTS nurse_sessions (
#     id           SERIAL PRIMARY KEY,
#     session_id   TEXT UNIQUE NOT NULL,
#     mrno         INTEGER NOT NULL,
#     started_at   TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
#     ended_at     TIMESTAMP WITHOUT TIME ZONE,
#     status       TEXT DEFAULT 'active',  -- active | completed | cancelled
#     summary_id   TEXT                    -- points to MongoDB document
# );
# """

# DOCTOR_SESSIONS_DDL = """
# CREATE TABLE IF NOT EXISTS doctor_sessions (
#     id                SERIAL PRIMARY KEY,
#     session_id        TEXT UNIQUE NOT NULL,
#     mrno              INTEGER NOT NULL,
#     nurse_session_id  TEXT,
#     started_at        TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
#     ended_at          TIMESTAMP WITHOUT TIME ZONE,
#     status            TEXT DEFAULT 'active',
#     summary_id        TEXT,
#     record_id         TEXT    -- points to final merged record in MongoDB
# );
# """


# def bootstrap_postgres():
#     """Create tables if they don't exist. Called on app startup."""
#     try:
#         with pg_cursor() as cur:
#             cur.execute(PATIENT_VITALS_DDL)
#             cur.execute(NURSE_SESSIONS_DDL)
#             cur.execute(DOCTOR_SESSIONS_DDL)
#         print("✅ PostgreSQL tables ready")
#     except Exception as e:
#         print(f"⚠️  PostgreSQL bootstrap skipped (no PG configured?): {e}")



# def bootstrap_postgres():
#     """Create tables if they don't exist. Called on app startup."""
#     try:
#         with pg_cursor() as cur:
#             cur.execute(PATIENT_VITALS_DDL)
#             cur.execute(NURSE_SESSIONS_DDL)
#             cur.execute(DOCTOR_SESSIONS_DDL)
        
#         # ✅ ADD: Create audio_recordings table using SQLAlchemy
#         if engine:
#             Base.metadata.create_all(bind=engine)
#             print("✅ PostgreSQL tables ready (including audio_recordings)")
#         else:
#             print("✅ PostgreSQL tables ready (vitals only, no SQLAlchemy)")
            
#     except Exception as e:
#         print(f"⚠️  PostgreSQL bootstrap skipped (no PG configured?): {e}")


# # ✅ ADD: Audio recording functions

# def save_audio_to_postgres(
#     session_id: str,
#     session_type: str,
#     mrno: int,
#     audio_bytes: bytes,
#     file_name: str = "recording.wav"
# ) -> int:
#     """
#     Save audio recording to PostgreSQL.
#     Returns the inserted record ID.
#     """
#     if not SessionLocal:
#         raise Exception("SQLAlchemy not initialized - cannot save audio")
    
#     db = SessionLocal()
#     try:
#         recording = AudioRecording(
#             session_id=session_id,
#             session_type=session_type,
#             mrno=mrno,
#             audio_data=audio_bytes,
#             file_name=file_name,
#             file_size=len(audio_bytes),
#             content_type="audio/wav"
#         )
        
#         db.add(recording)
#         db.commit()
#         db.refresh(recording)
        
#         record_id = recording.id
#         print(f"✅ Audio saved to PostgreSQL: ID={record_id}, Size={len(audio_bytes)} bytes")
#         return record_id
        
#     except Exception as e:
#         db.rollback()
#         print(f"❌ Failed to save audio to PostgreSQL: {e}")
#         raise
#     finally:
#         db.close()


# def get_audio_from_postgres(session_id: str) -> dict:
#     """Retrieve audio recording by session_id"""
#     if not SessionLocal:
#         return None
    
#     db = SessionLocal()
#     try:
#         recording = db.query(AudioRecording).filter(
#             AudioRecording.session_id == session_id
#         ).first()
        
#         if recording:
#             return {
#                 "id": recording.id,
#                 "session_id": recording.session_id,
#                 "session_type": recording.session_type,
#                 "mrno": recording.mrno,
#                 "audio_data": recording.audio_data,
#                 "file_name": recording.file_name,
#                 "file_size": recording.file_size,
#                 "content_type": recording.content_type,
#                 "created_at": recording.created_at
#             }
#         return None
        
#     except Exception as e:
#         print(f"❌ Failed to retrieve audio: {e}")
#         return None
#     finally:
#         db.close()


# def get_audio_by_mrno(mrno: int, limit: int = 10) -> list:
#     """Get all audio recordings for a patient"""
#     if not SessionLocal:
#         return []
    
#     db = SessionLocal()
#     try:
#         recordings = db.query(AudioRecording).filter(
#             AudioRecording.mrno == mrno
#         ).order_by(AudioRecording.created_at.desc()).limit(limit).all()
        
#         return [{
#             "id": r.id,
#             "session_id": r.session_id,
#             "session_type": r.session_type,
#             "file_size": r.file_size,
#             "created_at": r.created_at
#         } for r in recordings]
        
#     except Exception as e:
#         print(f"❌ Failed to get audio by MRNO: {e}")
#         return []
#     finally:
#         db.close()


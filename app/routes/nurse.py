"""
routes/nurse.py — nurse workflow (PostgreSQL only, no Mongo).

POST  /nurse/start-session
POST  /nurse/record/{session_id}
PATCH /nurse/edit/{session_id}
POST  /nurse/summary/{session_id}
GET   /nurse/summary/{session_id}
POST  /nurse/device-stream
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, HTTPException, Request

from app.core.database import save_nurse_audio, update_nurse_audio
from app.models.session import NurseSessionStart, EditTranscriptRequest
from app.services.transcription_service import transcribe_from_bytes, transcribe_pcm_stream
from app.services.vitals_service import (
    extract_vitals_from_transcript, vitals_extracted_to_db,
    save_vitals_to_db, get_latest_vitals,
)
from app.services.summary_service import generate_summary, translate_transcript
from app.services.patient_service import extract_and_save_demographics
from app.utils.session_store import create_session, update_session, require_session, require_summary

router = APIRouter(prefix="/nurse", tags=["Nurse"])


@router.post("/start-session")
def start_session(data: NurseSessionStart):
    session_id = str(uuid.uuid4())
    create_session(session_id, {
        "session_id": session_id, "mrno": data.mrno, "emr_id": data.emr_id or "",
        "clinic": getattr(data, "clinic", "") or "",
        "role": "nurse", "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    })
    return {"status": "success", "session_id": session_id, "mrno": data.mrno}


@router.post("/record/{session_id}")
async def record_audio(session_id: str, file: UploadFile):
    session = require_session(session_id)
    mrno = session.get("mrno", 0)

    audio_bytes = await file.read()

    audio_id, audio_error = None, None
    try:
        audio_id = save_nurse_audio(session_id, mrno, audio_bytes,
                                    file.filename or "nurse_recording.wav")
        print(f"✅ Nurse audio saved: ID={audio_id}")
    except Exception as e:
        audio_error = str(e)
        print(f"❌ Nurse audio save failed: {audio_error}")

    result = await transcribe_from_bytes(
        audio_bytes=audio_bytes,
        filename=file.filename or "recording.wav",
        role="nurse", mrno=mrno,
    )
    transcription, language = result["transcription"], result["language"]

    update_session(session_id, {
        "transcription": transcription, "language": language,
        "is_verified": False, "audio_id": audio_id,
        "audio_filename": file.filename, "audio_size": len(audio_bytes),
    })
    update_nurse_audio(audio_id, transcription=transcription, language=language)

    extracted = await extract_vitals_from_transcript(transcription)
    vitals_db = vitals_extracted_to_db(extracted, mrno, session_id, "nurse",
                                       nurse_audio_id=audio_id)
    vitals_id, pg_error = None, None
    try:
        vitals_id = save_vitals_to_db(vitals_db)
        update_session(session_id, {
            "vitals_extracted": extracted.model_dump(), "vitals_db_id": vitals_id,
        })
    except Exception as e:
        pg_error = str(e)
        print("POSTGRES SAVE ERROR:", pg_error)
        update_session(session_id, {
            "vitals_extracted": extracted.model_dump(), "vitals_pg_error": pg_error,
        })

    # Demographics: extract from transcript, save into registration.patient
    # (insert if new mrno, update only mentioned fields if existing).
    patient_saved, patient_pg_error = None, None
    try:
        patient_saved = await extract_and_save_demographics(
            mrno, transcription, clinic=session.get("clinic", ""))
    except Exception as e:
        patient_pg_error = str(e)
        print("PATIENT SAVE ERROR:", patient_pg_error)

    return {
        "status": "success", "session_id": session_id, "language": language,
        "transcription": transcription, "audio_id": audio_id,
        "audio_size": len(audio_bytes), "audio_error": audio_error,
        "vitals_extracted": extracted.model_dump(),
        "vitals_saved_id": vitals_id, "vitals_pg_error": pg_error,
        "patient_saved": patient_saved, "patient_pg_error": patient_pg_error,
    }


@router.post("/device-stream")
async def receive_device_stream(request: Request):
    chunks = [c async for c in request.stream()]
    raw_bytes = b"".join(chunks)
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Empty audio stream")

    mrno = int(request.headers.get("x-mrno", "0"))
    device_id = request.headers.get("x-device-id", "")
    mac_address = request.headers.get("x-mac-address", "")
    clinic = request.headers.get("x-clinic", "")
    session_id = str(uuid.uuid4())

    audio_id = None
    try:
        audio_id = save_nurse_audio(session_id, mrno, raw_bytes,
                                    f"device_{device_id}_{session_id[:8]}.pcm")
    except Exception as e:
        print(f"⚠️ Device audio save failed: {e}")

    result = await transcribe_pcm_stream(raw_bytes, role="nurse", mrno=mrno)
    transcription = result["transcription"]
    result["session_id"] = session_id

    update_nurse_audio(audio_id, transcription=transcription,
                       language=result["language"])

    extracted = await extract_vitals_from_transcript(transcription)
    vitals_db = vitals_extracted_to_db(extracted, mrno, session_id, "device",
                                       nurse_audio_id=audio_id)
    vitals_id, pg_error = None, None
    try:
        vitals_id = save_vitals_to_db(vitals_db)
    except Exception as e:
        pg_error = str(e)

    patient_saved, patient_pg_error = None, None
    try:
        patient_saved = await extract_and_save_demographics(mrno, transcription, clinic=clinic)
    except Exception as e:
        patient_pg_error = str(e)

    create_session(session_id, {
        "session_id": session_id, "mrno": mrno, "role": "nurse", "source": "device",
        "device_id": device_id, "mac_address": mac_address, "audio_id": audio_id,
        "audio_size": len(raw_bytes), "transcription": transcription,
        "language": result["language"], "vitals_extracted": extracted.model_dump(),
        "vitals_saved_id": vitals_id, "vitals_pg_error": pg_error,
        "started_at": datetime.now(timezone.utc).isoformat(), "status": "recorded",
    })

    return {
        "status": "success", "session_id": session_id, "device_id": device_id,
        "mrno": mrno, "audio_id": audio_id, "audio_size": len(raw_bytes),
        "transcription": transcription, "vitals_extracted": extracted.model_dump(),
        "vitals_saved_id": vitals_id, "vitals_pg_error": pg_error,
        "patient_saved": patient_saved, "patient_pg_error": patient_pg_error,
    }


@router.patch("/edit/{session_id}")
def edit_transcript(session_id: str, data: EditTranscriptRequest):
    if not update_session(session_id, {"transcription": data.new_text, "is_verified": True}):
        raise HTTPException(status_code=404, detail="Session not found")
    session = require_session(session_id)
    update_nurse_audio(session.get("audio_id"), transcription=data.new_text)
    return {"status": "success", "session_id": session_id,
            "message": "Transcript updated", "new_text": data.new_text}


@router.post("/summary/{session_id}")
async def generate_nurse_summary(session_id: str, target_language: str = "English"):
    session = require_session(session_id)
    if "transcription" not in session:
        raise HTTPException(status_code=400, detail="No transcription found. Upload audio first.")

    mrno = session.get("mrno", 0)
    emr_id = session.get("emr_id", "")

    pre_vitals = None
    try:
        pre_vitals = get_latest_vitals(mrno)
    except Exception:
        pass

    transcript = await translate_transcript(
        session["transcription"], session.get("language", "english"), target_language)

    summary = await generate_summary(
        transcript=transcript, target_language=target_language,
        role="nurse", emr_id=emr_id, mrno=mrno, pre_filled_vitals=pre_vitals)

    update_session(session_id, {"summary": summary, "summary_language": target_language})
    update_nurse_audio(session.get("audio_id"), summary=summary)

    return {"status": "success", "session_id": session_id, "mrno": mrno, "summary": summary}


@router.get("/summary/{session_id}")
def get_nurse_summary(session_id: str):
    return {"status": "success", "session_id": session_id,
            "summary": require_summary(session_id)}
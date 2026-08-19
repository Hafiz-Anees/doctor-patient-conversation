"""
routes/doctor.py — doctor workflow (PostgreSQL only, no Mongo).

GET   /doctor/patient-brief/{mrno}
POST  /doctor/start-session
POST  /doctor/record/{session_id}
PATCH /doctor/edit/{session_id}
POST  /doctor/summary/{session_id}
POST  /doctor/finalize/{session_id}
GET   /doctor/record/{record_id}
GET   /doctor/records/patient/{mrno}
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, UploadFile, HTTPException

from core.database import (
    save_doctor_audio, update_doctor_audio,
    get_latest_nurse_record_by_mrno, get_doctor_record_by_session,
)
from services.transcription_service import transcribe_from_bytes
from services.summary_service import generate_summary, translate_transcript
from services.vitals_service import (
    get_latest_vitals, extract_vitals_from_transcript,
    update_doctor_vitals_on_nurse_row,
)
from services.prescription_service import extract_raw_medications, build_prescription
from services.coding_service import generate_medical_codes
from services.merge_service import merge_summaries, get_medical_record, get_patient_records
from services.patient_service import extract_and_save_demographics
from utils.session_store import (
    create_session, update_session, require_session, require_summary, get_session,
)
from utils.json_helpers import keep_keys
from models.session import DoctorSessionStart, EditTranscriptRequest

router = APIRouter(prefix="/doctor", tags=["Doctor"])


@router.get("/patient-brief/{mrno}")
def patient_brief(mrno: int, nurse_session_id: Optional[str] = None):
    latest_vitals = None
    try:
        latest_vitals = get_latest_vitals(mrno)
    except Exception as e:
        latest_vitals = {"error": str(e)}

    nurse_summary = None
    if nurse_session_id:
        s = get_session(nurse_session_id)
        if s:
            nurse_summary = s.get("summary")

    if not nurse_summary:
        nrec = get_latest_nurse_record_by_mrno(mrno)
        if nrec:
            nurse_summary = nrec.get("summary")
            nurse_session_id = nurse_session_id or nrec.get("session_id")

    return {
        "status": "success", "mrno": mrno, "nurse_session_id": nurse_session_id,
        "latest_vitals": latest_vitals, "nurse_summary": nurse_summary,
    }


@router.post("/start-session")
def start_session(data: DoctorSessionStart):
    session_id = str(uuid.uuid4())
    create_session(session_id, {
        "session_id": session_id, "mrno": data.mrno,
        "nurse_session_id": data.nurse_session_id or "", "role": "doctor",
        "clinic": getattr(data, "clinic", "") or "",
        "started_at": datetime.now(timezone.utc).isoformat(), "status": "active",
    })
    return {"status": "success", "session_id": session_id, "mrno": data.mrno}


@router.post("/record/{session_id}")
async def record_audio(session_id: str, file: UploadFile):
    session = require_session(session_id)
    mrno = session.get("mrno", 0)
    nurse_sid = session.get("nurse_session_id", "")

    audio_bytes = await file.read()

    audio_id = None
    try:
        audio_id = save_doctor_audio(session_id, mrno, audio_bytes,
                                     nurse_session_id=nurse_sid,
                                     file_name=file.filename or "doctor_recording.wav")
        print(f"✅ Doctor audio saved: ID={audio_id}")
    except Exception as e:
        print(f"❌ Doctor audio save failed: {e}")

    result = await transcribe_from_bytes(
        audio_bytes=audio_bytes, filename=file.filename or "recording.wav",
        role="doctor", mrno=mrno, nurse_session_id=nurse_sid)

    update_session(session_id, {
        "transcription": result["transcription"], "language": result["language"],
        "is_verified": False, "audio_id": audio_id,
        "audio_filename": file.filename, "audio_size": len(audio_bytes),
    })
    update_doctor_audio(audio_id, transcription=result["transcription"],
                        language=result["language"])

    # Doctor vitals: extract from doctor transcript and UPDATE the nurse's vitals
    # row for this visit (adds doctor_audio_id + any vitals the doctor stated).
    doctor_vitals, doctor_vitals_error = None, None
    try:
        # locate the linked nurse audio id (for precise row match)
        nurse_audio_id = None
        if nurse_sid:
            ns = get_session(nurse_sid)
            if ns:
                nurse_audio_id = ns.get("audio_id")
        if nurse_audio_id is None:
            nrec = get_latest_nurse_record_by_mrno(mrno)
            if nrec:
                nurse_audio_id = nrec.get("id")

        extracted = await extract_vitals_from_transcript(result["transcription"])
        doctor_vitals = update_doctor_vitals_on_nurse_row(
            mrno=mrno, doctor_audio_id=audio_id,
            extracted=extracted, nurse_audio_id=nurse_audio_id,
        )
        doctor_vitals["extracted"] = extracted.model_dump()
    except Exception as e:
        doctor_vitals_error = str(e)
        print("DOCTOR VITALS UPDATE ERROR:", doctor_vitals_error)

    patient_saved, patient_pg_error = None, None
    try:
        patient_saved = await extract_and_save_demographics(
            mrno, result["transcription"], clinic=session.get("clinic", ""))
    except Exception as e:
        patient_pg_error = str(e)
        print("PATIENT SAVE ERROR:", patient_pg_error)

    return {
        "status": "success", "session_id": session_id, "language": result["language"],
        "transcription": result["transcription"], "audio_id": audio_id,
        "audio_size": len(audio_bytes),
        "doctor_vitals": doctor_vitals, "doctor_vitals_error": doctor_vitals_error,
        "patient_saved": patient_saved, "patient_pg_error": patient_pg_error,
    }


@router.patch("/edit/{session_id}")
def edit_transcript(session_id: str, data: EditTranscriptRequest):
    if not update_session(session_id, {"transcription": data.new_text, "is_verified": True}):
        raise HTTPException(status_code=404, detail="Session not found")
    session = require_session(session_id)
    update_doctor_audio(session.get("audio_id"), transcription=data.new_text)
    return {"status": "success", "session_id": session_id, "new_text": data.new_text}


@router.post("/summary/{session_id}")
async def generate_doctor_summary(session_id: str, target_language: str = "English"):
    session = require_session(session_id)
    if "transcription" not in session:
        raise HTTPException(status_code=400, detail="No transcription. Upload audio first.")

    mrno = session.get("mrno", 0)
    pre_vitals = None
    try:
        pre_vitals = get_latest_vitals(mrno)
    except Exception:
        pass

    transcript = await translate_transcript(
        session["transcription"], session.get("language", "english"), target_language)

    summary = await generate_summary(
        transcript=transcript, target_language=target_language,
        role="doctor", emr_id="", mrno=mrno, pre_filled_vitals=pre_vitals)

    update_session(session_id, {"summary": summary, "summary_language": target_language})
    update_doctor_audio(session.get("audio_id"), summary=summary)

    return {"status": "success", "session_id": session_id, "summary": summary}


@router.post("/finalize/{session_id}")
async def finalize_visit(session_id: str, nurse_session_id: Optional[str] = None,
                         generate_codes: bool = True):
    doctor_session = require_session(session_id)
    doctor_summary = require_summary(session_id)
    mrno = doctor_session.get("mrno", 0)
    audio_id = doctor_session.get("audio_id")

    nurse_sid = nurse_session_id or doctor_session.get("nurse_session_id", "")
    nurse_summary = None
    if nurse_sid:
        ns = get_session(nurse_sid)
        if ns:
            nurse_summary = ns.get("summary")
    if not nurse_summary:
        nrec = get_latest_nurse_record_by_mrno(mrno)
        if nrec:
            nurse_summary = nrec.get("summary")
            nurse_sid = nrec.get("session_id", nurse_sid)
    nurse_summary = nurse_summary or {}

    merged_record = await merge_summaries(
        nurse_summary=nurse_summary, doctor_summary=doctor_summary,
        mrno=mrno, nurse_session_id=nurse_sid, doctor_session_id=session_id)

    merged_note = merged_record.get("merged_record", doctor_summary)
    raw_meds = await extract_raw_medications(merged_note)
    prescription = build_prescription(merged_note, raw_meds, session_id)

    codes = {}
    if generate_codes:
        codes = await generate_medical_codes(merged_note)

    # Persist on the doctor audio row: keep doctor's own summary, store the
    # merged note separately, plus prescription + icd codes.
    # If the in-memory session lost audio_id, resolve the row by session_id.
    if audio_id is None:
        rec = get_doctor_record_by_session(session_id)
        if rec:
            audio_id = rec.get("id")

    persisted = update_doctor_audio(audio_id, merged_summary=merged_note,
                                    prescription=prescription, icd_codes=codes)
    if not persisted:
        print(f"⚠️ Finalize: merged record NOT saved (audio_id={audio_id}, "
              f"session={session_id}). Doctor audio row may be missing.")

    update_session(session_id, {
        "status": "finalized", "record_id": session_id,
        "prescription": prescription, "codes": codes, "merged_record": merged_note,
    })

    FIELDS_TO_SHOW = ["Visit Summary"]
    merged_note_display = keep_keys(merged_note, FIELDS_TO_SHOW)

    return {
        "status": "success", "record_id": session_id, "mrno": mrno,
        "persisted": persisted, "doctor_audio_id": audio_id,
        "merged_record": {**merged_record, "merged_record": merged_note_display},
        "codes": codes,
    }


@router.get("/record/{record_id}")
def get_record(record_id: str):
    record = get_medical_record(record_id)   # record_id == doctor session_id
    if not record:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
    return {"status": "success", "record": record}


@router.get("/records/patient/{mrno}")
def get_patient_records_endpoint(mrno: int):
    records = get_patient_records(mrno)
    return {"status": "success", "total": len(records), "records": records}
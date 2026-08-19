"""
routes/transcription.py — standalone transcription endpoints (legacy + shared).
"""

from fastapi import APIRouter, UploadFile, Form, HTTPException

from services.transcription_service import transcribe_upload
from services.summary_service import translate_transcript, generate_summary
from utils.session_store import require_session, update_session, get_session

router = APIRouter(prefix="/transcription", tags=["Transcription"])


@router.post("/upload")
async def upload_audio(file: UploadFile):
    """Generic transcription — not tied to nurse/doctor flow."""
    result = await transcribe_upload(file, role="general")
    return {
        "status":        "success",
        "session_id":    result["session_id"],
        "language":      result["language"],
        "transcription": result["transcription"],
    }


@router.patch("/edit/{session_id}")
async def edit_transcript(session_id: str, new_text: str = Form(...)):
    if not update_session(session_id, {"transcription": new_text, "is_verified": True}):
        raise HTTPException(404, "Session not found")
    return {"status": "success", "session_id": session_id, "updated_transcription": new_text}


@router.post("/translate/{session_id}")
async def translate(session_id: str, target_language: str = Form(...)):
    session = require_session(session_id)
    translation = await translate_transcript(
        session["transcription"],
        session.get("language", "english"),
        target_language,
    )
    update_session(session_id, {"translation": translation, "translated_language": target_language})
    return {
        "status":          "success",
        "session_id":      session_id,
        "source_language": session.get("language"),
        "target_language": target_language,
        "translation":     translation,
    }


@router.post("/summary/{session_id}")
async def summarize(session_id: str, target_language: str = Form("English"),
                    emr_id: str = Form("")):
    session = require_session(session_id)
    summary = await generate_summary(
        transcript=session["transcription"],
        target_language=target_language,
        role="doctor",
        emr_id=emr_id,
    )
    update_session(session_id, {"summary": summary})
    return {"status": "success", "session_id": session_id, "summary": summary}


@router.get("/session/{session_id}")
def get_session_data(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {"status": "success", "session": session}

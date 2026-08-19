"""
transcription_service.py — audio → text via Gemini.
Handles both regular file upload and raw PCM stream from the device.
"""

import os
import uuid
import tempfile
import google.generativeai as genai

from app.core.config import GEMINI_API_KEY, GEMINI_MODEL
from app.utils.audio_helpers import save_upload, cleanup_file, strip_pcm_markers, pcm_to_wav_bytes
from app.utils.session_store import create_session

genai.configure(api_key=GEMINI_API_KEY)

print("TRANSCRIPTION SERVICE - API key exists:", bool(GEMINI_API_KEY))
print("TRANSCRIPTION SERVICE - API key length:", len(GEMINI_API_KEY))

# Maps a file extension to the MIME type Gemini expects. Add more here if
# you need to support another audio format later.
AUDIO_MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".mpeg": "audio/mpeg",
    ".mpga": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".webm": "audio/webm",
}

async def transcribe_audio_file(audio_path: str) -> tuple[str, str]:
    model = genai.GenerativeModel(GEMINI_MODEL)

    ext = os.path.splitext(audio_path)[1].lower()
    mime_type = AUDIO_MIME_TYPES.get(ext, "audio/wav")

    with open(audio_path, "rb") as f:
        audio_file = {
            "mime_type": mime_type,
            "data": f.read(),
        }

    response = model.generate_content([
        "Transcribe this audio file accurately in its ORIGINAL language. "
        "If the audio is in Urdu, transcribe in Urdu script (اردو). "
        "If it's in English, transcribe in English. "
        "If it's mixed, keep each part in its original language. "
        "Preserve all medical terms exactly as spoken.",
        audio_file,
    ])

    transcription = response.text.strip()

    lang_response = model.generate_content(
        f"Detect the language of this text and return ONLY the language name "
        f"(e.g. English, Urdu, Arabic):\n\n{transcription}"
    )

    language = lang_response.text.strip().lower()

    return transcription, language


async def transcribe_upload(file, role: str = "general", mrno: int = 0,
                            nurse_session_id: str = "") -> dict:
    """
    Full pipeline: save upload → transcribe → create session.
    Returns session dict.
    
    ⚠️ IMPORTANT: This function reads from the file object.
    If you've already read the file before calling this, you need to
    either pass the bytes or reset the file pointer.
    """
    temp_path = None
    try:
        suffix = os.path.splitext(file.filename or "")[1] or ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name

        save_upload(file, temp_path)
        transcription, language = await transcribe_audio_file(temp_path)
    finally:
        if temp_path:
            cleanup_file(temp_path)

    session_id = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "transcription": transcription,
        "language": language,
        "role": role,
        "mrno": mrno,
        "nurse_session_id": nurse_session_id,
        "is_verified": False,
    }
    create_session(session_id, session_data)
    return session_data

# ✅ NEW FUNCTION: Accept bytes directly
async def transcribe_from_bytes(audio_bytes: bytes, filename: str = "recording.wav",
                               role: str = "general", mrno: int = 0,
                               nurse_session_id: str = "") -> dict:
    """
    Transcribe audio from raw bytes.
    Use this when you've already read the file bytes.
    """
    temp_path = None
    try:
        suffix = os.path.splitext(filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
            tmp.write(audio_bytes)

        transcription, language = await transcribe_audio_file(temp_path)
    finally:
        if temp_path:
            cleanup_file(temp_path)

    session_id = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "transcription": transcription,
        "language": language,
        "role": role,
        "mrno": mrno,
        "nurse_session_id": nurse_session_id,
        "is_verified": False,
    }
    create_session(session_id, session_data)
    return session_data



async def transcribe_pcm_stream(raw_bytes: bytes, role: str = "general",
                                mrno: int = 0) -> dict:
    """
    Process raw PCM bytes from the BLE/Wi-Fi device.
    Strips markers → wraps in WAV → transcribes.
    """
    pcm = strip_pcm_markers(raw_bytes)
    wav_bytes = pcm_to_wav_bytes(pcm)

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            temp_path = tmp.name
            tmp.write(wav_bytes)

        transcription, language = await transcribe_audio_file(temp_path)
    finally:
        if temp_path:
            cleanup_file(temp_path)

    session_id = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "transcription": transcription, 
        "language": language,
        "role": role,
        "mrno": mrno,
        "is_verified": False,
    }
    create_session(session_id, session_data)
    return session_data
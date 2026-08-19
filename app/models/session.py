from pydantic import BaseModel
from typing import Optional, Dict, Any


class NurseSessionStart(BaseModel):
    mrno: int
    emr_id: Optional[str] = None      # optional — to pull demographics
    clinic: Optional[str] = None      # clinic name, saved to registration.patient


class DoctorSessionStart(BaseModel):
    mrno: int
    nurse_session_id: Optional[str] = None   # link to nurse session
    clinic: Optional[str] = None             # clinic name, saved to registration.patient


class SessionSummaryRequest(BaseModel):
    session_id: str
    target_language: str = "English"


class EditTranscriptRequest(BaseModel):
    new_text: str


class TranslateRequest(BaseModel):
    target_language: str


class MergeRequest(BaseModel):
    nurse_session_id: str
    doctor_session_id: str

# from pydantic import BaseModel
# from typing import Optional, Dict, Any


# class NurseSessionStart(BaseModel):
#     mrno: int
#     emr_id: Optional[str] = None      # optional — to pull demographics


# class DoctorSessionStart(BaseModel):
#     mrno: int
#     nurse_session_id: Optional[str] = None   # link to nurse session


# class SessionSummaryRequest(BaseModel):
#     session_id: str
#     target_language: str = "English"


# class EditTranscriptRequest(BaseModel):
#     new_text: str


# class TranslateRequest(BaseModel):
#     target_language: str


# class MergeRequest(BaseModel):
#     nurse_session_id: str
#     doctor_session_id: str

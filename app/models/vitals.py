from pydantic import BaseModel
from typing import Optional


class VitalsInput(BaseModel):
    blood_pressure: str = ""          # "120/80"
    heart_rate: Optional[int] = None
    temperature: Optional[float] = None   # Fahrenheit
    spo2: Optional[float] = None          # oxygen saturation %
    blood_glucose: Optional[float] = None
    pain_score: Optional[int] = None      # 0-10
    avpu_score: Optional[str] = None      # A / V / P / U
    respiratory_rate: Optional[int] = None
    notes: str = ""


class VitalsDB(BaseModel):
    mrno: int
    sr_no: Optional[int] = None
    body_temperature: Optional[int] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    bp_systolic: Optional[int] = None
    bp_diastolic: Optional[int] = None
    spo2: Optional[float] = None
    blood_glucose: Optional[float] = None
    pain_score: Optional[int] = None
    avpu_score: Optional[str] = None
    session_id: Optional[str] = None
    recorded_by: str = "nurse"
    audio_recording_id: Optional[int] = None
    nurse_audio_id: Optional[int] = None
    doctor_audio_id: Optional[int] = None


class VitalsExtracted(BaseModel):
    body_temperature: Optional[int] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    bp_systolic: Optional[int] = None
    bp_diastolic: Optional[int] = None
    spo2: Optional[float] = None
    blood_glucose: Optional[float] = None
    pain_score: Optional[int] = None
    avpu_score: Optional[str] = None
from pydantic import BaseModel
from typing import Optional, List


class OrderItem(BaseModel):
    medicine_code: str
    quantity: int
    strength: str = ""
    notes: str = ""


class OrderRequest(BaseModel):
    emr_id: str
    session_id: str
    orders: List[OrderItem]
    ordered_by: str = "Doctor"


class PrescriptionHeader(BaseModel):
    patient_name: str
    age: str
    gender: str
    contact: str
    diagnosis: str
    doctor_comments: str
    date: str

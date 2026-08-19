from pydantic import BaseModel
from typing import List, Optional


class PatientDemographics(BaseModel):
    emr_id: str
    mrno: Optional[int] = None           # hospital MR number (integer)
    name: str
    age: int
    gender: str
    date_of_birth: str
    contact_number: str
    address: str
    blood_group: str
    allergies: List[str] = []
    chronic_conditions: List[str] = []


class PatientUpdateRequest(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    contact_number: Optional[str] = None
    address: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[List[str]] = None
    chronic_conditions: Optional[List[str]] = None


class PatientSearchQuery(BaseModel):
    query: str   # name, emr_id, or contact number

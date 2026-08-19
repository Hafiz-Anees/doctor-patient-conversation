# """
# core/models.py — SQLAlchemy models for PostgreSQL tables.
# """

# from sqlalchemy import Column, Integer, String, DateTime, LargeBinary, BigInteger
# from sqlalchemy.ext.declarative import declarative_base
# from datetime import datetime

# Base = declarative_base()

# class AudioRecording(Base):
#     """Store audio recordings in PostgreSQL BYTEA"""
#     __tablename__ = 'audio_recordings'
    
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     session_id = Column(String(255), nullable=False, index=True)
#     session_type = Column(String(50), nullable=False)  # 'nurse' or 'doctor'
#     mrno = Column(Integer, nullable=False, index=True)
#     audio_data = Column(LargeBinary, nullable=False)  # BYTEA in PostgreSQL
#     file_name = Column(String(255))
#     file_size = Column(BigInteger)
#     content_type = Column(String(100), default='audio/wav')
#     created_at = Column(DateTime, default=datetime.utcnow)
    
#     def __repr__(self):
#         return f"<AudioRecording(id={self.id}, session={self.session_id}, size={self.file_size})>"


"""
core/models.py — SQLAlchemy models for audio recordings (PostgreSQL only).

Stores raw audio bytes (BYTEA) + transcription + summary.
Doctor table also stores merged_summary + prescription + icd_codes.
"""

from sqlalchemy import Column, Integer, Text, LargeBinary, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class NurseAudioRecording(Base):
    __tablename__ = "nurse_audio_recordings"
    __table_args__ = {"schema": "public"}

    id            = Column(Integer, primary_key=True)
    session_id    = Column(Text, index=True)
    mrno          = Column(Integer, index=True)
    audio_data    = Column(LargeBinary)        # BYTEA — raw audio
    file_name     = Column(Text)
    file_size     = Column(Integer)
    content_type  = Column(Text, default="audio/wav")
    language      = Column(Text)
    transcription = Column(Text)
    summary       = Column(JSONB)              # structured nurse summary
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class DoctorAudioRecording(Base):
    __tablename__ = "doctor_audio_recordings"
    __table_args__ = {"schema": "public"}

    id               = Column(Integer, primary_key=True)
    session_id       = Column(Text, index=True)
    mrno             = Column(Integer, index=True)
    nurse_session_id = Column(Text)
    audio_data       = Column(LargeBinary)     # BYTEA — raw audio
    file_name        = Column(Text)
    file_size        = Column(Integer)
    content_type     = Column(Text, default="audio/wav")
    language         = Column(Text)
    transcription    = Column(Text)
    summary          = Column(JSONB)           # doctor's own summary
    merged_summary   = Column(JSONB)           # nurse + doctor merged note
    prescription     = Column(JSONB)
    icd_codes        = Column(JSONB)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
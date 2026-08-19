# EMRChain Backend v2.0

Complete medical transcription, vitals extraction, summary generation,
prescription, and coding API — with full nurse → doctor → merge workflow
and BLE/Wi-Fi device integration.

---

## Project Structure

```
emrchain-backend/
│
├── main.py                        # FastAPI app entry point
│
├── core/
│   ├── config.py                  # All env variables, credentials
│   ├── database.py                # MongoDB + PostgreSQL connections & schema bootstrap
│   └── security.py               # JWT auth, role-based dependencies
│
├── models/                        # Pydantic request/response models
│   ├── patient.py
│   ├── vitals.py
│   ├── session.py
│   └── prescription.py
│
├── services/                      # Business logic
│   ├── transcription_service.py   # Gemini audio → text (file upload + PCM stream)
│   ├── summary_service.py         # Text → structured JSON note (nurse & doctor)
│   ├── vitals_service.py          # AI vitals extraction + PostgreSQL save/fetch
│   ├── prescription_service.py    # Medication enrichment + lab matching
│   ├── merge_service.py           # Merge nurse + doctor summaries (AI-powered)
│   └── coding_service.py         # ICD-10 / HCC / E&M code generation
│
├── routes/                        # API endpoint layers
│   ├── auth.py                    # Login → JWT token
│   ├── patient.py                 # Patient CRUD + search
│   ├── vitals.py                  # Manual vitals entry + history
│   ├── nurse.py                   ← NEW: complete nurse workflow
│   ├── doctor.py                  ← NEW: complete doctor workflow + finalize
│   ├── transcription.py           # Standalone transcription (legacy/shared)
│   ├── prescription.py            # Prescription generation
│   ├── analytics.py               # Usage analytics
│   └── lab_tests.py              # Lab test catalogue + search
│
├── tools/                         # Reference data (pure Python lookups, no AI)
│   ├── medicine_codes.py
│   ├── frequency_codes.py
│   ├── route_codes.py
│   ├── lab_tests.py
│   └── prescription_engine.py
│
└── utils/
    ├── audio_helpers.py            # PCM parsing, WAV wrapping, file cleanup
    └── session_store.py            # Thread-safe in-memory session store
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Fill in your GEMINI_API_KEY, MONGO_URI, POSTGRES_URI, SECRET_KEY
```

### 3. Run
```bash
uvicorn main:app --reload --port 8000
```

### 4. Open docs
```
http://localhost:8000/docs
```

---

## Complete Patient Flow

### Phase 1 — Nurse Flow

```
1. POST /nurse/start-session
   Body: { "mrno": 1234, "emr_id": "EMR-001" }
   → Returns: session_id

2. POST /nurse/record/{session_id}
   Body: audio file (multipart)
   → Transcribes audio
   → Auto-extracts vitals from speech (Gemini)
   → Saves vitals to PostgreSQL patient_vitals table
   → Returns: transcription + extracted vitals

   [Optional] PATCH /nurse/edit/{session_id}
   Body: { "new_text": "corrected transcript..." }

3. POST /nurse/summary/{session_id}?target_language=English
   → Generates structured nurse note JSON
   → Includes: Chief Complaints, Vitals, Nurse Observations, Patient History
   → Returns: summary

   GET /nurse/summary/{session_id}   ← retrieve it later
```

### Phase 2 — Doctor Flow

```
4. GET /doctor/patient-brief/{mrno}?nurse_session_id={id}
   → Returns: latest vitals + nurse summary
   → Doctor sees everything BEFORE starting consult

5. POST /doctor/start-session
   Body: { "mrno": 1234, "nurse_session_id": "..." }
   → Returns: session_id

6. POST /doctor/record/{session_id}
   Body: audio file (multipart)
   → Transcribes doctor-patient conversation

   [Optional] PATCH /doctor/edit/{session_id}

7. POST /doctor/summary/{session_id}?target_language=English
   → Generates full clinical note:
     Diagnosis, Treatment Plan, Order Entry, Prescription

8. POST /doctor/finalize/{session_id}?nurse_session_id={id}
   → Merges nurse summary + doctor summary (AI-powered)
   → Generates prescription table with codes
   → Generates ICD-10 / HCC / E&M codes
   → Saves complete medical record to MongoDB
   → Returns: merged_record + prescription + codes
```

### Phase 3 — Retrieve

```
GET /doctor/record/{record_id}         ← final merged record
GET /doctor/records/patient/{mrno}     ← all records for a patient
GET /patient/{mrno}/vitals             ← vitals history (PostgreSQL)
```

---

## Device Integration (BLE/Wi-Fi)

The device sends raw PCM audio as a chunked HTTP stream:

```
POST /nurse/device-stream
Headers:
  x-device-id: <stable device ID>
  x-mac-address: <MAC>
  x-mrno: <patient MR number>
Content-Type: application/octet-stream

Body:
  0xFF 0xFF 0xFF 0xFF   ← START_SIGNAL
  <raw PCM samples>     ← 16-bit signed, mono, 16kHz, little-endian
  0xEE 0xEE 0xEE 0xEE   ← END_SIGNAL
```

The backend:
1. Strips markers
2. Wraps PCM in WAV header
3. Sends to Gemini for transcription
4. Extracts vitals from transcript
5. Saves vitals to PostgreSQL
6. Returns session_id + transcription + vitals

---

## Database Architecture

| Data | Where | Why |
|------|-------|-----|
| Patient vitals | PostgreSQL `patient_vitals` | Structured, typed, queryable |
| Nurse/Doctor sessions | MongoDB `sessions` | Flexible schema, nested summaries |
| Transcriptions | In-memory + MongoDB | Fast access during session |
| Prescriptions | MongoDB `prescriptions` | Analytics-friendly |
| Final records | MongoDB `medical_records` | Merged nested documents |
| Reference data | Python files (`tools/`) | Fast lookup, no DB round-trip |

---

## Auth

All endpoints can be protected with JWT:

```bash
# Get token
POST /auth/login
{ "email": "nurse@emrchain.com", "password": "nurse1234" }

# Use token
Authorization: Bearer <token>
```

Demo accounts:
| Email | Password | Role |
|-------|----------|------|
| emrchain@gmail.com | emr1234 | admin |
| nurse@emrchain.com | nurse1234 | nurse |
| doctor@emrchain.com | doctor1234 | doctor |

---

## Health Check

```
GET /health
→ { "mongo": true, "postgres": true, "gemini": true }
```

# MediAid API Reference
**Base URL:** `https://api.mediaid.health/v1` (production) | `http://localhost:8000` (local)

All endpoints require `Authorization: Bearer <firebase_id_token>` unless marked as **Public**.

---

## Authentication

### POST /auth/register
Register a new user after Firebase sign-up.

**Body:**
```json
{
  "firebase_uid": "string",
  "email": "user@example.com",
  "full_name": "Arjun Rao",
  "phone": "+91 98765 43210"
}
```
**Response:** `201 Created` with user object.

---

## AI Assistant

### POST /ai/chat
Send a message to the AI symptom checker.

**Body:**
```json
{
  "content": "I have a fever of 101°F and headache for 2 days",
  "session_id": "optional-uuid-to-continue-session"
}
```

**Response:**
```json
{
  "message": "Based on your symptoms, you may have a viral infection...",
  "urgency": "medium",
  "detected_symptoms": ["fever", "headache"],
  "recommendations": [
    "Rest and stay hydrated",
    "Take paracetamol for fever management",
    "Consult a doctor if fever exceeds 103°F"
  ],
  "should_seek_care": false,
  "session_id": "uuid"
}
```

**Urgency levels:** `low` | `medium` | `high` | `emergency`

---

### POST /ai/risk-assessment
AI-powered health risk prediction.

**Body:**
```json
{
  "age": 45,
  "gender": "male",
  "bmi": 26.5,
  "systolic_bp": 128,
  "blood_glucose": 108.0,
  "smoker": false,
  "family_history_diabetes": true,
  "family_history_heart": false,
  "physical_activity": "moderate"
}
```

**Response:**
```json
{
  "diabetes_risk": 0.42,
  "hypertension_risk": 0.31,
  "heart_disease_risk": 0.18,
  "overall_risk": "moderate",
  "recommendations": [
    "Reduce refined carbohydrate intake",
    "..."
  ],
  "assessed_at": "2026-06-10T09:00:00Z"
}
```

---

## Vitals

### POST /vitals
Log a new vitals reading.

**Body (all fields optional, log what you have):**
```json
{
  "systolic_bp": 124,
  "diastolic_bp": 82,
  "heart_rate": 72,
  "blood_glucose": 108.0,
  "temperature": 36.8,
  "spo2": 98.0,
  "weight_kg": 78.0,
  "notes": "After morning walk"
}
```

**Response includes `alerts` array** with any flagged abnormal values.

---

### GET /vitals?limit=30
Get vitals history. Default 30, max 365 readings.

### GET /vitals/latest
Get most recent vitals entry.

### GET /vitals/summary
Get 7-day and 30-day running averages.

---

## Medications

### GET /medications
List all active medications.

### POST /medications
Add a new medication with reminder times.

**Body:**
```json
{
  "name": "Metformin",
  "dosage": "500mg",
  "frequency": "twice daily",
  "times_per_day": 2,
  "reminder_times": ["08:00", "20:00"],
  "start_date": "2026-01-01",
  "instructions": "Take after meals"
}
```

### POST /medications/{id}/log
Log a dose as taken/missed/skipped.

---

## Reports

### GET /reports/generate?period=monthly&month=2026-05
Generate and return a PDF health report.

Returns binary PDF with `Content-Type: application/pdf`.

---

## Clinics

### GET /clinics/nearby?lat=19.2183&lon=73.1659&radius=5000
Find healthcare facilities within radius (meters).

---

## Error Responses

All errors follow:
```json
{
  "detail": "Human-readable error message"
}
```

| Code | Meaning |
|------|---------|
| 400 | Bad Request — invalid input |
| 401 | Unauthorized — invalid/expired token |
| 403 | Forbidden — insufficient permissions |
| 404 | Not Found |
| 429 | Rate limited — too many requests |
| 500 | Internal Server Error |

---

## Rate Limits

- AI chat: **30 requests/minute** per user
- Risk assessment: **10 requests/hour** per user
- All other endpoints: **100 requests/minute** per user

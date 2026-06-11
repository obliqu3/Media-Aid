# MediAid — AI Health Assistant
> **SDG 3: Good Health and Well-Being**

![MediAid Banner](screenshots/banner.png)

MediAid is a production-ready AI-powered health assistant that helps underserved communities access primary healthcare guidance, track symptoms, predict health risks, and connect with emergency services — all through an intelligent conversational interface.

---

## SDG Alignment

**Goal 3: Good Health and Well-Being**
- Target 3.8: Achieve universal health coverage
- Target 3.d: Strengthen early warning and risk reduction for national and global health risks

---

## Problem Statement

**What:** Millions of people in low-income and rural regions lack access to basic healthcare guidance. They delay seeking help due to cost, distance, or lack of awareness — turning treatable conditions into emergencies.

**Where:** Primarily in rural India, sub-Saharan Africa, and underserved urban communities worldwide.

**Who is affected:** ~4.5 billion people lack access to basic health services (WHO, 2023).

**Why it matters:** Early detection and guidance can prevent 70% of preventable deaths.

**If unsolved:** Conditions like diabetes, hypertension, and infections progress silently — causing 3.5 million avoidable deaths annually in low-income nations.

---

## Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | AI Symptom Checker | NLP-powered symptom analysis with urgency triage |
| 2 | Medication Tracker | Smart reminders with adherence analytics |
| 3 | Health Dashboard | Vitals tracking with trend visualization |
| 4 | Risk Prediction | ML model predicting diabetes/hypertension risk |
| 5 | Nearby Clinics | Geo-location based clinic and pharmacy finder |
| 6 | Multi-language Support | English, Hindi, Swahili (Gemini translation) |
| 7 | Health Reports | AI-generated PDF health summaries |
| 8 | Emergency SOS | One-tap emergency contact with location sharing |
| 9 | Health Profile | Comprehensive personal health record |
| 10 | Analytics Admin | Aggregated anonymized population health trends |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React)                  │
│  Landing │ Dashboard │ Chat │ Tracker │ Reports      │
└──────────────────────┬──────────────────────────────┘
                       │ REST API / WebSocket
┌──────────────────────▼──────────────────────────────┐
│                  Backend (FastAPI)                   │
│  Auth │ Health API │ AI Service │ Notification API  │
└────────┬──────────────────┬───────────────────┬─────┘
         │                  │                   │
┌────────▼──────┐  ┌────────▼──────┐  ┌────────▼──────┐
│  PostgreSQL   │  │  Gemini API   │  │  Firebase     │
│  (User data)  │  │  (AI Chat)    │  │  (Auth+Push)  │
└───────────────┘  └───────────────┘  └───────────────┘
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + TailwindCSS |
| Backend | FastAPI (Python 3.11) |
| Database | PostgreSQL + SQLAlchemy |
| AI/NLP | Google Gemini API + LangChain |
| Auth | Firebase Authentication |
| Charts | Recharts |
| Deployment | Docker + Railway / Render |

---

## Repository Structure

```
mediaid/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.js
├── backend/
│   ├── routes/
│   ├── models/
│   ├── middleware/
│   ├── services/
│   ├── main.py
│   └── requirements.txt
├── database/
│   └── schema.sql
├── ai-model/
│   └── risk_predictor.py
├── docs/
│   └── api_reference.md
├── screenshots/
├── README.md
├── requirements.txt
├── .env.example
└── docker-compose.yml
```

---

## Installation & Setup

### Prerequisites
- Node.js 18+
- Python 3.11+
- PostgreSQL 15+
- Google Gemini API key

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/mediaid.git
cd mediaid
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env        # Fill in your keys
uvicorn main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env.local     # Fill in your API base URL
npm run dev
```

### 4. Database Setup
```bash
psql -U postgres -c "CREATE DATABASE mediaid;"
psql -U postgres -d mediaid -f database/schema.sql
```

---

## Environment Variables

```env
# Backend (.env)
DATABASE_URL=postgresql://user:password@localhost/mediaid
GEMINI_API_KEY=your_gemini_api_key
FIREBASE_PROJECT_ID=your_firebase_project
JWT_SECRET=your_super_secret_key
PORT=8000

# Frontend (.env.local)
VITE_API_BASE_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=your_firebase_web_key
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|---------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login & get JWT |
| GET | `/health/profile` | Get health profile |
| PUT | `/health/profile` | Update health profile |
| POST | `/health/vitals` | Log vitals reading |
| GET | `/health/vitals` | Get vitals history |
| POST | `/ai/chat` | AI symptom chat |
| POST | `/ai/risk-assessment` | Predict health risk |
| GET | `/medications` | List medications |
| POST | `/medications` | Add medication |
| GET | `/reports/generate` | Generate health report |
| GET | `/clinics/nearby` | Find nearby clinics |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

- UN Sustainable Development Goals (SDGs)
- WHO Global Health Observatory data
- Google Gemini API
- OpenStreetMap / Nominatim for clinic data

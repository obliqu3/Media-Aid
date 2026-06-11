# MediAid — System Architecture

## High-Level Architecture

```mermaid
graph TB
    subgraph Client["🖥️ Client Layer"]
        Web["React Web App<br/>(Vite + TailwindCSS)"]
        Mobile["React Native<br/>(Future)"]
    end

    subgraph API["⚙️ API Layer (FastAPI)"]
        Auth["Auth Router<br/>/auth"]
        HealthAPI["Health Router<br/>/health + /vitals"]
        MedAPI["Medications Router<br/>/medications"]
        AIAPI["AI Router<br/>/ai/chat + /ai/risk"]
        ReportAPI["Reports Router<br/>/reports"]
        AdminAPI["Admin Router<br/>/admin"]
    end

    subgraph AI["🧠 AI Services"]
        Gemini["Google Gemini 1.5 Flash<br/>Symptom Chat + Recommendations"]
        RiskML["Gradient Boosting Model<br/>Diabetes + Hypertension Risk"]
        LangChain["LangChain<br/>Context Management"]
    end

    subgraph Data["🗄️ Data Layer"]
        PG["PostgreSQL 15<br/>Primary Database"]
        Firebase["Firebase Auth<br/>Identity Provider"]
    end

    subgraph Notifications["🔔 Notifications"]
        FCM["Firebase Cloud Messaging<br/>Push Notifications"]
    end

    Web --> Auth
    Web --> HealthAPI
    Web --> MedAPI
    Web --> AIAPI
    Web --> ReportAPI

    Auth --> Firebase
    AIAPI --> Gemini
    AIAPI --> RiskML
    Gemini --> LangChain

    HealthAPI --> PG
    MedAPI --> PG
    ReportAPI --> PG
    AdminAPI --> PG

    MedAPI --> FCM
```

---

## User Journey — Symptom Check Flow

```mermaid
sequenceDiagram
    actor User
    participant App as React App
    participant API as FastAPI Backend
    participant Gemini as Gemini AI
    participant DB as PostgreSQL

    User->>App: Describes symptoms in chat
    App->>API: POST /ai/chat {content, session_id}
    API->>API: Validate Firebase JWT
    API->>Gemini: Send symptom text + system prompt
    Gemini-->>API: JSON {message, urgency, symptoms, recs}
    API->>DB: Persist chat message + session
    API-->>App: ChatResponse {message, urgency, recommendations}
    App-->>User: Display AI response with urgency badge

    alt urgency == "emergency"
        App-->>User: ⚠️ EMERGENCY banner + call button
    else urgency == "high"
        App-->>User: Recommend urgent clinic visit
    end
```

---

## Medication Reminder Flow

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant FCM as Firebase Cloud Messaging
    participant Device as User's Phone

    Note over API: Cron job runs every 5 minutes
    API->>DB: Query medications due in next 15 min
    DB-->>API: List of pending medication_logs
    loop For each pending dose
        API->>FCM: Send push notification
        FCM->>Device: 💊 "Time to take Metformin 500mg"
        Device-->>User: Push notification
        User->>API: POST /medications/{id}/log {status: "taken"}
        API->>DB: Update medication_log.status
    end
```

---

## Data Model (ERD)

```mermaid
erDiagram
    USERS {
        uuid id PK
        string firebase_uid UK
        string email UK
        string full_name
        string role
        timestamp created_at
    }

    HEALTH_PROFILES {
        uuid id PK
        uuid user_id FK
        decimal height_cm
        decimal weight_kg
        string blood_type
        array allergies
        array chronic_conditions
    }

    VITALS {
        uuid id PK
        uuid user_id FK
        timestamp recorded_at
        int systolic_bp
        int diastolic_bp
        int heart_rate
        decimal blood_glucose
        decimal spo2
    }

    MEDICATIONS {
        uuid id PK
        uuid user_id FK
        string name
        string dosage
        int times_per_day
        array reminder_times
        boolean is_active
    }

    MEDICATION_LOGS {
        uuid id PK
        uuid medication_id FK
        uuid user_id FK
        timestamp scheduled_time
        timestamp taken_at
        string status
    }

    CHAT_SESSIONS {
        uuid id PK
        uuid user_id FK
        string urgency_level
        timestamp created_at
    }

    CHAT_MESSAGES {
        uuid id PK
        uuid session_id FK
        string role
        text content
        jsonb metadata
    }

    RISK_ASSESSMENTS {
        uuid id PK
        uuid user_id FK
        decimal diabetes_risk
        decimal hypertension_risk
        decimal heart_disease_risk
        string overall_risk
    }

    USERS ||--o| HEALTH_PROFILES : "has"
    USERS ||--o{ VITALS : "logs"
    USERS ||--o{ MEDICATIONS : "takes"
    MEDICATIONS ||--o{ MEDICATION_LOGS : "tracks"
    USERS ||--o{ CHAT_SESSIONS : "starts"
    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : "contains"
    USERS ||--o{ RISK_ASSESSMENTS : "receives"
```

---

## Deployment Architecture

```mermaid
graph LR
    subgraph CDN["🌐 CDN / Edge"]
        Vercel["Vercel<br/>(React Frontend)"]
    end

    subgraph Cloud["☁️ Cloud (Railway / Render)"]
        FastAPI["FastAPI Container<br/>(Dockerized)"]
        PG["PostgreSQL<br/>(Managed)"]
    end

    subgraph External["🔗 External APIs"]
        GeminiAPI["Google Gemini API"]
        FirebaseAuth["Firebase Auth"]
        FCMService["Firebase Cloud Messaging"]
    end

    Browser["User Browser"] --> Vercel
    Vercel --> FastAPI
    FastAPI --> PG
    FastAPI --> GeminiAPI
    FastAPI --> FirebaseAuth
    FastAPI --> FCMService
```

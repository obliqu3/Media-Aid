-- MediAid Database Schema
-- SDG 3: Good Health and Well-Being
-- PostgreSQL 15+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- USERS & AUTHENTICATION
-- ============================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    firebase_uid    VARCHAR(128) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    phone           VARCHAR(20),
    date_of_birth   DATE,
    gender          VARCHAR(10) CHECK (gender IN ('male', 'female', 'other')),
    language        VARCHAR(10) DEFAULT 'en',
    role            VARCHAR(20) DEFAULT 'patient' CHECK (role IN ('patient', 'admin', 'doctor')),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- HEALTH PROFILES
-- ============================================

CREATE TABLE health_profiles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    height_cm       DECIMAL(5,1),
    weight_kg       DECIMAL(5,1),
    blood_type      VARCHAR(5),
    allergies       TEXT[],
    chronic_conditions TEXT[],
    family_history  JSONB DEFAULT '{}',
    emergency_contact_name  VARCHAR(255),
    emergency_contact_phone VARCHAR(20),
    insurance_provider      VARCHAR(255),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- ============================================
-- VITALS TRACKING
-- ============================================

CREATE TABLE vitals (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    recorded_at     TIMESTAMPTZ DEFAULT NOW(),
    systolic_bp     INTEGER,           -- mmHg
    diastolic_bp    INTEGER,           -- mmHg
    heart_rate      INTEGER,           -- bpm
    blood_glucose   DECIMAL(5,1),     -- mg/dL
    temperature     DECIMAL(4,1),     -- Celsius
    spo2            DECIMAL(4,1),     -- %
    weight_kg       DECIMAL(5,1),
    notes           TEXT,
    source          VARCHAR(50) DEFAULT 'manual' CHECK (source IN ('manual', 'wearable', 'device'))
);

CREATE INDEX idx_vitals_user_date ON vitals(user_id, recorded_at DESC);

-- ============================================
-- MEDICATIONS
-- ============================================

CREATE TABLE medications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    dosage          VARCHAR(100),
    frequency       VARCHAR(100),          -- e.g., "twice daily", "every 8 hours"
    times_per_day   INTEGER DEFAULT 1,
    reminder_times  TIME[],               -- Array of reminder times
    start_date      DATE NOT NULL,
    end_date        DATE,
    is_active       BOOLEAN DEFAULT TRUE,
    instructions    TEXT,
    prescribing_doctor VARCHAR(255),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE medication_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    medication_id   UUID REFERENCES medications(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    scheduled_time  TIMESTAMPTZ NOT NULL,
    taken_at        TIMESTAMPTZ,
    status          VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('taken', 'missed', 'skipped', 'pending')),
    notes           TEXT
);

CREATE INDEX idx_med_logs_user_time ON medication_logs(user_id, scheduled_time DESC);

-- ============================================
-- AI CHAT SESSIONS
-- ============================================

CREATE TABLE chat_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(255),
    summary         TEXT,              -- AI-generated session summary
    urgency_level   VARCHAR(20) CHECK (urgency_level IN ('low', 'medium', 'high', 'emergency')),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    ended_at        TIMESTAMPTZ
);

CREATE TABLE chat_messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT NOT NULL,
    metadata        JSONB DEFAULT '{}',   -- symptoms detected, urgency, etc.
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_msgs_session ON chat_messages(session_id, created_at);

-- ============================================
-- RISK ASSESSMENTS
-- ============================================

CREATE TABLE risk_assessments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    assessed_at     TIMESTAMPTZ DEFAULT NOW(),
    diabetes_risk   DECIMAL(5,4),      -- 0.0 to 1.0
    hypertension_risk DECIMAL(5,4),
    heart_disease_risk DECIMAL(5,4),
    overall_risk    VARCHAR(20) CHECK (overall_risk IN ('low', 'moderate', 'high', 'critical')),
    recommendations JSONB DEFAULT '[]',
    model_version   VARCHAR(20) DEFAULT '1.0'
);

CREATE INDEX idx_risk_user_date ON risk_assessments(user_id, assessed_at DESC);

-- ============================================
-- HEALTH REPORTS
-- ============================================

CREATE TABLE health_reports (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    generated_at    TIMESTAMPTZ DEFAULT NOW(),
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    report_type     VARCHAR(50) DEFAULT 'monthly',
    file_path       VARCHAR(500),
    summary         TEXT,
    ai_insights     JSONB DEFAULT '{}'
);

-- ============================================
-- CLINICS & FACILITIES (Cached)
-- ============================================

CREATE TABLE clinics (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    address         TEXT,
    latitude        DECIMAL(9,6),
    longitude       DECIMAL(9,6),
    phone           VARCHAR(20),
    services        TEXT[],
    is_emergency    BOOLEAN DEFAULT FALSE,
    operating_hours JSONB DEFAULT '{}',
    last_updated    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_clinics_location ON clinics(latitude, longitude);

-- ============================================
-- NOTIFICATIONS
-- ============================================

CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    type            VARCHAR(50),       -- medication_reminder, risk_alert, report_ready
    title           VARCHAR(255),
    body            TEXT,
    is_read         BOOLEAN DEFAULT FALSE,
    sent_at         TIMESTAMPTZ DEFAULT NOW(),
    read_at         TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}'
);

-- ============================================
-- ADMIN: AGGREGATE ANALYTICS (Anonymized)
-- ============================================

CREATE TABLE aggregate_stats (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stat_date       DATE NOT NULL,
    region          VARCHAR(100),
    total_users     INTEGER DEFAULT 0,
    active_users    INTEGER DEFAULT 0,
    symptom_checkins INTEGER DEFAULT 0,
    high_risk_users INTEGER DEFAULT 0,
    top_symptoms    JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(stat_date, region)
);

-- ============================================
-- UPDATED_AT TRIGGER
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER health_profiles_updated_at
    BEFORE UPDATE ON health_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- SEED DATA: Sample admin user
-- ============================================
INSERT INTO users (firebase_uid, email, full_name, role)
VALUES ('admin_seed_uid', 'admin@mediaid.health', 'MediAid Admin', 'admin')
ON CONFLICT DO NOTHING;

# Diagrama Entidad-Relación - CASTOR ELECCIONES

## Vista General de Bases de Datos

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              POSTGRESQL SERVER                                       │
│                                                                                      │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                │
│   │    core_db      │    │     e14_db      │    │  dashboard_db   │                │
│   │                 │    │                 │    │                 │                │
│   │ - users         │    │ - 25+ tablas    │    │ - analyses      │                │
│   │ - sessions      │    │ - electoral     │    │ - tweets        │                │
│   │ - leads         │    │ - geography     │    │ - chat_history  │                │
│   │                 │    │ - forms/ocr     │    │ - forecasts     │                │
│   └─────────────────┘    └─────────────────┘    └─────────────────┘                │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Core Database (core_db)

### Diagrama ER

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   CORE_DB                                            │
└─────────────────────────────────────────────────────────────────────────────────────┘

                            ┌───────────────────────┐
                            │        users          │
                            ├───────────────────────┤
                            │ PK id: UUID           │
                            │    email: VARCHAR(255)│◄─────── UNIQUE
                            │    password_hash: TEXT│
                            │    full_name: VARCHAR │
                            │    role: user_role    │
                            │    organization: VARCHAR
                            │    is_active: BOOLEAN │
                            │    created_at: TIMESTAMP
                            │    updated_at: TIMESTAMP
                            │    last_login: TIMESTAMP
                            └───────────┬───────────┘
                                        │
                                        │ 1
                                        │
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    │ *                 │ *                 │ *
                    ▼                   ▼                   ▼
        ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
        │     sessions      │ │      leads        │ │   user_settings   │
        ├───────────────────┤ ├───────────────────┤ ├───────────────────┤
        │ PK id: UUID       │ │ PK id: UUID       │ │ PK id: UUID       │
        │ FK user_id: UUID  │ │ FK user_id: UUID  │ │ FK user_id: UUID  │
        │    token: TEXT    │ │    name: VARCHAR  │ │    theme: VARCHAR │
        │    device: VARCHAR│ │    email: VARCHAR │ │    language: VARCHAR
        │    ip_address: INET│    phone: VARCHAR │ │    notifications: BOOLEAN
        │    expires_at: TS │ │    company: VARCHAR│    timezone: VARCHAR
        │    created_at: TS │ │    source: VARCHAR│ │    created_at: TS │
        │    is_valid: BOOL │ │    status: lead_status    updated_at: TS │
        └───────────────────┘ │    notes: TEXT    │ └───────────────────┘
                              │    created_at: TS │
                              │    updated_at: TS │
                              └───────────────────┘


═══════════════════════════════════════════════════════════════════════════════════════
                                    ENUMS
═══════════════════════════════════════════════════════════════════════════════════════

┌─────────────────────┐     ┌─────────────────────┐
│     user_role       │     │    lead_status      │
├─────────────────────┤     ├─────────────────────┤
│ 'admin'             │     │ 'new'               │
│ 'analyst'           │     │ 'contacted'         │
│ 'observer'          │     │ 'qualified'         │
│ 'viewer'            │     │ 'converted'         │
└─────────────────────┘     │ 'lost'              │
                            └─────────────────────┘
```

### DDL Core Database

```sql
-- Enum Types
CREATE TYPE user_role AS ENUM ('admin', 'analyst', 'observer', 'viewer');
CREATE TYPE lead_status AS ENUM ('new', 'contacted', 'qualified', 'converted', 'lost');

-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'viewer',
    organization VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

-- Sessions Table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    device VARCHAR(255),
    ip_address INET,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_valid BOOLEAN DEFAULT TRUE
);

-- Leads Table
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    company VARCHAR(255),
    source VARCHAR(100),
    status lead_status DEFAULT 'new',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_leads_user_id ON leads(user_id);
CREATE INDEX idx_leads_status ON leads(status);
```

---

## 2. E-14 Database (e14_db) - Electoral

### 2.1 Catálogos Electorales

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            CATÁLOGOS ELECTORALES                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────┐         ┌───────────────────────┐
│      election         │         │       party           │
├───────────────────────┤         ├───────────────────────┤
│ PK id: UUID           │         │ PK id: UUID           │
│    name: VARCHAR(255) │         │    name: VARCHAR(255) │
│    election_date: DATE│         │    abbreviation: VARCHAR(20)
│    election_type: type│         │    logo_url: TEXT     │
│    status: election_  │         │    color: VARCHAR(7)  │
│           status      │         │    created_at: TS     │
│    country: VARCHAR   │         └───────────┬───────────┘
│    created_at: TS     │                     │
└───────────┬───────────┘                     │
            │                                 │
            │ 1                               │ 1
            │                                 │
            │ *                               │ *
            ▼                                 │
┌───────────────────────┐                     │
│       contest         │                     │
├───────────────────────┤                     │
│ PK id: UUID           │                     │
│ FK election_id: UUID  │                     │
│    name: VARCHAR(255) │                     │
│    contest_type: type │                     │
│    jurisdiction: VARCHAR                    │
│    total_seats: INT   │                     │
│    created_at: TS     │                     │
└───────────┬───────────┘                     │
            │                                 │
            │ 1                               │
            │                                 │
            │ *                               │
            ▼                                 │
┌───────────────────────┐                     │
│      candidate        │◄────────────────────┘
├───────────────────────┤
│ PK id: UUID           │
│ FK contest_id: UUID   │
│ FK party_id: UUID     │
│    full_name: VARCHAR │
│    document_id: VARCHAR
│    ballot_number: INT │
│    photo_url: TEXT    │
│    is_active: BOOLEAN │
│    created_at: TS     │
└───────────────────────┘


═══════════════════════════════════════════════════════════════════════════════════════
                                    ENUMS
═══════════════════════════════════════════════════════════════════════════════════════

┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   election_type     │     │  election_status    │     │   contest_type      │
├─────────────────────┤     ├─────────────────────┤     ├─────────────────────┤
│ 'PRESIDENTIAL'      │     │ 'SCHEDULED'         │     │ 'PRESIDENT'         │
│ 'LEGISLATIVE'       │     │ 'IN_PROGRESS'       │     │ 'SENATE'            │
│ 'REGIONAL'          │     │ 'COMPLETED'         │     │ 'HOUSE'             │
│ 'LOCAL'             │     │ 'CANCELLED'         │     │ 'GOVERNOR'          │
│ 'REFERENDUM'        │     └─────────────────────┘     │ 'MAYOR'             │
└─────────────────────┘                                 │ 'COUNCIL'           │
                                                        └─────────────────────┘
```

### 2.2 Geografía (DIVIPOLA Colombia)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              GEOGRAFÍA ELECTORAL                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────┐
│     department        │
├───────────────────────┤
│ PK id: UUID           │
│    code: VARCHAR(2)   │◄─────── DIVIPOLA Code
│    name: VARCHAR(100) │
│    created_at: TS     │
└───────────┬───────────┘
            │
            │ 1
            │
            │ *
            ▼
┌───────────────────────┐
│    municipality       │
├───────────────────────┤
│ PK id: UUID           │
│ FK department_id: UUID│
│    code: VARCHAR(5)   │◄─────── DIVIPOLA Code
│    name: VARCHAR(100) │
│    risk_level: risk   │
│    population: INT    │
│    created_at: TS     │
└───────────┬───────────┘
            │
            │ 1
            │
            │ *
            ▼
┌───────────────────────┐
│   polling_station     │
├───────────────────────┤
│ PK id: UUID           │
│ FK municipality_id: UUID
│    code: VARCHAR(10)  │
│    name: VARCHAR(255) │
│    address: TEXT      │
│    latitude: DECIMAL  │
│    longitude: DECIMAL │
│    total_tables: INT  │
│    created_at: TS     │
└───────────┬───────────┘
            │
            │ 1
            │
            │ *
            ▼
┌───────────────────────┐
│   polling_table       │
├───────────────────────┤
│ PK id: UUID           │
│ FK station_id: UUID   │
│ FK contest_id: UUID   │
│    table_number: INT  │
│    registered_voters: INT
│    created_at: TS     │
└───────────────────────┘


═══════════════════════════════════════════════════════════════════════════════════════
                                    ENUMS
═══════════════════════════════════════════════════════════════════════════════════════

┌─────────────────────┐
│    risk_level       │
├─────────────────────┤
│ 'LOW'               │
│ 'MEDIUM'            │
│ 'HIGH'              │
│ 'EXTREME'           │
└─────────────────────┘
```

### 2.3 Formularios y OCR

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            FORMULARIOS Y OCR                                         │
└─────────────────────────────────────────────────────────────────────────────────────┘

                            ┌───────────────────────┐
                            │    form_instance      │
                            ├───────────────────────┤
                            │ PK id: UUID           │
                            │ FK polling_table_id   │
                            │ FK uploaded_by: UUID  │──────► users (core_db)
                            │    form_type: form_type
                            │    source_type: source│
                            │    file_url: TEXT     │
                            │    file_hash: VARCHAR │
                            │    processing_status  │
                            │    ocr_confidence: DECIMAL
                            │    processed_at: TS   │
                            │    created_at: TS     │
                            │    updated_at: TS     │
                            └───────────┬───────────┘
                                        │
                        ┌───────────────┼───────────────┐
                        │               │               │
                        │ 1             │ 1             │ 1
                        │               │               │
                        │ *             │ *             │ *
                        ▼               ▼               ▼
            ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
            │     ocr_field     │ │    vote_tally     │ │validation_result  │
            ├───────────────────┤ ├───────────────────┤ ├───────────────────┤
            │ PK id: UUID       │ │ PK id: UUID       │ │ PK id: UUID       │
            │ FK form_id: UUID  │ │ FK form_id: UUID  │ │ FK form_id: UUID  │
            │    field_name: VARCHAR FK candidate_id  │ │ FK rule_id: UUID  │
            │    raw_value: TEXT│ │    votes: INT     │ │    passed: BOOLEAN│
            │    parsed_value   │ │    null_votes: INT│ │    message: TEXT  │
            │    confidence: DECIMAL blank_votes: INT │ │    severity: alert│
            │    bounding_box: JSONB total_votes: INT │ │    created_at: TS │
            │    page_number: INT    source: source  │ └───────────────────┘
            │    created_at: TS │ │    created_at: TS │
            └───────────────────┘ └───────────────────┘


═══════════════════════════════════════════════════════════════════════════════════════
                                    ENUMS
═══════════════════════════════════════════════════════════════════════════════════════

┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│     form_type       │  │    source_type      │  │ processing_status   │
├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤
│ 'E14'               │  │ 'WITNESS'           │  │ 'PENDING'           │
│ 'E24'               │  │ 'OFFICIAL'          │  │ 'PROCESSING'        │
│ 'E26'               │  │ 'BOLETIN'           │  │ 'COMPLETED'         │
│ 'BOLETIN'           │  │ 'SCRAPER'           │  │ 'FAILED'            │
│ 'OTHER'             │  └─────────────────────┘  │ 'NEEDS_REVIEW'      │
└─────────────────────┘                           │ 'VALIDATED'         │
                                                  └─────────────────────┘
```

### 2.4 Validación, Alertas y Auditoría

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        VALIDACIÓN, ALERTAS Y AUDITORÍA                               │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────┐
│   validation_rule     │
├───────────────────────┤                    ┌───────────────────────┐
│ PK id: UUID           │                    │      discrepancy      │
│    name: VARCHAR      │                    ├───────────────────────┤
│    description: TEXT  │                    │ PK id: UUID           │
│    rule_type: VARCHAR │                    │ FK form_id: UUID      │
│    expression: TEXT   │                    │ FK field_name: VARCHAR│
│    severity: alert    │                    │    expected_value     │
│    is_active: BOOLEAN │                    │    actual_value       │
│    created_at: TS     │                    │    difference: DECIMAL│
└───────────────────────┘                    │    severity: alert    │
                                             │    resolved: BOOLEAN  │
                                             │    resolved_by: UUID  │
        ┌───────────────────────┐            │    resolved_at: TS    │
        │        alert          │            │    created_at: TS     │
        ├───────────────────────┤            └───────────────────────┘
        │ PK id: UUID           │
        │ FK form_id: UUID      │
        │ FK discrepancy_id     │
        │    alert_type: VARCHAR│            ┌───────────────────────┐
        │    severity: alert    │            │    reconciliation     │
        │    status: alert_status            ├───────────────────────┤
        │    title: VARCHAR     │            │ PK id: UUID           │
        │    message: TEXT      │            │ FK polling_table_id   │
        │    acknowledged_by    │            │ FK contest_id: UUID   │
        │    acknowledged_at: TS│            │ FK winning_form_id    │
        │    resolved_by: UUID  │            │    status: recon_status
        │    resolved_at: TS    │            │    final_votes: JSONB │
        │    created_at: TS     │            │    notes: TEXT        │
        └───────────────────────┘            │    reconciled_by: UUID│
                                             │    reconciled_at: TS  │
                                             │    created_at: TS     │
        ┌───────────────────────┐            └───────────────────────┘
        │      audit_log        │
        ├───────────────────────┤
        │ PK id: UUID           │◄─────── IMMUTABLE (no UPDATE/DELETE)
        │ FK user_id: UUID      │
        │ FK form_id: UUID      │
        │    action: audit_action
        │    entity_type: VARCHAR
        │    entity_id: UUID    │
        │    old_values: JSONB  │
        │    new_values: JSONB  │
        │    ip_address: INET   │
        │    user_agent: TEXT   │
        │    created_at: TS     │◄─────── Indexed for queries
        └───────────────────────┘


═══════════════════════════════════════════════════════════════════════════════════════
                                    ENUMS
═══════════════════════════════════════════════════════════════════════════════════════

┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   alert_severity    │  │   alert_status      │  │ reconciliation_status│
├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤
│ 'INFO'              │  │ 'OPEN'              │  │ 'PROVISIONAL'       │
│ 'LOW'               │  │ 'ACKNOWLEDGED'      │  │ 'FINAL'             │
│ 'MEDIUM'            │  │ 'INVESTIGATING'     │  │ 'DISPUTED'          │
│ 'HIGH'              │  │ 'RESOLVED'          │  └─────────────────────┘
│ 'CRITICAL'          │  │ 'FALSE_POSITIVE'    │
└─────────────────────┘  └─────────────────────┘  ┌─────────────────────┐
                                                  │   audit_action      │
                                                  ├─────────────────────┤
                                                  │ 'CREATE'            │
                                                  │ 'UPDATE'            │
                                                  │ 'DELETE'            │
                                                  │ 'REVIEW_APPROVED'   │
                                                  │ 'REVIEW_REJECTED'   │
                                                  │ 'RECONCILE'         │
                                                  │ 'ALERT_CREATED'     │
                                                  │ 'ALERT_RESOLVED'    │
                                                  └─────────────────────┘
```

### 2.5 Diagrama ER Completo E-14

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              E14_DB - DIAGRAMA COMPLETO                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ election │────<│ contest  │────<│candidate │>────│  party   │
└──────────┘     └────┬─────┘     └──────────┘     └──────────┘
                      │
                      │
┌──────────┐     ┌────┴─────┐     ┌──────────┐     ┌──────────┐
│department│────<│municipal.│────<│ station  │────<│  table   │
└──────────┘     └──────────┘     └──────────┘     └────┬─────┘
                                                        │
                                                        │
                                        ┌───────────────┴───────────────┐
                                        │                               │
                                        ▼                               ▼
                                  ┌──────────┐                   ┌──────────┐
                                  │   form   │                   │reconcile │
                                  │ instance │                   │          │
                                  └────┬─────┘                   └──────────┘
                                       │
                     ┌─────────────────┼─────────────────┐
                     │                 │                 │
                     ▼                 ▼                 ▼
               ┌──────────┐     ┌──────────┐     ┌──────────┐
               │ocr_field │     │vote_tally│     │validation│
               └──────────┘     └──────────┘     │  result  │
                                                 └────┬─────┘
                                                      │
                                                      ▼
               ┌──────────┐     ┌──────────┐     ┌──────────┐
               │  alert   │◄────│discrepancy│    │val_rule  │
               └────┬─────┘     └──────────┘     └──────────┘
                    │
                    ▼
               ┌──────────┐
               │audit_log │ (IMMUTABLE)
               └──────────┘


═══════════════════════════════════════════════════════════════════════════════════════
                                 CARDINALIDADES
═══════════════════════════════════════════════════════════════════════════════════════

election      1 ──────< * contest           (Una elección tiene muchas contiendas)
contest       1 ──────< * candidate         (Una contienda tiene muchos candidatos)
party         1 ──────< * candidate         (Un partido tiene muchos candidatos)
department    1 ──────< * municipality      (Un departamento tiene muchos municipios)
municipality  1 ──────< * polling_station   (Un municipio tiene muchos puestos)
station       1 ──────< * polling_table     (Un puesto tiene muchas mesas)
table         1 ──────< * form_instance     (Una mesa tiene muchos formularios)
form          1 ──────< * ocr_field         (Un formulario tiene muchos campos OCR)
form          1 ──────< * vote_tally        (Un formulario tiene muchos conteos)
form          1 ──────< * validation_result (Un formulario tiene muchas validaciones)
form          1 ──────< * discrepancy       (Un formulario puede tener discrepancias)
discrepancy   1 ──────< * alert             (Una discrepancia genera alertas)
form          1 ──────< * audit_log         (Un formulario tiene historial de auditoría)
```

---

## 3. Dashboard Database (dashboard_db)

### Diagrama ER

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                 DASHBOARD_DB                                         │
└─────────────────────────────────────────────────────────────────────────────────────┘

                            ┌───────────────────────┐
                            │      analysis         │
                            ├───────────────────────┤
                            │ PK id: UUID           │
                            │ FK user_id: UUID      │──────► users (core_db)
                            │    candidate: VARCHAR │
                            │    location: VARCHAR  │
                            │    topic_pnd: VARCHAR │
                            │    summary: TEXT      │
                            │    strategy: TEXT     │
                            │    speech: TEXT       │
                            │    charts_data: JSONB │
                            │    metrics: JSONB     │
                            │    tweet_count: INT   │
                            │    sentiment_dist: JSONB
                            │    created_at: TS     │
                            └───────────┬───────────┘
                                        │
                                        │ 1
                                        │
                                        │ *
                                        ▼
                            ┌───────────────────────┐
                            │       tweets          │
                            ├───────────────────────┤
                            │ PK id: UUID           │
                            │ FK analysis_id: UUID  │
                            │    tweet_id: VARCHAR  │◄─────── Twitter ID
                            │    text: TEXT         │
                            │    author: VARCHAR    │
                            │    author_followers: INT
                            │    retweets: INT      │
                            │    likes: INT         │
                            │    sentiment: sentiment
                            │    sentiment_score: DECIMAL
                            │    topic_pnd: VARCHAR │
                            │    created_at: TS     │
                            │    tweet_date: TS     │
                            └───────────────────────┘


┌───────────────────────┐                    ┌───────────────────────┐
│    chat_session       │                    │      forecast         │
├───────────────────────┤                    ├───────────────────────┤
│ PK id: UUID           │                    │ PK id: UUID           │
│ FK user_id: UUID      │                    │ FK user_id: UUID      │
│    title: VARCHAR     │                    │    candidate: VARCHAR │
│    created_at: TS     │                    │    forecast_date: DATE│
│    updated_at: TS     │                    │    icce: DECIMAL      │
└───────────┬───────────┘                    │    isn: DECIMAL       │
            │                                │    icr: DECIMAL       │
            │ 1                              │    momentum: DECIMAL  │
            │                                │    sve: DECIMAL       │
            │ *                              │    ivn: DECIMAL       │
            ▼                                │    predictions: JSONB │
┌───────────────────────┐                    │    confidence: DECIMAL│
│    chat_message       │                    │    created_at: TS     │
├───────────────────────┤                    └───────────────────────┘
│ PK id: UUID           │
│ FK session_id: UUID   │
│    role: message_role │                    ┌───────────────────────┐
│    content: TEXT      │                    │   trending_topic      │
│    tokens_used: INT   │                    ├───────────────────────┤
│    model: VARCHAR     │                    │ PK id: UUID           │
│    created_at: TS     │                    │    name: VARCHAR      │
└───────────────────────┘                    │    tweet_volume: INT  │
                                             │    location: VARCHAR  │
                                             │    rank: INT          │
                                             │    fetched_at: TS     │
┌───────────────────────┐                    │    expires_at: TS     │
│   rag_document        │                    └───────────────────────┘
├───────────────────────┤
│ PK id: UUID           │
│    content: TEXT      │
│    source: VARCHAR    │                    ┌───────────────────────┐
│    source_id: VARCHAR │                    │    campaign_agent     │
│    metadata: JSONB    │                    ├───────────────────────┤
│    embedding_id: VARCHAR◄─── ChromaDB ref  │ PK id: UUID           │
│    created_at: TS     │                    │ FK user_id: UUID      │
└───────────────────────┘                    │    candidate: VARCHAR │
                                             │    analysis_type: VARCHAR
                                             │    recommendations: JSONB
                                             │    winning_strategies: JSONB
                                             │    created_at: TS     │
                                             └───────────────────────┘

═══════════════════════════════════════════════════════════════════════════════════════
                                    ENUMS
═══════════════════════════════════════════════════════════════════════════════════════

┌─────────────────────┐     ┌─────────────────────┐
│    sentiment        │     │   message_role      │
├─────────────────────┤     ├─────────────────────┤
│ 'positive'          │     │ 'user'              │
│ 'negative'          │     │ 'assistant'         │
│ 'neutral'           │     │ 'system'            │
└─────────────────────┘     └─────────────────────┘
```

### DDL Dashboard Database

```sql
-- Enum Types
CREATE TYPE sentiment AS ENUM ('positive', 'negative', 'neutral');
CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system');

-- Analysis Table
CREATE TABLE analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,  -- References core_db.users
    candidate VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    topic_pnd VARCHAR(100),
    summary TEXT,
    strategy TEXT,
    speech TEXT,
    charts_data JSONB,
    metrics JSONB,
    tweet_count INTEGER DEFAULT 0,
    sentiment_distribution JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tweets Table
CREATE TABLE tweets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES analysis(id) ON DELETE CASCADE,
    tweet_id VARCHAR(50) NOT NULL,
    text TEXT NOT NULL,
    author VARCHAR(255),
    author_followers INTEGER,
    retweets INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    sentiment sentiment,
    sentiment_score DECIMAL(5,4),
    topic_pnd VARCHAR(100),
    tweet_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat Session Table
CREATE TABLE chat_session (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat Messages Table
CREATE TABLE chat_message (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_session(id) ON DELETE CASCADE,
    role message_role NOT NULL,
    content TEXT NOT NULL,
    tokens_used INTEGER,
    model VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Forecast Table
CREATE TABLE forecast (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    candidate VARCHAR(255) NOT NULL,
    forecast_date DATE NOT NULL,
    icce DECIMAL(5,2),           -- Índice Compuesto Capacidad Electoral
    isn DECIMAL(5,2),            -- Índice Sentimiento Neto
    icr DECIMAL(5,2),            -- Índice Conversación Relativa
    momentum DECIMAL(5,2),
    sve DECIMAL(5,2),            -- Sentimiento Votante Esperado
    ivn DECIMAL(5,2),            -- Índice Votante Neto
    predictions JSONB,           -- Array of {date, value, confidence}
    confidence DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trending Topics Table
CREATE TABLE trending_topic (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    tweet_volume INTEGER,
    location VARCHAR(100),
    rank INTEGER,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

-- RAG Documents Table
CREATE TABLE rag_document (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    source VARCHAR(100),
    source_id VARCHAR(255),
    metadata JSONB,
    embedding_id VARCHAR(255),  -- Reference to ChromaDB
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Campaign Agent Table
CREATE TABLE campaign_agent (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    candidate VARCHAR(255) NOT NULL,
    analysis_type VARCHAR(100),
    recommendations JSONB,
    winning_strategies JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_analysis_user_id ON analysis(user_id);
CREATE INDEX idx_analysis_candidate ON analysis(candidate);
CREATE INDEX idx_analysis_created_at ON analysis(created_at DESC);
CREATE INDEX idx_tweets_analysis_id ON tweets(analysis_id);
CREATE INDEX idx_tweets_sentiment ON tweets(sentiment);
CREATE INDEX idx_chat_session_user_id ON chat_session(user_id);
CREATE INDEX idx_chat_message_session_id ON chat_message(session_id);
CREATE INDEX idx_forecast_candidate ON forecast(candidate);
CREATE INDEX idx_forecast_date ON forecast(forecast_date DESC);
CREATE INDEX idx_trending_expires ON trending_topic(expires_at);
```

---

## 4. Vistas Materializadas (War Room)

```sql
-- Vista materializada para resultados por contienda
CREATE MATERIALIZED VIEW mv_contest_results AS
SELECT
    c.id AS contest_id,
    c.name AS contest_name,
    ca.id AS candidate_id,
    ca.full_name AS candidate_name,
    p.name AS party_name,
    COALESCE(SUM(vt.votes), 0) AS total_votes,
    COALESCE(SUM(vt.null_votes), 0) AS total_null_votes,
    COALESCE(SUM(vt.blank_votes), 0) AS total_blank_votes,
    COUNT(DISTINCT fi.polling_table_id) AS tables_counted,
    (SELECT COUNT(*) FROM polling_table pt WHERE pt.contest_id = c.id) AS total_tables,
    ROUND(
        COUNT(DISTINCT fi.polling_table_id)::DECIMAL /
        NULLIF((SELECT COUNT(*) FROM polling_table pt WHERE pt.contest_id = c.id), 0) * 100,
        2
    ) AS percentage_counted
FROM contest c
JOIN candidate ca ON ca.contest_id = c.id
JOIN party p ON p.id = ca.party_id
LEFT JOIN vote_tally vt ON vt.candidate_id = ca.id
LEFT JOIN form_instance fi ON fi.id = vt.form_id AND fi.processing_status = 'VALIDATED'
GROUP BY c.id, c.name, ca.id, ca.full_name, p.name
ORDER BY c.id, total_votes DESC;

-- Vista materializada para estado de procesamiento por zona
CREATE MATERIALIZED VIEW mv_processing_status AS
SELECT
    d.name AS department,
    m.name AS municipality,
    COUNT(DISTINCT pt.id) AS total_tables,
    COUNT(DISTINCT CASE WHEN fi.processing_status = 'VALIDATED' THEN pt.id END) AS validated,
    COUNT(DISTINCT CASE WHEN fi.processing_status = 'NEEDS_REVIEW' THEN pt.id END) AS needs_review,
    COUNT(DISTINCT CASE WHEN fi.processing_status = 'PROCESSING' THEN pt.id END) AS processing,
    COUNT(DISTINCT CASE WHEN fi.processing_status = 'FAILED' THEN pt.id END) AS failed,
    COUNT(DISTINCT CASE WHEN a.severity = 'CRITICAL' AND a.status = 'OPEN' THEN a.id END) AS critical_alerts
FROM department d
JOIN municipality m ON m.department_id = d.id
JOIN polling_station ps ON ps.municipality_id = m.id
JOIN polling_table pt ON pt.station_id = ps.id
LEFT JOIN form_instance fi ON fi.polling_table_id = pt.id
LEFT JOIN alert a ON a.form_id = fi.id
GROUP BY d.name, m.name
ORDER BY d.name, m.name;

-- Refresh periódico (cada 5 minutos durante elección)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_contest_results;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_processing_status;
```

---

## 5. Resumen de Relaciones

| Tabla Origen | Relación | Tabla Destino | Cardinalidad |
|--------------|----------|---------------|--------------|
| **Core DB** |
| users | tiene | sessions | 1:N |
| users | tiene | leads | 1:N |
| users | tiene | user_settings | 1:1 |
| **E14 DB - Catálogos** |
| election | tiene | contest | 1:N |
| contest | tiene | candidate | 1:N |
| party | tiene | candidate | 1:N |
| **E14 DB - Geografía** |
| department | tiene | municipality | 1:N |
| municipality | tiene | polling_station | 1:N |
| polling_station | tiene | polling_table | 1:N |
| **E14 DB - Formularios** |
| polling_table | tiene | form_instance | 1:N |
| form_instance | tiene | ocr_field | 1:N |
| form_instance | tiene | vote_tally | 1:N |
| form_instance | tiene | validation_result | 1:N |
| form_instance | tiene | discrepancy | 1:N |
| form_instance | tiene | audit_log | 1:N |
| discrepancy | genera | alert | 1:N |
| polling_table | tiene | reconciliation | 1:1 |
| **Dashboard DB** |
| analysis | tiene | tweets | 1:N |
| chat_session | tiene | chat_message | 1:N |
| users | tiene | analysis | 1:N |
| users | tiene | chat_session | 1:N |
| users | tiene | forecast | 1:N |

---

## 6. Índices Recomendados

```sql
-- Core DB
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);

-- E14 DB
CREATE INDEX idx_form_status ON form_instance(processing_status);
CREATE INDEX idx_form_table ON form_instance(polling_table_id);
CREATE INDEX idx_vote_candidate ON vote_tally(candidate_id);
CREATE INDEX idx_alert_status ON alert(status, severity);
CREATE INDEX idx_audit_form ON audit_log(form_id);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);

-- Dashboard DB
CREATE INDEX idx_analysis_candidate_date ON analysis(candidate, created_at DESC);
CREATE INDEX idx_tweets_sentiment ON tweets(sentiment);
CREATE INDEX idx_forecast_candidate_date ON forecast(candidate, forecast_date DESC);

-- Full Text Search
CREATE INDEX idx_tweets_text_search ON tweets USING gin(to_tsvector('spanish', text));
CREATE INDEX idx_analysis_summary_search ON analysis USING gin(to_tsvector('spanish', summary));
```

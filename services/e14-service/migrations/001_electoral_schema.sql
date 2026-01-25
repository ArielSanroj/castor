-- ============================================================
-- CASTOR ELECCIONES - Schema Electoral Producción
-- Versión: 1.0
-- Fecha: 2025-01
-- ============================================================

-- ============================================================
-- 1. ENUMS
-- ============================================================

CREATE TYPE form_type AS ENUM ('E14', 'E24', 'E26', 'BOLETIN', 'OTHER');
CREATE TYPE source_type AS ENUM ('WITNESS', 'OFFICIAL', 'BOLETIN', 'SCRAPER');
CREATE TYPE copy_type AS ENUM ('CLAVEROS', 'DELEGADOS', 'TRANSMISION', 'UNKNOWN');
CREATE TYPE tally_subject AS ENUM ('CANDIDATE', 'PARTY', 'BLANK', 'NULL', 'UNMARKED', 'TOTAL');
CREATE TYPE processing_status AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'NEEDS_REVIEW', 'VALIDATED');
CREATE TYPE alert_severity AS ENUM ('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE alert_status AS ENUM ('OPEN', 'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED', 'FALSE_POSITIVE');
CREATE TYPE reconciliation_status AS ENUM ('PROVISIONAL', 'FINAL', 'DISPUTED');

-- ============================================================
-- 2. CATÁLOGOS BASE
-- ============================================================

CREATE TABLE election (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    election_date DATE NOT NULL,
    election_type TEXT NOT NULL, -- PRESIDENTIAL, CONGRESS, LOCAL, CONSULTA
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE contest (
    id BIGSERIAL PRIMARY KEY,
    election_id BIGINT NOT NULL REFERENCES election(id),
    name TEXT NOT NULL,
    contest_type TEXT NOT NULL, -- PRESIDENT, SENATE, HOUSE, GOVERNOR, MAYOR, etc.
    scope TEXT NOT NULL, -- NATIONAL, DEPARTMENTAL, MUNICIPAL
    circunscripcion TEXT, -- TERRITORIAL, ESPECIAL_INDIGENA, ESPECIAL_AFRO
    total_seats INT, -- Curules a asignar (si aplica)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE party (
    id BIGSERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    short_name TEXT,
    logo_uri TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE candidate (
    id BIGSERIAL PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES contest(id),
    party_id BIGINT REFERENCES party(id),
    party_code TEXT NOT NULL,
    candidate_number TEXT, -- 101, 102, etc. para voto preferente
    name TEXT,
    list_type TEXT, -- CON_VOTO_PREFERENTE, SIN_VOTO_PREFERENTE
    ballot_position INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 3. GEOGRAFÍA (DIVIPOLA)
-- ============================================================

CREATE TABLE department (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE municipality (
    code TEXT PRIMARY KEY,
    dept_code TEXT NOT NULL REFERENCES department(code),
    name TEXT NOT NULL
);

CREATE TABLE polling_station (
    id BIGSERIAL PRIMARY KEY,
    dept_code TEXT NOT NULL REFERENCES department(code),
    muni_code TEXT NOT NULL REFERENCES municipality(code),
    zone_code TEXT NOT NULL,
    station_code TEXT NOT NULL,
    station_name TEXT,
    address TEXT,
    lat DECIMAL(10, 8),
    lon DECIMAL(11, 8),
    UNIQUE (dept_code, muni_code, zone_code, station_code)
);

CREATE TABLE polling_table (
    id BIGSERIAL PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES contest(id),
    station_id BIGINT NOT NULL REFERENCES polling_station(id),
    table_number INT NOT NULL,
    -- Denormalizados para queries rápidas
    dept_code TEXT NOT NULL,
    muni_code TEXT NOT NULL,
    zone_code TEXT NOT NULL,
    station_code TEXT NOT NULL,
    -- Mesa ID único: DEPT-MUNI-ZONE-STATION-TABLE
    mesa_id TEXT GENERATED ALWAYS AS (
        dept_code || '-' || muni_code || '-' || zone_code || '-' || station_code || '-' || LPAD(table_number::TEXT, 3, '0')
    ) STORED,
    UNIQUE (contest_id, station_id, table_number)
);

CREATE INDEX idx_polling_table_mesa ON polling_table(mesa_id);
CREATE INDEX idx_polling_table_geo ON polling_table(contest_id, dept_code, muni_code);

-- ============================================================
-- 4. FORMULARIOS Y CAPTURA
-- ============================================================

CREATE TABLE form_instance (
    id BIGSERIAL PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES contest(id),
    polling_table_id BIGINT REFERENCES polling_table(id),

    -- Tipo y fuente
    form_type form_type NOT NULL DEFAULT 'E14',
    source_type source_type NOT NULL DEFAULT 'SCRAPER',
    copy_type copy_type NOT NULL DEFAULT 'UNKNOWN',

    -- Archivo original
    object_uri TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    file_size_bytes INT,
    total_pages INT,

    -- Procesamiento OCR
    extraction_id UUID UNIQUE,
    model_version TEXT,
    processing_time_ms INT,
    overall_confidence DECIMAL(5, 4),

    -- Estado
    status processing_status DEFAULT 'PENDING',
    fields_needing_review INT DEFAULT 0,

    -- Timestamps
    captured_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ,
    validated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Usuarios
    captured_by BIGINT,
    processed_by BIGINT,
    validated_by BIGINT,

    UNIQUE (sha256)
);

CREATE INDEX idx_form_status ON form_instance(status);
CREATE INDEX idx_form_contest_table ON form_instance(contest_id, polling_table_id);
CREATE INDEX idx_form_source ON form_instance(source_type, form_type);

-- ============================================================
-- 5. OCR - EXTRACCIÓN POR CELDA
-- ============================================================

CREATE TABLE ocr_field (
    id BIGSERIAL PRIMARY KEY,
    form_id BIGINT NOT NULL REFERENCES form_instance(id) ON DELETE CASCADE,

    -- Identificación del campo
    field_key TEXT NOT NULL, -- TOTAL_SUFRAGANTES, PARTY_0011_TOTAL, CANDIDATE_0011_101, etc.
    page_number INT NOT NULL DEFAULT 1,

    -- Referencia a candidato/partido (si aplica)
    party_code TEXT,
    candidate_number TEXT,

    -- Valores extraídos
    value_raw TEXT, -- Valor tal cual se leyó
    value_int INT, -- Valor parseado como entero
    value_normalized TEXT, -- Valor normalizado

    -- Evidencia OCR
    confidence DECIMAL(5, 4) NOT NULL,
    bbox JSONB, -- {x, y, width, height}
    snippet_uri TEXT, -- Recorte de la celda

    -- Review
    needs_review BOOLEAN DEFAULT FALSE,
    reviewed BOOLEAN DEFAULT FALSE,
    reviewed_by BIGINT,
    reviewed_at TIMESTAMPTZ,
    original_value TEXT, -- Si se corrigió

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ocr_form ON ocr_field(form_id);
CREATE INDEX idx_ocr_review ON ocr_field(needs_review) WHERE needs_review = TRUE;
CREATE INDEX idx_ocr_field_key ON ocr_field(form_id, field_key);

-- ============================================================
-- 6. VOTE TALLY - VOTOS NORMALIZADOS (EL CORAZÓN)
-- ============================================================

CREATE TABLE vote_tally (
    id BIGSERIAL PRIMARY KEY,
    form_id BIGINT NOT NULL REFERENCES form_instance(id) ON DELETE CASCADE,
    contest_id BIGINT NOT NULL REFERENCES contest(id),
    polling_table_id BIGINT REFERENCES polling_table(id),

    -- Qué se está contando
    subject_type tally_subject NOT NULL,
    party_code TEXT, -- Para PARTY o CANDIDATE
    candidate_number TEXT, -- Para CANDIDATE con voto preferente

    -- Votos
    votes INT NOT NULL DEFAULT 0,

    -- Metadata OCR
    confidence DECIMAL(5, 4),
    needs_review BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraint: CANDIDATE requiere party_code
    CHECK (
        (subject_type = 'CANDIDATE' AND party_code IS NOT NULL)
        OR (subject_type = 'PARTY' AND party_code IS NOT NULL AND candidate_number IS NULL)
        OR (subject_type NOT IN ('CANDIDATE', 'PARTY') AND party_code IS NULL)
    )
);

CREATE INDEX idx_tally_form ON vote_tally(form_id);
CREATE INDEX idx_tally_table ON vote_tally(contest_id, polling_table_id);
CREATE INDEX idx_tally_party ON vote_tally(contest_id, party_code) WHERE party_code IS NOT NULL;
CREATE INDEX idx_tally_subject ON vote_tally(contest_id, subject_type);

-- ============================================================
-- 7. NIVELACIÓN DE MESA
-- ============================================================

CREATE TABLE mesa_leveling (
    id BIGSERIAL PRIMARY KEY,
    form_id BIGINT NOT NULL REFERENCES form_instance(id) ON DELETE CASCADE,
    polling_table_id BIGINT REFERENCES polling_table(id),

    -- Valores de nivelación
    total_sufragantes_e11 INT NOT NULL,
    total_votos_urna INT NOT NULL,
    total_votos_incinerados INT DEFAULT 0,

    -- Confianza
    confidence_sufragantes DECIMAL(5, 4),
    confidence_urna DECIMAL(5, 4),

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (form_id)
);

-- ============================================================
-- 8. VALIDACIONES
-- ============================================================

CREATE TABLE validation_rule (
    id SERIAL PRIMARY KEY,
    rule_key TEXT NOT NULL UNIQUE,
    rule_name TEXT NOT NULL,
    description TEXT,
    severity alert_severity NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Reglas predefinidas
INSERT INTO validation_rule (rule_key, rule_name, description, severity) VALUES
('NIV_001', 'SUFRAGANTES_VS_URNA', 'Sufragantes E-11 debe ser >= votos en urna', 'HIGH'),
('SUM_001', 'SUMA_IGUAL_URNA', 'Suma de todos los votos debe igualar total en urna', 'HIGH'),
('SUM_002', 'SUMA_PARTIDO', 'Total partido = votos agrupación + votos candidatos', 'MEDIUM'),
('EXC_001', 'EXCEDE_SUFRAGANTES', 'Ningún partido puede tener más votos que sufragantes', 'CRITICAL'),
('OCR_001', 'CONFIDENCE_BAJA', 'Campo con confianza OCR < 0.7', 'MEDIUM'),
('FRM_001', 'FIRMAS_JURADOS', 'Debe haber al menos 3 firmas de jurados', 'LOW');

CREATE TABLE validation_result (
    id BIGSERIAL PRIMARY KEY,
    form_id BIGINT NOT NULL REFERENCES form_instance(id) ON DELETE CASCADE,
    rule_key TEXT NOT NULL REFERENCES validation_rule(rule_key),

    passed BOOLEAN NOT NULL,
    severity alert_severity NOT NULL,
    message TEXT,

    expected_value INT,
    actual_value INT,
    delta INT,
    details JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_validation_form ON validation_result(form_id);
CREATE INDEX idx_validation_failed ON validation_result(passed) WHERE passed = FALSE;

-- ============================================================
-- 9. DISCREPANCIAS Y ALERTAS
-- ============================================================

CREATE TABLE discrepancy (
    id BIGSERIAL PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES contest(id),
    polling_table_id BIGINT NOT NULL REFERENCES polling_table(id),

    -- Formularios comparados
    form_a_id BIGINT NOT NULL REFERENCES form_instance(id),
    form_b_id BIGINT NOT NULL REFERENCES form_instance(id),
    form_a_source source_type NOT NULL,
    form_b_source source_type NOT NULL,

    -- Métricas
    metric TEXT NOT NULL, -- TOTAL, BY_PARTY, BY_CANDIDATE
    delta_total INT,
    delta_json JSONB, -- Detalle por partido/candidato

    severity alert_severity NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_discrepancy_table ON discrepancy(contest_id, polling_table_id);

CREATE TABLE alert (
    id BIGSERIAL PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES contest(id),
    polling_table_id BIGINT REFERENCES polling_table(id),
    form_id BIGINT REFERENCES form_instance(id),
    discrepancy_id BIGINT REFERENCES discrepancy(id),

    -- Tipo y severidad
    alert_type TEXT NOT NULL, -- ARITHMETIC, SOURCE_MISMATCH, OCR_LOW_CONF, EXCEEDS_VOTERS, etc.
    severity alert_severity NOT NULL,
    status alert_status DEFAULT 'OPEN',

    -- Descripción
    title TEXT NOT NULL,
    message TEXT,
    evidence JSONB,

    -- Asignación
    assigned_to BIGINT,
    assigned_at TIMESTAMPTZ,

    -- Resolución
    resolved_by BIGINT,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alert_status ON alert(status);
CREATE INDEX idx_alert_severity ON alert(severity);
CREATE INDEX idx_alert_open_critical ON alert(status, severity) WHERE status = 'OPEN';
CREATE INDEX idx_alert_table ON alert(contest_id, polling_table_id);

-- ============================================================
-- 10. RECONCILIACIÓN
-- ============================================================

CREATE TABLE reconciliation (
    contest_id BIGINT NOT NULL REFERENCES contest(id),
    polling_table_id BIGINT NOT NULL REFERENCES polling_table(id),

    -- Formulario elegido como "verdad"
    chosen_form_id BIGINT NOT NULL REFERENCES form_instance(id),

    -- Estado
    status reconciliation_status NOT NULL DEFAULT 'PROVISIONAL',

    -- Justificación
    reason JSONB, -- Por qué se eligió este formulario
    priority_score DECIMAL(5, 2), -- Score calculado

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    finalized_at TIMESTAMPTZ,
    finalized_by BIGINT,

    PRIMARY KEY (contest_id, polling_table_id)
);

-- ============================================================
-- 11. AUDITORÍA (INMUTABLE)
-- ============================================================

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,

    -- Quién
    actor_user_id BIGINT,
    actor_username TEXT,
    actor_ip INET,

    -- Qué
    entity_type TEXT NOT NULL, -- form_instance, vote_tally, alert, etc.
    entity_id BIGINT NOT NULL,
    action TEXT NOT NULL, -- CREATE, UPDATE, DELETE, VALIDATE, RECONCILE, etc.

    -- Estado antes/después
    before_state JSONB,
    after_state JSONB,
    changes JSONB,

    -- Cuándo
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_time ON audit_log(created_at);
CREATE INDEX idx_audit_user ON audit_log(actor_user_id);

-- ============================================================
-- 12. AGREGADOS PARA WAR ROOM (MATERIALIZED VIEW)
-- ============================================================

CREATE MATERIALIZED VIEW mv_contest_results AS
SELECT
    vt.contest_id,
    pt.dept_code,
    pt.muni_code,
    vt.party_code,
    vt.subject_type,
    SUM(vt.votes) as total_votes,
    COUNT(DISTINCT vt.polling_table_id) as mesas_count
FROM vote_tally vt
JOIN reconciliation r ON r.polling_table_id = vt.polling_table_id
    AND r.contest_id = vt.contest_id
JOIN polling_table pt ON pt.id = vt.polling_table_id
WHERE vt.form_id = r.chosen_form_id
GROUP BY vt.contest_id, pt.dept_code, pt.muni_code, vt.party_code, vt.subject_type;

CREATE UNIQUE INDEX idx_mv_results ON mv_contest_results(contest_id, dept_code, muni_code, party_code, subject_type);

-- Refresh command (ejecutar periódicamente o con trigger)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_contest_results;

CREATE MATERIALIZED VIEW mv_processing_status AS
SELECT
    f.contest_id,
    pt.dept_code,
    pt.muni_code,
    COUNT(*) as total_mesas,
    COUNT(f.id) FILTER (WHERE f.status = 'VALIDATED') as validated,
    COUNT(f.id) FILTER (WHERE f.status = 'NEEDS_REVIEW') as needs_review,
    COUNT(f.id) FILTER (WHERE f.status = 'PENDING') as pending,
    COUNT(a.id) FILTER (WHERE a.status = 'OPEN' AND a.severity IN ('HIGH', 'CRITICAL')) as critical_alerts
FROM polling_table pt
LEFT JOIN form_instance f ON f.polling_table_id = pt.id AND f.form_type = 'E14'
LEFT JOIN alert a ON a.polling_table_id = pt.id
GROUP BY f.contest_id, pt.dept_code, pt.muni_code;

-- ============================================================
-- 13. FUNCIONES ÚTILES
-- ============================================================

-- Función para calcular score de prioridad de un formulario
CREATE OR REPLACE FUNCTION calculate_form_priority(form_id_param BIGINT)
RETURNS DECIMAL AS $$
DECLARE
    score DECIMAL := 0;
    form_record RECORD;
BEGIN
    SELECT * INTO form_record FROM form_instance WHERE id = form_id_param;

    -- Prioridad por fuente
    score := score + CASE form_record.source_type
        WHEN 'WITNESS' THEN 30
        WHEN 'OFFICIAL' THEN 25
        WHEN 'SCRAPER' THEN 20
        WHEN 'BOLETIN' THEN 10
    END;

    -- Prioridad por tipo de copia
    score := score + CASE form_record.copy_type
        WHEN 'CLAVEROS' THEN 20
        WHEN 'DELEGADOS' THEN 15
        WHEN 'TRANSMISION' THEN 10
        ELSE 5
    END;

    -- Prioridad por confianza OCR
    score := score + COALESCE(form_record.overall_confidence, 0) * 30;

    -- Penalización por campos que necesitan revisión
    score := score - COALESCE(form_record.fields_needing_review, 0) * 2;

    -- Prioridad por validaciones pasadas
    score := score + (
        SELECT COUNT(*) * 5
        FROM validation_result
        WHERE form_id = form_id_param AND passed = TRUE
    );

    RETURN GREATEST(score, 0);
END;
$$ LANGUAGE plpgsql;

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_form_instance_updated
    BEFORE UPDATE ON form_instance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_alert_updated
    BEFORE UPDATE ON alert
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_reconciliation_updated
    BEFORE UPDATE ON reconciliation
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- 14. COMENTARIOS DE DOCUMENTACIÓN
-- ============================================================

COMMENT ON TABLE form_instance IS 'Instancias de formularios capturados (E-14, E-24, boletines)';
COMMENT ON TABLE vote_tally IS 'Votos normalizados por candidato/partido/especiales';
COMMENT ON TABLE reconciliation IS 'Fuente elegida como "verdad" por mesa';
COMMENT ON TABLE audit_log IS 'Log inmutable de todas las acciones';
COMMENT ON COLUMN vote_tally.subject_type IS 'CANDIDATE=voto preferente, PARTY=voto lista, BLANK/NULL/UNMARKED=especiales';
COMMENT ON COLUMN reconciliation.status IS 'PROVISIONAL=noche electoral, FINAL=post-escrutinio';

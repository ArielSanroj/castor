-- ============================================================
-- CASTOR ELECCIONES - Schema Electoral v2.0
-- Consulta Nacional 8 de Marzo 2026 + Soporte Multi-página
-- ============================================================
--
-- Cambios vs v1:
-- 1. political_group: partidos/listas como entidad separada
-- 2. ballot_option: opciones de voto (CANDIDATE, LIST_ONLY, LIST_CANDIDATE, SPECIAL)
-- 3. form_page: soporte multi-página (Asamblea/Concejo)
-- 4. ocr_field mejorado con raw_mark para "***"
-- 5. Particionado por election_id
--
-- ============================================================

-- ============================================================
-- 1. ENUMS (actualizados)
-- ============================================================

-- Tipos de formulario
CREATE TYPE form_type AS ENUM ('E14', 'E24', 'E26', 'BOLETIN', 'OTHER');

-- Fuente del documento
CREATE TYPE source_type AS ENUM ('WITNESS', 'OFFICIAL', 'BOLETIN', 'SCRAPER');

-- Tipo de copia E-14
CREATE TYPE copy_type AS ENUM ('CLAVEROS', 'DELEGADOS', 'TRANSMISION', 'UNKNOWN');

-- Tipo de contienda
CREATE TYPE contest_type AS ENUM (
    'PRESIDENTIAL', 'GOVERNOR', 'MAYOR',           -- Boleta simple
    'SENATE', 'HOUSE', 'ASSEMBLY', 'COUNCIL',      -- Multi-página con voto preferente
    'CONSULTA', 'CONSULTA_INTERPARTIDISTA'         -- Consultas
);

-- Alcance de la contienda
CREATE TYPE contest_scope AS ENUM ('NATIONAL', 'DEPARTMENTAL', 'MUNICIPAL');

-- Tipo de opción en boleta
CREATE TYPE ballot_option_type AS ENUM (
    'CANDIDATE',       -- Candidato directo (Presidente, Gobernador, Alcalde, Consulta)
    'LIST_ONLY',       -- Voto solo por lista/partido (renglón 0 en Asamblea/Concejo)
    'LIST_CANDIDATE',  -- Candidato dentro de lista (voto preferente: 51, 52, etc.)
    'BLANK',           -- Voto en blanco
    'NULL',            -- Voto nulo
    'UNMARKED',        -- Voto no marcado
    'TOTAL'            -- Total de votos
);

-- Estado de procesamiento
CREATE TYPE processing_status AS ENUM (
    'PENDING', 'PROCESSING', 'OCR_COMPLETED',
    'NEEDS_REVIEW', 'VALIDATED', 'FAILED'
);

-- Severidad de alertas
CREATE TYPE alert_severity AS ENUM ('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

-- Estado de alertas
CREATE TYPE alert_status AS ENUM ('OPEN', 'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED', 'FALSE_POSITIVE');

-- Estado de reconciliación
CREATE TYPE reconciliation_status AS ENUM ('PROVISIONAL', 'FINAL', 'DISPUTED');


-- ============================================================
-- 2. CATÁLOGOS BASE
-- ============================================================

-- Elección (proceso electoral)
CREATE TABLE election (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    election_date DATE NOT NULL,
    election_type TEXT NOT NULL,  -- PRESIDENTIAL, TERRITORIAL, CONSULTA
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Contienda (corporación dentro de una elección)
CREATE TABLE contest (
    id BIGSERIAL PRIMARY KEY,
    election_id BIGINT NOT NULL REFERENCES election(id),
    name TEXT NOT NULL,
    contest_type contest_type NOT NULL,
    scope contest_scope NOT NULL,
    circunscripcion TEXT,  -- TERRITORIAL, ESPECIAL_INDIGENA, ESPECIAL_AFRO
    total_seats INT,
    -- Template de OCR a usar
    template_family TEXT DEFAULT 'E14',
    template_version TEXT,  -- E14_CONSULTA_2026_V1, E14_ASAMBLEA_V1, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contest_election ON contest(election_id);


-- ============================================================
-- 3. OFERTA ELECTORAL (Partidos + Opciones de Boleta)
-- ============================================================

-- Agrupación política (partido/lista/coalición)
CREATE TABLE political_group (
    id BIGSERIAL PRIMARY KEY,
    code TEXT NOT NULL,           -- Código en tarjetón (ej: "11", "0302")
    name TEXT NOT NULL,           -- Nombre completo
    short_name TEXT,              -- Sigla
    logo_uri TEXT,
    group_type TEXT,              -- PARTIDO, COALICION, MOVIMIENTO, INDEPENDIENTE
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(code)
);

-- Opción de boleta (candidato, lista, especiales)
CREATE TABLE ballot_option (
    id BIGSERIAL PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES contest(id),
    option_type ballot_option_type NOT NULL,

    -- Para CANDIDATE / LIST_ONLY / LIST_CANDIDATE
    political_group_id BIGINT REFERENCES political_group(id),

    -- Identificación en boleta
    ballot_code TEXT,             -- Código en tarjetón (1, 2, 51, 52, etc.)
    ballot_position INT,          -- Posición en tarjetón

    -- Candidato (si aplica)
    candidate_name TEXT,
    candidate_ordinal INT,        -- Para voto preferente: 51, 52, 53...

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(contest_id, option_type, ballot_code)
);

CREATE INDEX idx_ballot_option_contest ON ballot_option(contest_id);
CREATE INDEX idx_ballot_option_group ON ballot_option(political_group_id);


-- ============================================================
-- 4. GEOGRAFÍA (DIVIPOLA)
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

    -- Mesa ID calculado
    mesa_id TEXT GENERATED ALWAYS AS (
        dept_code || '-' || muni_code || '-' || zone_code || '-' ||
        station_code || '-' || LPAD(table_number::TEXT, 3, '0')
    ) STORED,

    UNIQUE (contest_id, station_id, table_number)
);

CREATE INDEX idx_polling_table_mesa ON polling_table(mesa_id);
CREATE INDEX idx_polling_table_geo ON polling_table(contest_id, dept_code, muni_code);


-- ============================================================
-- 5. EVIDENCIA (Documentos + Páginas)
-- ============================================================

-- Instancia de formulario
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

    -- Header extraído del documento
    reported_election_date DATE,
    reported_election_label TEXT,

    -- Procesamiento OCR
    extraction_id UUID UNIQUE,
    model_version TEXT,
    template_version TEXT,
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

-- Páginas del formulario (NUEVO: soporte multi-página)
CREATE TABLE form_page (
    id BIGSERIAL PRIMARY KEY,
    form_id BIGINT NOT NULL REFERENCES form_instance(id) ON DELETE CASCADE,
    page_no INT NOT NULL,
    page_sha256 TEXT NOT NULL,
    image_uri TEXT NOT NULL,

    -- Para Asamblea/Concejo: qué partido/lista está en esta página
    political_group_id BIGINT REFERENCES political_group(id),

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (form_id, page_no)
);

CREATE INDEX idx_form_page_form ON form_page(form_id);


-- ============================================================
-- 6. EXTRACCIÓN OCR (Campos individuales)
-- ============================================================

CREATE TABLE ocr_field (
    id BIGSERIAL PRIMARY KEY,
    form_id BIGINT NOT NULL REFERENCES form_instance(id) ON DELETE CASCADE,
    page_no INT NOT NULL DEFAULT 1,

    -- Identificación del campo
    field_key TEXT NOT NULL,  -- TOTAL_SUFRAGANTES_E11, CANDIDATE_ROW_1, etc.

    -- Referencia a opción de boleta (si es voto)
    ballot_option_id BIGINT REFERENCES ballot_option(id),

    -- Valores extraídos
    raw_text TEXT,            -- Texto tal cual se leyó
    raw_mark TEXT,            -- Marca especial: "*", "**", "***"
    value_int INT,            -- Valor normalizado
    value_text TEXT,          -- Para campos no numéricos
    value_bool BOOLEAN,       -- Para checkboxes (HUBO_RECUENTO)

    -- Evidencia OCR
    confidence DECIMAL(5, 4) NOT NULL,
    bbox JSONB,               -- {x, y, width, height}
    snippet_uri TEXT,

    -- Review
    needs_review BOOLEAN DEFAULT FALSE,
    notes TEXT,
    reviewed BOOLEAN DEFAULT FALSE,
    reviewed_by BIGINT,
    reviewed_at TIMESTAMPTZ,
    original_value TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ocr_form ON ocr_field(form_id);
CREATE INDEX idx_ocr_review ON ocr_field(needs_review) WHERE needs_review = TRUE;
CREATE INDEX idx_ocr_field_key ON ocr_field(form_id, field_key);
CREATE INDEX idx_ocr_ballot_option ON ocr_field(ballot_option_id);


-- ============================================================
-- 7. VOTOS NORMALIZADOS (Hechos)
-- ============================================================

CREATE TABLE vote_tally (
    id BIGSERIAL PRIMARY KEY,
    form_id BIGINT NOT NULL REFERENCES form_instance(id) ON DELETE CASCADE,
    contest_id BIGINT NOT NULL REFERENCES contest(id),
    polling_table_id BIGINT REFERENCES polling_table(id),

    -- Opción de boleta
    ballot_option_id BIGINT NOT NULL REFERENCES ballot_option(id),

    -- Votos
    votes INT NOT NULL DEFAULT 0,

    -- Ranking de fuente (para reconciliación)
    source_rank INT DEFAULT 0,  -- WITNESS=30, OFFICIAL=25, SCRAPER=20, BOLETIN=10

    -- Metadata OCR
    confidence DECIMAL(5, 4),
    needs_review BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (form_id, ballot_option_id)
);

CREATE INDEX idx_tally_form ON vote_tally(form_id);
CREATE INDEX idx_tally_table ON vote_tally(contest_id, polling_table_id);
CREATE INDEX idx_tally_option ON vote_tally(ballot_option_id);


-- ============================================================
-- 8. NIVELACIÓN DE MESA
-- ============================================================

CREATE TABLE mesa_leveling (
    id BIGSERIAL PRIMARY KEY,
    form_id BIGINT NOT NULL REFERENCES form_instance(id) ON DELETE CASCADE UNIQUE,
    polling_table_id BIGINT REFERENCES polling_table(id),

    total_sufragantes_e11 INT NOT NULL,
    total_votos_urna INT NOT NULL,
    total_votos_incinerados INT DEFAULT 0,

    confidence_sufragantes DECIMAL(5, 4),
    confidence_urna DECIMAL(5, 4),

    -- Marcas especiales
    sufragantes_raw_mark TEXT,  -- Si era "***"
    urna_raw_mark TEXT,
    incinerados_raw_mark TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================
-- 9. VALIDACIONES
-- ============================================================

CREATE TABLE validation_rule (
    id SERIAL PRIMARY KEY,
    rule_key TEXT NOT NULL UNIQUE,
    rule_name TEXT NOT NULL,
    description TEXT,
    severity alert_severity NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Reglas predefinidas para Consulta
INSERT INTO validation_rule (rule_key, rule_name, description, severity) VALUES
('E11_EQUALS_URNA', 'Sufragantes = Urna', 'Total sufragantes E-11 debe ser >= votos en urna', 'HIGH'),
('SUM_EQUALS_TOTAL', 'Suma = Total', 'Suma de candidatos + especiales = total mesa', 'HIGH'),
('NO_EXCEEDS_VOTERS', 'No excede sufragantes', 'Ningún candidato puede tener más votos que sufragantes', 'CRITICAL'),
('LOW_CONFIDENCE_REVIEW', 'Confianza baja', 'Campos con confianza < 0.70 requieren revisión', 'MEDIUM'),
('ASTERISK_NORMALIZATION', 'Normalización ***', 'Campos marcados con *** normalizados a 0', 'LOW'),
('SIGNATURE_COUNT', 'Firmas jurados', 'Debe haber al menos 3 firmas', 'LOW');

CREATE TABLE validation_result (
    id BIGSERIAL PRIMARY KEY,
    form_id BIGINT NOT NULL REFERENCES form_instance(id) ON DELETE CASCADE,
    rule_key TEXT NOT NULL REFERENCES validation_rule(rule_key),

    passed BOOLEAN NOT NULL,
    severity alert_severity NOT NULL,
    message TEXT,
    details JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_validation_form ON validation_result(form_id);
CREATE INDEX idx_validation_failed ON validation_result(passed) WHERE passed = FALSE;


-- ============================================================
-- 10. ALERTAS Y DISCREPANCIAS
-- ============================================================

CREATE TABLE alert (
    id BIGSERIAL PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES contest(id),
    polling_table_id BIGINT REFERENCES polling_table(id),
    form_id BIGINT REFERENCES form_instance(id),

    alert_type TEXT NOT NULL,  -- OCR_LOW_CONF, ARITHMETIC_FAIL, SOURCE_MISMATCH
    severity alert_severity NOT NULL,
    status alert_status DEFAULT 'OPEN',

    title TEXT NOT NULL,
    message TEXT,
    evidence JSONB,

    assigned_to BIGINT,
    assigned_at TIMESTAMPTZ,
    resolved_by BIGINT,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alert_status ON alert(status);
CREATE INDEX idx_alert_open ON alert(status, severity) WHERE status = 'OPEN';
CREATE INDEX idx_alert_table ON alert(contest_id, polling_table_id);

CREATE TABLE discrepancy (
    id BIGSERIAL PRIMARY KEY,
    contest_id BIGINT NOT NULL REFERENCES contest(id),
    polling_table_id BIGINT NOT NULL REFERENCES polling_table(id),

    form_a_id BIGINT NOT NULL REFERENCES form_instance(id),
    form_b_id BIGINT NOT NULL REFERENCES form_instance(id),
    form_a_source source_type NOT NULL,
    form_b_source source_type NOT NULL,

    metric TEXT NOT NULL,  -- TOTAL, BY_CANDIDATE, BY_OPTION
    delta_total INT,
    delta_json JSONB,

    severity alert_severity NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_discrepancy_table ON discrepancy(contest_id, polling_table_id);


-- ============================================================
-- 11. RECONCILIACIÓN
-- ============================================================

CREATE TABLE reconciliation (
    contest_id BIGINT NOT NULL REFERENCES contest(id),
    polling_table_id BIGINT NOT NULL REFERENCES polling_table(id),

    chosen_form_id BIGINT NOT NULL REFERENCES form_instance(id),
    status reconciliation_status NOT NULL DEFAULT 'PROVISIONAL',

    reason JSONB,
    priority_score DECIMAL(5, 2),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    finalized_at TIMESTAMPTZ,
    finalized_by BIGINT,

    PRIMARY KEY (contest_id, polling_table_id)
);


-- ============================================================
-- 12. AUDITORÍA
-- ============================================================

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,

    actor_user_id BIGINT,
    actor_username TEXT,
    actor_ip INET,

    entity_type TEXT NOT NULL,
    entity_id BIGINT NOT NULL,
    action TEXT NOT NULL,

    before_state JSONB,
    after_state JSONB,
    changes JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_time ON audit_log(created_at);


-- ============================================================
-- 13. TRAINING DATA (para fine-tuning)
-- ============================================================

CREATE TABLE training_sample (
    id BIGSERIAL PRIMARY KEY,
    form_id BIGINT REFERENCES form_instance(id),
    page_no INT,

    -- Recorte de celda
    bbox JSONB,
    image_crop_uri TEXT,

    -- Labels
    field_key TEXT,
    ballot_option_id BIGINT REFERENCES ballot_option(id),
    label_text TEXT,
    label_int INT,

    -- Anotación
    annotated_by BIGINT,
    annotated_at TIMESTAMPTZ,
    is_validated BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE model_run (
    id BIGSERIAL PRIMARY KEY,
    model_version TEXT NOT NULL,
    model_type TEXT,  -- CLASSIFIER, DIGIT_RECOGNIZER, LAYOUT_DETECTOR
    train_data_hash TEXT,
    metrics JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================
-- 14. VIEWS PARA WAR ROOM
-- ============================================================

-- Vista de progreso por municipio
CREATE VIEW vw_processing_progress AS
SELECT
    c.id as contest_id,
    c.name as contest_name,
    pt.dept_code,
    pt.muni_code,
    COUNT(DISTINCT pt.id) as total_mesas,
    COUNT(DISTINCT f.id) FILTER (WHERE f.status = 'VALIDATED') as validated,
    COUNT(DISTINCT f.id) FILTER (WHERE f.status = 'NEEDS_REVIEW') as needs_review,
    COUNT(DISTINCT f.id) FILTER (WHERE f.status = 'PENDING') as pending,
    COUNT(a.id) FILTER (WHERE a.status = 'OPEN' AND a.severity IN ('HIGH', 'CRITICAL')) as critical_alerts
FROM contest c
JOIN polling_table pt ON pt.contest_id = c.id
LEFT JOIN form_instance f ON f.polling_table_id = pt.id
LEFT JOIN alert a ON a.polling_table_id = pt.id
GROUP BY c.id, c.name, pt.dept_code, pt.muni_code;

-- Vista de resultados reconciliados
CREATE VIEW vw_reconciled_results AS
SELECT
    r.contest_id,
    pt.dept_code,
    pt.muni_code,
    bo.option_type,
    bo.ballot_code,
    bo.candidate_name,
    pg.name as political_group_name,
    SUM(vt.votes) as total_votes,
    COUNT(DISTINCT r.polling_table_id) as mesas_count
FROM reconciliation r
JOIN polling_table pt ON pt.id = r.polling_table_id
JOIN vote_tally vt ON vt.form_id = r.chosen_form_id
JOIN ballot_option bo ON bo.id = vt.ballot_option_id
LEFT JOIN political_group pg ON pg.id = bo.political_group_id
WHERE r.status IN ('PROVISIONAL', 'FINAL')
GROUP BY r.contest_id, pt.dept_code, pt.muni_code,
         bo.option_type, bo.ballot_code, bo.candidate_name, pg.name;


-- ============================================================
-- 15. FUNCIONES
-- ============================================================

-- Función para calcular prioridad de formulario
CREATE OR REPLACE FUNCTION calculate_form_priority(form_id_param BIGINT)
RETURNS DECIMAL AS $$
DECLARE
    score DECIMAL := 0;
    form_record RECORD;
BEGIN
    SELECT * INTO form_record FROM form_instance WHERE id = form_id_param;

    -- Por fuente
    score := score + CASE form_record.source_type
        WHEN 'WITNESS' THEN 30
        WHEN 'OFFICIAL' THEN 25
        WHEN 'SCRAPER' THEN 20
        WHEN 'BOLETIN' THEN 10
    END;

    -- Por tipo de copia
    score := score + CASE form_record.copy_type
        WHEN 'CLAVEROS' THEN 20
        WHEN 'DELEGADOS' THEN 15
        WHEN 'TRANSMISION' THEN 10
        ELSE 5
    END;

    -- Por confianza OCR
    score := score + COALESCE(form_record.overall_confidence, 0) * 30;

    -- Penalización por campos pendientes
    score := score - COALESCE(form_record.fields_needing_review, 0) * 2;

    RETURN GREATEST(score, 0);
END;
$$ LANGUAGE plpgsql;

-- Trigger para updated_at
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
-- 16. DATOS INICIALES PARA CONSULTA 8 MARZO 2026
-- ============================================================

-- Elección
INSERT INTO election (id, name, election_date, election_type, status) VALUES
(1, 'Gran Consulta Nacional 2026', '2026-03-08', 'CONSULTA', 'ACTIVE');

-- Contienda (ejemplo: Consulta Interpartidista)
INSERT INTO contest (id, election_id, name, contest_type, scope, template_version) VALUES
(1, 1, 'Consulta Interpartidista Nacional', 'CONSULTA_INTERPARTIDISTA', 'NATIONAL', 'E14_CONSULTA_2026_V1');

-- Opciones de boleta (ejemplo con precandidatos ficticios)
-- Los reales se cargarán del catálogo oficial
INSERT INTO ballot_option (contest_id, option_type, ballot_code, ballot_position, candidate_name) VALUES
(1, 'CANDIDATE', '1', 1, 'PRECANDIDATO 1'),
(1, 'CANDIDATE', '2', 2, 'PRECANDIDATO 2'),
(1, 'CANDIDATE', '3', 3, 'PRECANDIDATO 3'),
(1, 'CANDIDATE', '4', 4, 'PRECANDIDATO 4'),
(1, 'CANDIDATE', '5', 5, 'PRECANDIDATO 5'),
-- Especiales
(1, 'BLANK', 'BLANK', 100, NULL),
(1, 'NULL', 'NULL', 101, NULL),
(1, 'UNMARKED', 'UNMARKED', 102, NULL),
(1, 'TOTAL', 'TOTAL', 103, NULL);


-- ============================================================
-- COMENTARIOS
-- ============================================================

COMMENT ON TABLE political_group IS 'Agrupaciones políticas (partidos, coaliciones, movimientos)';
COMMENT ON TABLE ballot_option IS 'Opciones de voto: candidatos, listas, especiales';
COMMENT ON TABLE form_page IS 'Páginas individuales de formularios multi-página (Asamblea/Concejo)';
COMMENT ON TABLE ocr_field IS 'Campos extraídos por OCR con raw_mark para símbolos especiales';
COMMENT ON TABLE vote_tally IS 'Votos normalizados por opción de boleta';
COMMENT ON TABLE training_sample IS 'Muestras para fine-tuning del modelo OCR';
COMMENT ON COLUMN ocr_field.raw_mark IS 'Marca especial detectada: *, **, *** (indica campo tachado o ilegible)';
COMMENT ON COLUMN vote_tally.source_rank IS 'Ranking de confiabilidad: WITNESS=30, OFFICIAL=25, SCRAPER=20, BOLETIN=10';

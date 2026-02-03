-- ============================================================
-- CASTOR ELECCIONES - Schema de Testigos Electorales
-- Versión: 3.0
-- Fecha: 2026-01
-- Descripción: Sistema de registro y notificación de testigos via QR + PWA
-- ============================================================

-- ============================================================
-- 1. ENUMS PARA TESTIGOS
-- ============================================================

CREATE TYPE witness_status AS ENUM (
    'PENDING',      -- Registrado pero no ha confirmado
    'ACTIVE',       -- Activo y disponible
    'ASSIGNED',     -- Asignado a una mesa
    'BUSY',         -- Ocupado en tarea
    'OFFLINE',      -- No disponible
    'INACTIVE'      -- Dado de baja
);

CREATE TYPE assignment_status AS ENUM (
    'PENDING',      -- Asignación pendiente de aceptar
    'ACCEPTED',     -- Testigo aceptó la asignación
    'IN_TRANSIT',   -- En camino a la mesa
    'ON_SITE',      -- En el sitio
    'COMPLETED',    -- Tarea completada
    'CANCELLED',    -- Asignación cancelada
    'REJECTED'      -- Testigo rechazó la asignación
);

-- ============================================================
-- 2. TABLA PRINCIPAL DE TESTIGOS
-- ============================================================

CREATE TABLE witness (
    id BIGSERIAL PRIMARY KEY,

    -- Código único para registro via QR
    registration_code UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,

    -- Información personal
    cedula TEXT UNIQUE,                  -- Cédula de ciudadanía (opcional hasta confirmar)
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,

    -- Estado
    status witness_status NOT NULL DEFAULT 'PENDING',

    -- Ubicación actual (GPS)
    current_lat DECIMAL(10, 8),
    current_lon DECIMAL(11, 8),
    location_updated_at TIMESTAMPTZ,
    current_zone TEXT,                   -- Zona/barrio actual

    -- Push Notifications (Web Push API)
    push_subscription JSONB,             -- {endpoint, keys: {p256dh, auth}}
    push_enabled BOOLEAN DEFAULT FALSE,

    -- Zona de cobertura asignada (donde el testigo puede cubrir)
    coverage_dept_code TEXT REFERENCES department(code),
    coverage_dept_name TEXT,
    coverage_muni_code TEXT REFERENCES municipality(code),
    coverage_muni_name TEXT,
    coverage_station_id BIGINT REFERENCES polling_station(id),
    coverage_station_name TEXT,                -- Nombre del puesto de votación
    coverage_zone_code TEXT,                   -- Zona dentro del municipio

    -- Metadatos
    device_info JSONB,                   -- Info del dispositivo
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Usuario que lo registró (admin)
    registered_by BIGINT,
    notes TEXT
);

CREATE INDEX idx_witness_status ON witness(status);
CREATE INDEX idx_witness_registration ON witness(registration_code);
CREATE INDEX idx_witness_phone ON witness(phone);
CREATE INDEX idx_witness_location ON witness(current_lat, current_lon) WHERE current_lat IS NOT NULL;
CREATE INDEX idx_witness_coverage_dept ON witness(coverage_dept_code);
CREATE INDEX idx_witness_coverage_muni ON witness(coverage_dept_code, coverage_muni_code);
CREATE INDEX idx_witness_coverage_station ON witness(coverage_station_id);
CREATE INDEX idx_witness_push ON witness(push_enabled) WHERE push_enabled = TRUE;

-- ============================================================
-- 3. ASIGNACIONES DE TESTIGOS A MESAS
-- ============================================================

CREATE TABLE witness_assignment (
    id BIGSERIAL PRIMARY KEY,

    witness_id BIGINT NOT NULL REFERENCES witness(id) ON DELETE CASCADE,
    polling_table_id BIGINT NOT NULL REFERENCES polling_table(id),
    contest_id BIGINT NOT NULL REFERENCES contest(id),

    -- Estado de la asignación
    status assignment_status NOT NULL DEFAULT 'PENDING',

    -- Prioridad y razón
    priority INT DEFAULT 0,              -- Mayor = más prioritario
    reason TEXT,                         -- Razón de la asignación

    -- Timestamps del flujo
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    notified_at TIMESTAMPTZ,             -- Cuando se envió la notificación
    accepted_at TIMESTAMPTZ,
    arrived_at TIMESTAMPTZ,              -- Cuando llegó al sitio
    completed_at TIMESTAMPTZ,

    -- Asignado por
    assigned_by BIGINT,

    -- Notas y resultado
    notes TEXT,
    result JSONB,                        -- Resultado de la visita

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Un testigo no puede tener múltiples asignaciones activas a la misma mesa
    UNIQUE (witness_id, polling_table_id, contest_id)
        WHERE status NOT IN ('COMPLETED', 'CANCELLED', 'REJECTED')
);

CREATE INDEX idx_assignment_witness ON witness_assignment(witness_id);
CREATE INDEX idx_assignment_table ON witness_assignment(polling_table_id);
CREATE INDEX idx_assignment_status ON witness_assignment(status);
CREATE INDEX idx_assignment_active ON witness_assignment(witness_id, status)
    WHERE status NOT IN ('COMPLETED', 'CANCELLED', 'REJECTED');

-- ============================================================
-- 4. HISTORIAL DE NOTIFICACIONES
-- ============================================================

CREATE TABLE witness_notification (
    id BIGSERIAL PRIMARY KEY,

    witness_id BIGINT NOT NULL REFERENCES witness(id) ON DELETE CASCADE,
    assignment_id BIGINT REFERENCES witness_assignment(id) ON DELETE SET NULL,

    -- Tipo y contenido
    notification_type TEXT NOT NULL,     -- ASSIGNMENT, ALERT, UPDATE, REMINDER
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    data JSONB,                          -- Datos adicionales para la app

    -- Estado de entrega
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,

    -- Resultado del push
    push_success BOOLEAN,
    push_error TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notification_witness ON witness_notification(witness_id);
CREATE INDEX idx_notification_sent ON witness_notification(sent_at);

-- ============================================================
-- 5. CÓDIGOS QR DE REGISTRO
-- ============================================================

CREATE TABLE witness_qr_code (
    id BIGSERIAL PRIMARY KEY,

    -- Código único del QR
    code UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,

    -- Configuración del QR
    dept_code TEXT REFERENCES department(code),
    muni_code TEXT REFERENCES municipality(code),
    station_id BIGINT REFERENCES polling_station(id),

    -- Estado
    is_active BOOLEAN DEFAULT TRUE,
    max_uses INT DEFAULT 1,              -- Cuántas veces se puede usar
    current_uses INT DEFAULT 0,
    expires_at TIMESTAMPTZ,

    -- Quién lo creó
    created_by BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Testigo que lo usó (si max_uses = 1)
    used_by_witness_id BIGINT REFERENCES witness(id),
    used_at TIMESTAMPTZ
);

CREATE INDEX idx_qr_code ON witness_qr_code(code);
CREATE INDEX idx_qr_active ON witness_qr_code(is_active) WHERE is_active = TRUE;

-- ============================================================
-- 6. CONFIGURACIÓN DE PUSH (VAPID Keys)
-- ============================================================

CREATE TABLE push_config (
    id SERIAL PRIMARY KEY,

    -- VAPID keys para Web Push
    vapid_public_key TEXT NOT NULL,
    vapid_private_key TEXT NOT NULL,
    vapid_subject TEXT NOT NULL,         -- mailto:email o URL

    -- Estado
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 7. FUNCIONES Y TRIGGERS
-- ============================================================

-- Trigger para actualizar updated_at
CREATE TRIGGER tr_witness_updated
    BEFORE UPDATE ON witness
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_assignment_updated
    BEFORE UPDATE ON witness_assignment
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Función para encontrar testigos cercanos a una ubicación
CREATE OR REPLACE FUNCTION find_nearby_witnesses(
    lat DECIMAL,
    lon DECIMAL,
    radius_km DECIMAL DEFAULT 5.0,
    limit_count INT DEFAULT 10
)
RETURNS TABLE (
    witness_id BIGINT,
    full_name TEXT,
    phone TEXT,
    distance_km DECIMAL,
    status witness_status
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        w.id,
        w.full_name,
        w.phone,
        (
            6371 * acos(
                cos(radians(lat)) * cos(radians(w.current_lat)) *
                cos(radians(w.current_lon) - radians(lon)) +
                sin(radians(lat)) * sin(radians(w.current_lat))
            )
        )::DECIMAL AS distance_km,
        w.status
    FROM witness w
    WHERE w.status IN ('ACTIVE', 'ASSIGNED')
      AND w.current_lat IS NOT NULL
      AND w.current_lon IS NOT NULL
      AND w.push_enabled = TRUE
    HAVING (
        6371 * acos(
            cos(radians(lat)) * cos(radians(w.current_lat)) *
            cos(radians(w.current_lon) - radians(lon)) +
            sin(radians(lat)) * sin(radians(w.current_lat))
        )
    ) <= radius_km
    ORDER BY distance_km
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 8. COMENTARIOS
-- ============================================================

COMMENT ON TABLE witness IS 'Testigos electorales registrados via QR + PWA';
COMMENT ON TABLE witness_assignment IS 'Asignaciones de testigos a mesas de votación';
COMMENT ON TABLE witness_notification IS 'Historial de notificaciones push enviadas';
COMMENT ON TABLE witness_qr_code IS 'Códigos QR para registro de testigos';
COMMENT ON TABLE push_config IS 'Configuración VAPID para Web Push notifications';
COMMENT ON COLUMN witness.push_subscription IS 'Subscription object de Web Push API: {endpoint, keys: {p256dh, auth}}';
COMMENT ON COLUMN witness.registration_code IS 'UUID único usado en el QR para registro';

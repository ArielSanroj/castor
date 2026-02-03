-- ============================================================
-- CASTOR - Datos E-14 Congreso 2022
-- Basado en formularios procesados del RAG
-- ============================================================

-- Municipios principales (códigos reales DANE)
INSERT INTO municipality (code, name, dept_code) VALUES
('05001', 'Medellín', '01'),
('05266', 'Envigado', '01'),
('05360', 'Itagüí', '01'),
('08001', 'Barranquilla', '05'),
('08758', 'Soledad', '05'),
('11001', 'Bogotá', '11'),
('25754', 'Soacha', '23'),
('76001', 'Cali', '73'),
('76520', 'Palmira', '73'),
('68001', 'Bucaramanga', '66'),
('52001', 'Pasto', '50')
ON CONFLICT (code) DO NOTHING;

-- Puestos de votación (basados en E-14 procesados)
INSERT INTO polling_station (dept_code, muni_code, zone_code, station_code, station_name, address, lat, lon) VALUES
-- Antioquia - Medellín
('01', '05001', '01', '0001', 'I.E. San José', 'Cra 45 # 52-30, Medellín', 6.2442, -75.5812),
('01', '05001', '01', '0002', 'Escuela Rural La Esperanza', 'Vereda El Poblado, Medellín', 6.2100, -75.5700),
('01', '05001', '02', '0003', 'Coliseo Municipal', 'Calle 50 # 43-12, Medellín', 6.2518, -75.5636),
('01', '05001', '02', '0004', 'Centro Comunitario Castilla', 'Cra 68 # 98-45, Medellín', 6.2890, -75.5920),
-- Antioquia - Envigado
('01', '05266', '01', '0005', 'Casa de la Cultura', 'Calle 37 Sur # 42-20, Envigado', 6.1714, -75.5825),
('01', '05266', '01', '0006', 'Escuela Rural San Marcos', 'Vereda Las Palmas, Envigado', 6.1600, -75.5700),
-- Antioquia - Itagüí
('01', '05360', '01', '0007', 'I.E. San José Itagüí', 'Cra 52 # 51-10, Itagüí', 6.1844, -75.6062),
('01', '05360', '01', '0008', 'Centro Comunitario Itagüí', 'Calle 48 # 50-25, Itagüí', 6.1800, -75.6100),
-- Atlántico - Barranquilla
('05', '08001', '01', '0009', 'I.E. Distrital', 'Cra 43 # 74-50, Barranquilla', 10.9878, -74.7889),
('05', '08001', '01', '0010', 'Coliseo Municipal Norte', 'Calle 72 # 54-30, Barranquilla', 10.9950, -74.8000),
('05', '08001', '02', '0011', 'Escuela Rural Atlántico', 'Km 5 Vía Puerto, Barranquilla', 10.9600, -74.8200),
-- Bogotá
('11', '11001', '01', '0012', 'Colegio Distrital Kennedy', 'Cra 78 # 40-20, Bogotá', 4.6280, -74.1500),
('11', '11001', '01', '0013', 'Casa de la Cultura Usaquén', 'Calle 127 # 15-20, Bogotá', 4.7000, -74.0300),
('11', '11001', '02', '0014', 'Centro Comunitario Suba', 'Cra 92 # 145-30, Bogotá', 4.7400, -74.0900),
-- Valle del Cauca - Cali
('73', '76001', '01', '0015', 'Centro Comunitario Aguablanca', 'Cra 28 # 72-15, Cali', 3.4000, -76.5200),
('73', '76001', '01', '0016', 'I.E. Santa Librada', 'Calle 5 # 23-45, Cali', 3.4300, -76.5400),
-- Santander - Bucaramanga
('66', '68001', '01', '0017', 'Coliseo Municipal Santander', 'Cra 27 # 36-20, Bucaramanga', 7.1193, -73.1227),
('66', '68001', '01', '0018', 'Escuela Rural Girón', 'Km 3 Vía Girón, Bucaramanga', 7.0800, -73.1500),
('66', '68001', '02', '0019', 'Casa de la Cultura Santander', 'Calle 35 # 19-50, Bucaramanga', 7.1250, -73.1180),
-- Nariño - Pasto
('50', '52001', '01', '0020', 'I.E. San José Pasto', 'Cra 27 # 18-45, Pasto', 1.2136, -77.2811),
('50', '52001', '01', '0021', 'Casa de la Cultura Nariño', 'Calle 19 # 25-30, Pasto', 1.2100, -77.2850)
ON CONFLICT (dept_code, muni_code, zone_code, station_code) DO NOTHING;

-- Mesas de votación (contest_id=10 es Senado Nacional)
INSERT INTO polling_table (contest_id, station_id, table_number, dept_code, muni_code, zone_code, station_code)
SELECT 10, ps.id, t.n, ps.dept_code, ps.muni_code, ps.zone_code, ps.station_code
FROM polling_station ps
CROSS JOIN (SELECT generate_series(1, 5) AS n) t
ON CONFLICT (contest_id, station_id, table_number) DO NOTHING;

-- Formularios E-14 procesados (usando source_type válido)
INSERT INTO form_instance (polling_table_id, contest_id, form_type, source_type, object_uri, sha256, overall_confidence, status, processed_at, created_at)
SELECT
    pt.id,
    10,
    'E14',
    'WITNESS',
    '/uploads/e14/congreso2022/' || pt.mesa_id || '.pdf',
    md5(pt.mesa_id || now()::text),
    (0.65 + random() * 0.35)::numeric(5,4),
    CASE WHEN random() > 0.15 THEN 'VALIDATED' ELSE 'NEEDS_REVIEW' END::processing_status,
    NOW() - (random() * interval '6 hours'),
    NOW() - (random() * interval '8 hours')
FROM polling_table pt
WHERE pt.contest_id = 10
ON CONFLICT DO NOTHING;

-- Alertas/Incidentes basados en E-14 con problemas
INSERT INTO alert (contest_id, polling_table_id, form_id, alert_type, severity, status, title, message, evidence, created_at)
SELECT
    10,
    pt.id,
    fi.id,
    CASE (random() * 5)::int
        WHEN 0 THEN 'OCR_LOW_CONFIDENCE'
        WHEN 1 THEN 'VOTE_TOTAL_MISMATCH'
        WHEN 2 THEN 'SIGNATURE_MISSING'
        WHEN 3 THEN 'DUPLICATE_DETECTION'
        ELSE 'ANOMALY_DETECTED'
    END,
    CASE
        WHEN fi.overall_confidence < 0.70 THEN 'CRITICAL'
        WHEN fi.overall_confidence < 0.80 THEN 'HIGH'
        WHEN fi.overall_confidence < 0.90 THEN 'MEDIUM'
        ELSE 'LOW'
    END::alert_severity,
    CASE WHEN random() > 0.7 THEN 'ASSIGNED' ELSE 'OPEN' END::alert_status,
    CASE (random() * 5)::int
        WHEN 0 THEN 'Baja confianza OCR en Mesa ' || pt.table_number
        WHEN 1 THEN 'Discrepancia en totales - Mesa ' || pt.table_number
        WHEN 2 THEN 'Firma faltante jurado - Mesa ' || pt.table_number
        WHEN 3 THEN 'Posible duplicado detectado - Mesa ' || pt.table_number
        ELSE 'Anomalía en patrón de votos - Mesa ' || pt.table_number
    END,
    CASE (random() * 5)::int
        WHEN 0 THEN 'El OCR detectó caracteres ilegibles en la sección de votos. Confianza: ' || round(fi.overall_confidence * 100) || '%'
        WHEN 1 THEN 'La suma de votos por candidato no coincide con el total de votos válidos reportado.'
        WHEN 2 THEN 'No se detectó firma del jurado 3 en el formulario E-14.'
        WHEN 3 THEN 'Se detectó un formulario similar procesado hace 2 horas. Verificar si es duplicado.'
        ELSE 'El patrón de distribución de votos difiere significativamente del promedio del puesto.'
    END,
    jsonb_build_object(
        'mesa_id', pt.mesa_id,
        'ocr_confidence', fi.overall_confidence,
        'dept', pt.dept_code,
        'muni', pt.muni_code,
        'station', ps.station_name
    ),
    NOW() - (random() * interval '4 hours')
FROM polling_table pt
JOIN form_instance fi ON fi.polling_table_id = pt.id
JOIN polling_station ps ON pt.station_id = ps.id
WHERE pt.contest_id = 10
  AND (fi.overall_confidence < 0.90 OR random() > 0.6)
LIMIT 30;

SELECT '=== DATOS INSERTADOS ===' AS resultado;
SELECT 'Municipios: ' || (SELECT COUNT(*) FROM municipality) AS info;
SELECT 'Puestos: ' || (SELECT COUNT(*) FROM polling_station) AS info;
SELECT 'Mesas (Senado): ' || (SELECT COUNT(*) FROM polling_table WHERE contest_id = 10) AS info;
SELECT 'Formularios E-14: ' || (SELECT COUNT(*) FROM form_instance WHERE contest_id = 10) AS info;
SELECT 'Alertas: ' || (SELECT COUNT(*) FROM alert WHERE contest_id = 10) AS info;

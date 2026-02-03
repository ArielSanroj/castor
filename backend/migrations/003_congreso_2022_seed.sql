-- ============================================================
-- CASTOR ELECCIONES - Datos Reales Congreso 2022
-- Elecciones Congreso 13 de Marzo de 2022
-- Senado y Camara de Representantes
-- ============================================================
-- Extraido de formularios E-14 oficiales
-- ============================================================

-- ============================================================
-- 1. ELECCION
-- ============================================================

INSERT INTO election (id, name, election_date, election_type, status) VALUES
(2, 'Elecciones Congreso 2022', '2022-03-13', 'CONGRESSIONAL', 'COMPLETED')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

-- ============================================================
-- 2. CONTIENDAS (CORPORACIONES)
-- ============================================================

INSERT INTO contest (id, election_id, name, contest_type, scope, circunscripcion, total_seats, template_version) VALUES
-- Senado
(10, 2, 'Senado de la Republica - Circunscripcion Nacional', 'SENATE', 'NATIONAL', 'NACIONAL', 100, 'E14_SENADO_2022'),
(11, 2, 'Senado de la Republica - Circunscripcion Especial Indigenas', 'SENATE', 'NATIONAL', 'ESPECIAL_INDIGENA', 2, 'E14_SENADO_2022'),
-- Camara
(20, 2, 'Camara de Representantes - Circunscripcion Territorial', 'HOUSE', 'DEPARTMENTAL', 'TERRITORIAL', 161, 'E14_CAMARA_2022'),
(21, 2, 'Camara de Representantes - Circunscripcion Especial Indigenas', 'HOUSE', 'NATIONAL', 'ESPECIAL_INDIGENA', 1, 'E14_CAMARA_2022'),
(22, 2, 'Camara de Representantes - Circunscripcion Especial Afrodescendientes', 'HOUSE', 'NATIONAL', 'ESPECIAL_AFRO', 2, 'E14_CAMARA_2022')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

-- ============================================================
-- 3. PARTIDOS POLITICOS (AGRUPACIONES POLITICAS)
-- ============================================================

-- Partidos principales - Circunscripcion Nacional/Territorial
INSERT INTO political_group (code, name, short_name, group_type) VALUES
-- Partidos tradicionales
('0001', 'Partido Liberal Colombiano', 'PLC', 'PARTIDO'),
('0002', 'Partido Conservador Colombiano', 'PCC', 'PARTIDO'),
('0003', 'Partido Cambio Radical', 'CR', 'PARTIDO'),
('0004', 'Partido Alianza Verde', 'VERDE', 'PARTIDO'),
('0005', 'Partido Polo Democratico Alternativo', 'POLO', 'PARTIDO'),
('0007', 'Partido Politico MIRA', 'MIRA', 'PARTIDO'),
('0008', 'Partido de la Union por la Gente - Partido de la U', 'U', 'PARTIDO'),
('0011', 'Partido Centro Democratico', 'CD', 'PARTIDO'),
('0013', 'Partido Comunes', 'COMUNES', 'PARTIDO'),
('0019', 'Partido Nuevo Liberalismo', 'NL', 'PARTIDO'),
('0057', 'Partido Colombia Renaciente', 'PCR', 'PARTIDO'),

-- Coaliciones
('0201', 'Coalicion Partidos Cambio Radical - Colombia Justa Libres - MIRA', 'COALICION CR-CJL-MIRA', 'COALICION'),
('0203', 'Coalicion Centro Esperanza', 'CENTRO ESPERANZA', 'COALICION'),
('0257', 'Coalicion Centro Esperanza', 'CENTRO ESPERANZA', 'COALICION'),
('0281', 'Coalicion Partidos Cambio Radical - Colombia Justa Libres - MIRA - de la U', 'COALICION CR-CJL-MIRA-U', 'COALICION'),
('0282', 'Coalicion Centro Esperanza', 'CENTRO ESPERANZA', 'COALICION'),

-- Movimientos
('0290', 'Pacto Historico', 'PH', 'COALICION'),
('0302', 'Movimiento de Salvacion Nacional', 'MSN', 'MOVIMIENTO'),

-- Otros
('1076', 'Liga de Gobernantes Anticorrupcion', 'LIGA', 'MOVIMIENTO'),

-- Partidos Indigenas
('0156', 'Movimiento Alternativo Indigena Social MAIS', 'MAIS', 'MOVIMIENTO'),
('0167', 'Asociacion Nacional de Cabildos y Autoridades Indigenas en Colombia ANICOL', 'ANICOL', 'MOVIMIENTO'),
('0168', 'Resguardo Indigena Alta y Media Guajira', 'RIAMG', 'MOVIMIENTO'),
('0177', 'Partido Indigena Colombiano P.I.C', 'PIC', 'PARTIDO'),
('0182', 'Resguardo Indigena Zenu del Alto San Jorge', 'RIZASJ', 'MOVIMIENTO'),
('0183', 'Cabildo Indigena Aywjawashi', 'AYWJAWASHI', 'MOVIMIENTO'),
('0186', 'Movimiento Autoridades Indigenas de Colombia AICO', 'AICO', 'MOVIMIENTO'),

-- Organizaciones Afrodescendientes (principales)
('0020', 'Alianza Nacional Afrocolombiana', 'ANA', 'MOVIMIENTO'),
('0021', 'Palenque de la Vereda Las Trecientas y del Municipio de Galapa', 'PALENQUE', 'MOVIMIENTO'),
('0022', 'Consejo Comunitario Union Patia Viejo', 'CCUPV', 'MOVIMIENTO'),
('0023', 'Consejo Comunitario Mayor de Certegui', 'CCMC', 'MOVIMIENTO'),
('0025', 'Consejo Comunitario de Comunidades Negras de Campo Hermoso', 'CCCH', 'MOVIMIENTO'),
('0027', 'Consejo Comunitario Bocas del Atrato y Leoncito', 'CCBAL', 'MOVIMIENTO'),
('0028', 'Asociacion Afrodescendientes de Arboletes AFRODESAR', 'AFRODESAR', 'MOVIMIENTO'),
('0029', 'Afromutata', 'AFROMUTATA', 'MOVIMIENTO'),
('0037', 'Consejo Comunitario de la Costa Pacifica CONCOSTA', 'CONCOSTA', 'MOVIMIENTO'),
('0038', 'Consejo Comunitario Veredas Unidas Un Bien Comun', 'CCVUBC', 'MOVIMIENTO'),
('0039', 'Consejo Mayor Condoto Iro', 'CMCI', 'MOVIMIENTO'),
('0040', 'Consejo Comunitario Integral de Lloro', 'CCIL', 'MOVIMIENTO'),
('0041', 'Consejo Comunitario La Voz de Los Negros', 'CCLVN', 'MOVIMIENTO'),
('0042', 'Consejo Comunitario Alto Paraiso', 'CCAP', 'MOVIMIENTO'),
('0043', 'Organizacion Etnica de Comunidades Afros Los Palenkes', 'OECAP', 'MOVIMIENTO'),
('0044', 'Consejo Comunitario Rio Curbarado', 'CCRC', 'MOVIMIENTO'),
('0045', 'Consejo Comunitario Recuerdo de Nuestros Ancestros Rio Mejicano', 'CCRARM', 'MOVIMIENTO'),
('0046', 'Consejo Comunitario de Comunidades Negras de Guayabal', 'CCCNG', 'MOVIMIENTO'),
('0058', 'Consejo Comunitario Manuel Zapata Olivella de San Antero', 'CCMZOSA', 'MOVIMIENTO'),
('0059', 'Consejo Comunitario Piedras Bachichi Correg Santa Cecilia', 'CCPBSC', 'MOVIMIENTO'),
('0060', 'Consejo Comunitario Puerto Giron', 'CCPG', 'MOVIMIENTO'),
('0067', 'C.C La Toma', 'CCLT', 'MOVIMIENTO'),
('0068', 'Consejo Comunitario del Rio Guajui', 'CCRG', 'MOVIMIENTO'),
('0069', 'Fernando Rios Hidalgo', 'FRH', 'INDEPENDIENTE'),
('0070', 'Fundacion para el Desarrollo Social de Comunidades Negras', 'FDSCN', 'MOVIMIENTO'),
('0077', 'Consejo Comunitario de la Comunidad Negra de Villa Gloria', 'CCCNVG', 'MOVIMIENTO'),
('0078', 'Movimiento Alianza Democratica Amplia', 'MADA', 'MOVIMIENTO'),
('0079', 'Consejo Comunitario Bocas de Taparal', 'CCBT', 'MOVIMIENTO'),
('0081', 'Consejo Comunitario de Flamenco Municipio de Maria La Baja', 'CCFMLB', 'MOVIMIENTO'),
('0084', 'ODEPRIVICOR', 'ODEPRIVICOR', 'MOVIMIENTO'),
('0085', 'Fundacion Social Magende Mi', 'FSMM', 'MOVIMIENTO'),
('0087', 'Consejo Comunitario Arcilla Cardon y Tuna', 'CCACT', 'MOVIMIENTO'),
('0089', 'COACNEJA', 'COACNEJA', 'MOVIMIENTO'),
('0091', 'CONMOGUZ', 'CONMOGUZ', 'MOVIMIENTO'),
('0092', 'Consejo Comunitario de Comunidades Negras Socolando', 'CCCNS', 'MOVIMIENTO'),
('0093', 'Comunidad de Negros de Aguas Blancas', 'CNAB', 'MOVIMIENTO'),
('0097', 'Consejo Comunitario de la Comunidad Negra Limones', 'CCCNL', 'MOVIMIENTO'),
('0099', 'Consejo Comunitario Afrozabaletas', 'CCA', 'MOVIMIENTO'),
('0100', 'Corporacion de Educadores del Litoral Pacifico CORELIPA', 'CORELIPA', 'MOVIMIENTO'),
('0101', 'Asoc Afrocol Desplazados Mcpio Guacari Valle del Cauca ADAG', 'ADAG', 'MOVIMIENTO'),
('0102', 'Somos Identidad', 'SI', 'MOVIMIENTO'),
('0103', 'Consejo Comunitario de los Corregimientos de San Antonio y El Castillo Municipio de El Cerrito', 'CCSAEC', 'MOVIMIENTO'),
('0104', 'Consejo Comunitario del Guabal', 'CCG', 'MOVIMIENTO'),
('0112', 'Consejo Comunitario Rescate Las Varas', 'CCRLV', 'MOVIMIENTO'),
('0114', 'Consejo Comunitario de Vuelta Manza', 'CCVM', 'MOVIMIENTO'),
('0116', 'Corporacion Kofi Annan', 'CKA', 'MOVIMIENTO'),
('0157', 'Consejo Comunitario Mayor de Casimiro', 'CCMCAS', 'MOVIMIENTO')
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, short_name = EXCLUDED.short_name;

-- ============================================================
-- 4. OPCIONES DE BOLETA - SENADO NACIONAL
-- ============================================================

-- Limpiar opciones anteriores de esta contienda
DELETE FROM ballot_option WHERE contest_id = 10;

-- Partidos con voto preferente (tienen candidatos numerados)
INSERT INTO ballot_option (contest_id, option_type, political_group_id, ballot_code, ballot_position, candidate_name)
SELECT 10, 'LIST_ONLY', pg.id, pg.code, 1, pg.name || ' (Lista)'
FROM political_group pg
WHERE pg.code IN ('0001', '0002', '0003', '0004', '0005', '0007', '0008', '0011', '0203', '0281');

-- Partidos sin voto preferente (solo voto por lista)
INSERT INTO ballot_option (contest_id, option_type, political_group_id, ballot_code, ballot_position, candidate_name)
SELECT 10, 'LIST_ONLY', pg.id, pg.code, 2, pg.name || ' (Lista Cerrada)'
FROM political_group pg
WHERE pg.code IN ('0013', '0019', '0290', '0302', '1076');

-- Votos especiales Senado
INSERT INTO ballot_option (contest_id, option_type, ballot_code, ballot_position, candidate_name) VALUES
(10, 'BLANK', 'BLANK', 100, 'Voto en Blanco'),
(10, 'NULL', 'NULL', 101, 'Votos Nulos'),
(10, 'UNMARKED', 'UNMARKED', 102, 'Votos No Marcados'),
(10, 'TOTAL', 'TOTAL', 103, 'Total Votos Validos');

-- ============================================================
-- 5. OPCIONES DE BOLETA - SENADO INDIGENA
-- ============================================================

DELETE FROM ballot_option WHERE contest_id = 11;

INSERT INTO ballot_option (contest_id, option_type, political_group_id, ballot_code, ballot_position, candidate_name)
SELECT 11, 'LIST_ONLY', pg.id, pg.code, ROW_NUMBER() OVER (), pg.name
FROM political_group pg
WHERE pg.code IN ('0156', '0167', '0177', '0186');

INSERT INTO ballot_option (contest_id, option_type, ballot_code, ballot_position, candidate_name) VALUES
(11, 'BLANK', 'BLANK', 100, 'Voto en Blanco'),
(11, 'NULL', 'NULL', 101, 'Votos Nulos'),
(11, 'UNMARKED', 'UNMARKED', 102, 'Votos No Marcados'),
(11, 'TOTAL', 'TOTAL', 103, 'Total Votos Validos');

-- ============================================================
-- 6. OPCIONES DE BOLETA - CAMARA TERRITORIAL
-- ============================================================

DELETE FROM ballot_option WHERE contest_id = 20;

-- Partidos principales Camara Territorial
INSERT INTO ballot_option (contest_id, option_type, political_group_id, ballot_code, ballot_position, candidate_name)
SELECT 20, 'LIST_ONLY', pg.id, pg.code, ROW_NUMBER() OVER (), pg.name || ' (Lista)'
FROM political_group pg
WHERE pg.code IN ('0001', '0002', '0003', '0004', '0007', '0008', '0011', '0013', '0019', '0057', '0201', '0203', '0257', '0281', '0282', '0290', '0302', '1076');

INSERT INTO ballot_option (contest_id, option_type, ballot_code, ballot_position, candidate_name) VALUES
(20, 'BLANK', 'BLANK', 100, 'Voto en Blanco'),
(20, 'NULL', 'NULL', 101, 'Votos Nulos'),
(20, 'UNMARKED', 'UNMARKED', 102, 'Votos No Marcados'),
(20, 'TOTAL', 'TOTAL', 103, 'Total Votos Validos');

-- ============================================================
-- 7. OPCIONES DE BOLETA - CAMARA INDIGENA
-- ============================================================

DELETE FROM ballot_option WHERE contest_id = 21;

INSERT INTO ballot_option (contest_id, option_type, political_group_id, ballot_code, ballot_position, candidate_name)
SELECT 21, 'LIST_ONLY', pg.id, pg.code, ROW_NUMBER() OVER (), pg.name
FROM political_group pg
WHERE pg.code IN ('0156', '0167', '0168', '0177', '0182', '0183', '0186');

INSERT INTO ballot_option (contest_id, option_type, ballot_code, ballot_position, candidate_name) VALUES
(21, 'BLANK', 'BLANK', 100, 'Voto en Blanco'),
(21, 'NULL', 'NULL', 101, 'Votos Nulos'),
(21, 'UNMARKED', 'UNMARKED', 102, 'Votos No Marcados'),
(21, 'TOTAL', 'TOTAL', 103, 'Total Votos Validos');

-- ============================================================
-- 8. OPCIONES DE BOLETA - CAMARA AFRODESCENDIENTES
-- ============================================================

DELETE FROM ballot_option WHERE contest_id = 22;

-- Principales organizaciones afro (hay mas de 50, estos son los principales)
INSERT INTO ballot_option (contest_id, option_type, political_group_id, ballot_code, ballot_position, candidate_name)
SELECT 22, 'LIST_ONLY', pg.id, pg.code, ROW_NUMBER() OVER (), pg.name
FROM political_group pg
WHERE pg.code IN (
    '0020', '0021', '0022', '0023', '0025', '0027', '0028', '0029',
    '0037', '0038', '0039', '0040', '0041', '0042', '0043', '0044',
    '0045', '0046', '0058', '0059', '0060', '0067', '0068', '0069',
    '0070', '0077', '0078', '0079', '0081', '0084', '0085', '0087',
    '0089', '0091', '0092', '0093', '0097', '0099', '0100', '0101',
    '0102', '0103', '0104', '0112', '0114', '0116', '0157'
);

INSERT INTO ballot_option (contest_id, option_type, ballot_code, ballot_position, candidate_name) VALUES
(22, 'BLANK', 'BLANK', 100, 'Voto en Blanco'),
(22, 'NULL', 'NULL', 101, 'Votos Nulos'),
(22, 'UNMARKED', 'UNMARKED', 102, 'Votos No Marcados'),
(22, 'TOTAL', 'TOTAL', 103, 'Total Votos Validos');

-- ============================================================
-- 9. DEPARTAMENTOS PRINCIPALES (DIVIPOLA)
-- ============================================================

INSERT INTO department (code, name) VALUES
('01', 'Antioquia'),
('05', 'Atlantico'),
('08', 'Bolivar'),
('11', 'Bogota D.C.'),
('13', 'Boyaca'),
('15', 'Caldas'),
('17', 'Caqueta'),
('18', 'Cauca'),
('19', 'Cesar'),
('20', 'Cordoba'),
('23', 'Cundinamarca'),
('25', 'Choco'),
('27', 'Huila'),
('41', 'La Guajira'),
('44', 'Magdalena'),
('47', 'Meta'),
('50', 'Narino'),
('52', 'Norte de Santander'),
('54', 'Quindio'),
('63', 'Risaralda'),
('66', 'Santander'),
('68', 'Sucre'),
('70', 'Tolima'),
('73', 'Valle del Cauca'),
('76', 'Arauca'),
('81', 'Casanare'),
('85', 'Putumayo'),
('86', 'San Andres'),
('88', 'Amazonas'),
('91', 'Guainia'),
('94', 'Guaviare'),
('95', 'Vaupes'),
('97', 'Vichada'),
('99', 'Exterior')
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name;

-- ============================================================
-- COMENTARIOS
-- ============================================================

COMMENT ON TABLE political_group IS 'Partidos politicos extraidos de E-14 Congreso 2022';

# Diplomado en Arquitectura de Software - Proyecto Final

## **CASTOR ELECCIONES**
### Plataforma de Inteligencia Artificial para Campañas Electorales

---

## Problema

**Castor Elecciones** es una plataforma que permite a equipos de campañas políticas, partidos y observadores electorales colaborar y analizar en tiempo real el sentimiento ciudadano en redes sociales, procesar formularios electorales (E-14) mediante OCR, y generar estrategias automáticas basadas en inteligencia artificial.

Cualquier organización política puede adquirir los servicios de Castor gracias a que cuenta con un módulo de autenticación JWT independiente. Esto permite registrar usuarios de cada campaña mediante integración con sistemas de identidad propios.

El objetivo es que Castor sea usado a nivel nacional en Colombia, con soporte para español e inglés.

---

## Módulos del Sistema

### 1. Módulo de Autenticación (Core Service - Puerto 5001)

#### Registro en la Plataforma
Usuarios autorizados pueden registrarse con correo electrónico y contraseña. El sistema valida credenciales mediante JWT.

#### Inicio de Sesión
- Autenticación mediante JWT con tokens de acceso (1 hora por defecto)
- Refresh tokens para sesiones prolongadas
- Rate limiting: 5 peticiones/segundo en endpoints de auth

#### Cerrar Sesión
El usuario puede invalidar su token de forma segura.

#### Perfil de Usuario
Información gestionada:
- Correo electrónico
- Nombre completo
- Rol (administrador, analista, observador electoral)
- Organización/Campaña asociada

---

### 2. Módulo de Análisis de Campaña (Dashboard Service - Puerto 5003)

#### Análisis de Sentimiento
- Integración con **Twitter API v2** para búsqueda de tweets
- Modelo **BETO** (Transformers) para sentiment analysis en español
- Clasificación por ejes del Plan Nacional de Desarrollo (PND)
- Detección automática de trending topics

**Restricciones operacionales:**
- Límite Free Tier Twitter: 100 posts/mes
- Máximo 3 peticiones diarias a Twitter
- Cache TTL: 24 horas para tweets, 12 horas para análisis OpenAI

#### Generación de Contenido con IA
Usando **GPT-4o** se genera automáticamente:
- Resúmenes ejecutivos
- Planes estratégicos de campaña
- Discursos personalizados
- Datos para visualización (gráficos)

#### Chat Inteligente (RAG)
- Sistema de Retrieval-Augmented Generation
- Embeddings con `text-embedding-3-small` de OpenAI
- Almacenamiento vectorial con **ChromaDB**
- Historial de conversaciones persistente

#### Métricas y Pronósticos
Índices calculados:

| Métrica | Descripción |
|---------|-------------|
| ICCE | Índice Compuesto de Capacidad Electoral (0-100) |
| ISN | Índice Sentimiento Neto (Positivos - Negativos) |
| ICR | Índice Conversación Relativa |
| Momentum | Velocidad de cambio en conversación |
| SVE | Sentimiento Votante Esperado |

**Modelo predictivo:** Holt-Winters para proyecciones a 14 días

---

### 3. Módulo Electoral E-14 (E14 Service - Puerto 5002)

#### Procesamiento OCR de Formularios
- OCR con **Claude 3.5 Sonnet** (Anthropic Vision)
- Soporte para formularios: E-14, E-24, E-26, Boletines
- Extracción de celdas con nivel de confianza
- Procesamiento paralelo de múltiples páginas

**Restricciones de archivos:**
- Máximo 10 MB por archivo
- Máximo 20 páginas por documento
- DPI de procesamiento: 150

#### Validación y Reconciliación
- Validación aritmética automática
- Detección de discrepancias entre fuentes
- Sistema de alertas por severidad: CRITICAL, HIGH, MEDIUM, LOW
- Reconciliación para elegir fuente de verdad por mesa

#### Auditoría
- Log inmutable de todas las acciones
- Trazabilidad completa de cambios
- Historial de validaciones y correcciones

---

### 4. Módulo de Dashboard y Visualización

#### Feed de Análisis
Vista principal donde se muestran:
- Análisis recientes de campaña
- Alertas electorales activas
- Trending topics detectados
- Métricas en tiempo real

#### Dashboard de Equipo de Campaña
- Visualización con **Chart.js**
- Gráficos de sentimiento por tema
- Distribución geográfica de conversación
- Comparativas entre candidatos

#### Registro de Observadores (Witness)
- Formulario para registro de observadores electorales
- Captura de incidentes en tiempo real
- Geolocalización de reportes

---

### 5. Módulo de Notificaciones y Alertas

#### Sistema de Alertas Electorales
Estados: `OPEN`, `ACKNOWLEDGED`, `INVESTIGATING`, `RESOLVED`, `FALSE_POSITIVE`

Tipos de alertas automáticas:
- Discrepancias en conteo de votos
- Formularios que requieren revisión manual
- Anomalías detectadas por validación aritmética

---

### 6. Módulo de Administración

Funcionalidades exclusivas para administradores:
- Gestión de usuarios y roles
- Configuración de campañas/organizaciones
- Reportes de uso de la plataforma
- Gestión de alertas y discrepancias
- Eliminación de datos sensibles

---

## Arquitectura Técnica

### Diagrama de Servicios

```
┌─────────────────────────────────────────────────────────────┐
│                    NGINX (API Gateway)                       │
│                    Puerto 80/443                             │
│         Rate Limiting: 10 req/s general, 5 req/s auth        │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬─────────────┐
        ▼             ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
│   Core    │  │   E-14    │  │ Dashboard │  │  Backend  │
│  Service  │  │  Service  │  │  Service  │  │ Monolítico│
│   :5001   │  │   :5002   │  │   :5003   │  │   :5001   │
└─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
      │              │              │              │
      └──────────────┴──────────────┴──────────────┘
                          │
           ┌──────────────┴──────────────┐
           ▼                             ▼
    ┌─────────────┐               ┌─────────────┐
    │ PostgreSQL  │               │    Redis    │
    │    :5432    │               │    :6379    │
    │  3 DBs:     │               │  3 Slots:   │
    │  - core_db  │               │  - DB 0     │
    │  - e14_db   │               │  - DB 1     │
    │  - dash_db  │               │  - DB 2     │
    └─────────────┘               └─────────────┘
```

### Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| **Backend** | Flask 3.0.0 + Flask-SQLAlchemy |
| **Base de Datos** | PostgreSQL 15 |
| **Cache** | Redis 7.0 |
| **AI/ML** | OpenAI GPT-4o, Anthropic Claude 3.5, BETO (Transformers) |
| **Vector DB** | ChromaDB |
| **Frontend** | HTML5/Jinja2 + Chart.js + JavaScript |
| **Contenedores** | Docker + Docker Compose |
| **API Gateway** | Nginx con SSL/TLS |

### Integraciones Externas

| Servicio | Propósito | Librería |
|----------|-----------|----------|
| Twitter API v2 | Búsqueda de tweets | Tweepy 4.14 |
| OpenAI | Generación de contenido | openai 1.3.0 |
| Anthropic | OCR de formularios | anthropic 0.39 |

### Patrones de Diseño Implementados

1. **Application Factory Pattern** - Inicialización de Flask apps
2. **Repository Pattern** - Acceso a datos (DatabaseService)
3. **Strategy Pattern** - Clasificación de temas PND
4. **Factory Pattern** - Creación de servicios
5. **Circuit Breaker** - Resiliencia en APIs externas
6. **Singleton Pattern** - Servicios compartidos (RAG, DB)

### Esquema de Base de Datos (E-14)

```sql
-- Catálogos
election, contest, party, candidate

-- Geografía (DIVIPOLA Colombia)
department, municipality, polling_station, polling_table

-- Procesamiento
form_instance (E-14, E-24, E-26, BOLETIN)
ocr_field (campos extraídos con confianza)
vote_tally (votos normalizados)

-- Validación
validation_result, validation_rule
discrepancy, alert

-- Auditoría
audit_log (inmutable)
reconciliation (fuente de verdad por mesa)
```

---

## Requisitos No Funcionales

### Escalabilidad
- Arquitectura de microservicios independientes
- Cache distribuido con Redis
- Preparado para escalamiento horizontal con Docker

### Seguridad
- JWT para autenticación
- Rate limiting en API Gateway
- Headers de seguridad: HSTS, X-Frame-Options, CSP
- SSL/TLS (TLSv1.2+)
- Variables de entorno para secretos

### Rendimiento
- Cache con TTL inteligente por tipo de dato
- Procesamiento paralelo de OCR
- Vistas materializadas para War Room electoral

### Disponibilidad
- Health checks cada 30 segundos
- Circuit breaker para APIs externas
- Logging estructurado para debugging

---

## Métricas del Proyecto

| Métrica | Valor |
|---------|-------|
| Líneas de código | 71,805 |
| Archivos Python | 126+ |
| Endpoints API | 50+ |
| Microservicios | 4 |
| Tablas en BD | 30+ |
| Modelos ML/AI | 3 |
| Docker containers | 6 |

---

## Roadmap Futuro

La plataforma está diseñada para permitir:
- Módulo de streaming en vivo de resultados
- Módulo de historias/timeline de campaña
- Integración con más redes sociales (Facebook, Instagram)
- Alertas push en tiempo real
- Aplicación móvil para observadores electorales

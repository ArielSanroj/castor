# CASTOR - Arquitectura de Microservicios

## Visión General

```
                                    ┌─────────────────┐
                                    │   API Gateway   │
                                    │   (nginx/Kong)  │
                                    └────────┬────────┘
                                             │
              ┌──────────────────────────────┼──────────────────────────────┐
              │                              │                              │
              ▼                              ▼                              ▼
    ┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
    │  E-14 Service   │          │  Dashboard IA   │          │  Core Service   │
    │   (Port 5002)   │          │  (Port 5003)    │          │  (Port 5001)    │
    └────────┬────────┘          └────────┬────────┘          └────────┬────────┘
             │                            │                            │
             ▼                            ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
    │  PostgreSQL     │          │  PostgreSQL     │          │  PostgreSQL     │
    │  e14_db         │          │  dashboard_db   │          │  core_db        │
    └─────────────────┘          └─────────────────┘          └─────────────────┘
                                         │
                                         ▼
                                 ┌─────────────────┐
                                 │  Redis Cache    │
                                 │  (Compartido)   │
                                 └─────────────────┘
```

---

## Microservicio 1: E-14 Service

**Dominio**: Procesamiento de formularios E-14 electorales colombianos
**Puerto**: 5002
**Base de datos**: `e14_db`

### Responsabilidades
- OCR de formularios E-14 (Claude Vision API)
- Scraping de Registraduría
- Pipeline de ingestion (download → OCR → validation → review)
- Extracción de celdas y alfabeto electoral
- Sistema HITL (Human-in-the-Loop) para revisión
- Entrenamiento de modelos locales
- Métricas y SLOs

### Estructura de Directorios
```
services/e14-service/
├── app/
│   ├── __init__.py              # Flask factory
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── electoral.py         # /api/e14/*
│   │   ├── ingestion.py         # /api/pipeline/*
│   │   ├── review.py            # /api/review/*
│   │   └── health.py
│   ├── schemas/
│   │   └── e14.py               # Pydantic models v1/v2
│   └── services/
│       ├── e14_ocr_service.py
│       ├── e14_scraper.py
│       ├── e14_ingestion_pipeline.py
│       ├── e14_training_service.py
│       ├── cell_extractor.py
│       ├── qr_parser.py
│       ├── electoral_alphabet.py
│       ├── parallel_ocr.py
│       └── hitl_review.py
├── models/
│   └── electoral.py             # SQLAlchemy models
├── utils/
│   ├── electoral_security.py
│   ├── pdf_validator.py
│   └── metrics.py
├── migrations/
│   ├── 001_electoral_schema.sql
│   └── 002_electoral_schema_v2.sql
├── docs/
│   └── slos/
├── tests/
├── config.py
├── main.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### Endpoints API
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/metrics` | Prometheus metrics |
| POST | `/api/e14/process` | Procesar E-14 con OCR |
| POST | `/api/e14/process-v2` | Payload estructurado v2 |
| POST | `/api/e14/validate` | Validar E-14 extraído |
| GET | `/api/pipeline/status` | Estado del pipeline |
| POST | `/api/pipeline/start` | Iniciar pipeline |
| POST | `/api/queue/table` | Encolar mesa |
| POST | `/api/queue/department` | Encolar departamento |
| GET | `/api/review/pending` | Items pendientes de revisión |
| POST | `/api/review/submit` | Enviar corrección HITL |

### Dependencias Externas
- Anthropic Claude API (Vision OCR)
- Registraduría Nacional (scraping)
- Core Service (autenticación JWT)

### Variables de Entorno
```env
# E-14 Service
E14_SERVICE_PORT=5002
E14_DATABASE_URL=postgresql://user:pass@localhost:5432/e14_db

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Core Service (para auth)
CORE_SERVICE_URL=http://localhost:5001

# Redis
REDIS_URL=redis://localhost:6379/0
```

---

## Microservicio 2: Dashboard IA Electoral

**Dominio**: Estrategia electoral, análisis Twitter, sentiment, forecasting, RAG, chat
**Puerto**: 5003
**Base de datos**: `dashboard_db`

### Responsabilidades
- Análisis de Twitter/X en tiempo real
- Análisis de sentimiento (BETO model)
- RAG (Retrieval Augmented Generation)
- Chat con IA contextual
- Forecasting electoral (ICCE, Momentum)
- Comparación de rivales
- Generación de estrategias y planes de acción
- Dashboard de métricas

### Estructura de Directorios
```
services/dashboard-ia/
├── app/
│   ├── __init__.py              # Flask factory
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── media.py             # /api/media/*
│   │   ├── chat.py              # /api/chat/*
│   │   ├── campaign.py          # /api/campaign/*
│   │   ├── campaign_team.py     # /api/team/*
│   │   ├── forecast.py          # /api/forecast/*
│   │   ├── advisor.py           # /api/advisor/*
│   │   └── health.py
│   ├── schemas/
│   │   ├── media.py
│   │   ├── campaign.py
│   │   ├── campaign_team.py
│   │   ├── forecast.py
│   │   ├── narrative.py
│   │   ├── advisor.py
│   │   ├── rag.py
│   │   └── core.py
│   └── services/
│       ├── analysis_core.py
│       ├── forecast_service.py
│       └── campaign_team_service.py
├── services/
│   ├── twitter_service.py
│   ├── sentiment_service.py
│   ├── model_singleton.py       # BETO singleton
│   ├── rag_service.py
│   ├── openai_service.py
│   ├── llm_service.py
│   ├── trending_service.py
│   ├── campaign_agent.py
│   ├── database_service.py
│   └── llm/
│       ├── base.py
│       ├── openai_provider.py
│       ├── claude_provider.py
│       ├── local_provider.py
│       └── factory.py
├── models/
│   └── database.py              # Analysis, Tweet, Forecast models
├── utils/
│   ├── twitter_rate_tracker.py
│   ├── bot_detector.py
│   └── chart_generator.py
├── data/
│   ├── dashboard.db             # SQLite (dev)
│   └── rag_store.sqlite3        # Vector store
├── tests/
├── config.py
├── main.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### Endpoints API
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/media/analyze` | Análisis de medios |
| GET | `/api/media/history` | Histórico de análisis |
| POST | `/api/chat/rag` | Chat con RAG |
| GET | `/api/chat/rag/stats` | Estadísticas RAG |
| GET | `/api/forecast/icce` | Índice ICCE |
| GET | `/api/forecast/momentum` | Momentum electoral |
| GET | `/api/forecast/dashboard` | Dashboard completo |
| POST | `/api/campaign/analyze` | Análisis de campaña |
| POST | `/api/campaign/rivals/compare` | Comparar rivales |
| GET | `/api/campaign/trending` | Trending topics |
| POST | `/api/advisor/recommendations` | Recomendaciones IA |

### Dependencias Externas
- Twitter API v2 (Tweepy)
- OpenAI API (GPT-4o, embeddings)
- Anthropic Claude API (fallback)
- Ollama (modelo local opcional)
- Core Service (autenticación JWT)

### Variables de Entorno
```env
# Dashboard IA Service
DASHBOARD_SERVICE_PORT=5003
DASHBOARD_DATABASE_URL=postgresql://user:pass@localhost:5432/dashboard_db

# Twitter
TWITTER_BEARER_TOKEN=...
TWITTER_DAILY_LIMIT=500
TWITTER_MONTHLY_LIMIT=15000

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Anthropic (fallback)
ANTHROPIC_API_KEY=sk-ant-...

# Local LLM (opcional)
OLLAMA_BASE_URL=http://localhost:11434

# Core Service (para auth)
CORE_SERVICE_URL=http://localhost:5001

# Redis
REDIS_URL=redis://localhost:6379/1

# Cache TTLs
TWITTER_CACHE_TTL=3600
SENTIMENT_CACHE_TTL=86400
TRENDING_CACHE_TTL=1800
```

---

## Microservicio 3: Core Service

**Dominio**: Autenticación, usuarios, infraestructura compartida
**Puerto**: 5001
**Base de datos**: `core_db`

### Responsabilidades
- Autenticación y autorización (JWT)
- Gestión de usuarios
- API Gateway interno
- Rate limiting global
- Health checks
- Leads y demo requests
- Configuración compartida

### Estructura de Directorios
```
services/core-service/
├── app/
│   ├── __init__.py              # Flask factory
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py              # /api/auth/*
│   │   ├── health.py            # /api/health
│   │   ├── leads.py             # /api/leads/*
│   │   └── proxy.py             # Proxy a otros servicios
│   └── schemas/
│       └── auth.py
├── models/
│   └── database.py              # User, Lead models
├── utils/
│   ├── cache.py
│   ├── rate_limiter.py
│   ├── circuit_breaker.py
│   ├── validators.py
│   ├── formatters.py
│   └── response_helpers.py
├── tests/
├── config.py
├── main.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### Endpoints API
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/auth/register` | Registro de usuario |
| POST | `/api/auth/login` | Login (retorna JWT) |
| GET | `/api/auth/me` | Usuario actual |
| POST | `/api/auth/refresh` | Refrescar token |
| POST | `/api/leads/demo-request` | Solicitud de demo |
| GET | `/api/leads` | Listar leads (admin) |

### Variables de Entorno
```env
# Core Service
CORE_SERVICE_PORT=5001
CORE_DATABASE_URL=postgresql://user:pass@localhost:5432/core_db

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=604800

# Redis
REDIS_URL=redis://localhost:6379/2

# Rate Limiting
RATE_LIMIT_DEFAULT=100/hour
RATE_LIMIT_AUTH=20/minute
```

---

## Comunicación entre Servicios

### Autenticación (JWT Flow)
```
Client → Core Service (login) → JWT Token
Client → Dashboard IA (con JWT) → Core Service (validar) → Respuesta
Client → E-14 Service (con JWT) → Core Service (validar) → Respuesta
```

### Patrón de Comunicación
- **Síncrono**: HTTP REST para operaciones inmediatas
- **Asíncrono**: Redis Pub/Sub para eventos (opcional)

### Service Discovery
```python
# config.py (cada servicio)
SERVICES = {
    "core": os.getenv("CORE_SERVICE_URL", "http://localhost:5001"),
    "e14": os.getenv("E14_SERVICE_URL", "http://localhost:5002"),
    "dashboard": os.getenv("DASHBOARD_SERVICE_URL", "http://localhost:5003"),
}
```

---

## Docker Compose (Desarrollo)

```yaml
# docker-compose.yml (raíz del proyecto)
version: '3.8'

services:
  # Bases de datos
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: castor
      POSTGRES_PASSWORD: castor_dev
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # Core Service
  core-service:
    build: ./services/core-service
    ports:
      - "5001:5001"
    environment:
      - CORE_DATABASE_URL=postgresql://castor:castor_dev@postgres:5432/core_db
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - postgres
      - redis

  # E-14 Service
  e14-service:
    build: ./services/e14-service
    ports:
      - "5002:5002"
    environment:
      - E14_DATABASE_URL=postgresql://castor:castor_dev@postgres:5432/e14_db
      - REDIS_URL=redis://redis:6379/1
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - CORE_SERVICE_URL=http://core-service:5001
    depends_on:
      - postgres
      - redis
      - core-service

  # Dashboard IA Service
  dashboard-service:
    build: ./services/dashboard-ia
    ports:
      - "5003:5003"
    environment:
      - DASHBOARD_DATABASE_URL=postgresql://castor:castor_dev@postgres:5432/dashboard_db
      - REDIS_URL=redis://redis:6379/2
      - TWITTER_BEARER_TOKEN=${TWITTER_BEARER_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - CORE_SERVICE_URL=http://core-service:5001
    depends_on:
      - postgres
      - redis
      - core-service

  # API Gateway (opcional)
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - core-service
      - e14-service
      - dashboard-service

volumes:
  postgres_data:
```

---

## Plan de Migración

### Fase 1: Preparación
1. [ ] Crear estructura de directorios para microservicios
2. [ ] Configurar PostgreSQL con 3 bases de datos
3. [ ] Configurar Redis compartido
4. [ ] Crear scripts de migración de SQLite a PostgreSQL

### Fase 2: Core Service
1. [ ] Extraer auth, users, leads
2. [ ] Implementar JWT validation endpoint
3. [ ] Configurar rate limiting global
4. [ ] Tests y deploy

### Fase 3: E-14 Service
1. [ ] Mover todos los archivos E-14
2. [ ] Actualizar imports y dependencias
3. [ ] Implementar cliente HTTP para Core Service
4. [ ] Migrar datos de SQLite a PostgreSQL
5. [ ] Tests y deploy

### Fase 4: Dashboard IA Service
1. [ ] Mover servicios de Twitter, sentiment, RAG
2. [ ] Mover rutas de media, chat, campaign, forecast
3. [ ] Actualizar integraciones
4. [ ] Migrar datos y vector store
5. [ ] Tests y deploy

### Fase 5: Integración
1. [ ] Configurar API Gateway (nginx/Kong)
2. [ ] Implementar service discovery
3. [ ] Configurar monitoreo (Prometheus + Grafana)
4. [ ] Load testing
5. [ ] Documentación final

---

## Archivos a Mover por Servicio

### E-14 Service (desde backend/)
```
services/e14_ocr_service.py
services/e14_scraper.py
services/e14_ingestion_pipeline.py
services/e14_training_service.py
services/cell_extractor.py
services/qr_parser.py
services/electoral_alphabet.py
services/parallel_ocr.py
services/hitl_review.py
app/routes/electoral.py
app/routes/ingestion.py
app/routes/review.py
app/schemas/e14.py
models/electoral.py
utils/electoral_security.py
utils/pdf_validator.py
utils/metrics.py
migrations/
docs/slos/
scripts/test_e14_ocr.py
scripts/test_ocr_v2.py
scripts/test_integration.py
scripts/test_security.py
scripts/generate_training_data.py
training_data/
```

### Dashboard IA Service (desde backend/)
```
services/twitter_service.py
services/sentiment_service.py
services/model_singleton.py
services/rag_service.py
services/openai_service.py
services/llm_service.py
services/llm/
services/trending_service.py
services/campaign_agent.py
services/database_service.py
app/routes/media.py
app/routes/chat.py
app/routes/campaign.py
app/routes/campaign_team.py
app/routes/forecast.py
app/routes/advisor.py
app/services/analysis_core.py
app/services/forecast_service.py
app/services/campaign_team_service.py
app/schemas/media.py
app/schemas/campaign.py
app/schemas/campaign_team.py
app/schemas/forecast.py
app/schemas/narrative.py
app/schemas/advisor.py
app/schemas/rag.py
app/schemas/core.py
utils/twitter_rate_tracker.py
utils/bot_detector.py
utils/chart_generator.py
```

### Core Service (desde backend/)
```
app/routes/auth.py
app/routes/health.py
app/routes/leads.py
models/database.py (User, Lead)
utils/cache.py
utils/rate_limiter.py
utils/circuit_breaker.py
utils/validators.py
utils/formatters.py
utils/response_helpers.py
config.py (adaptado)
```

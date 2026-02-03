# CASTOR Elecciones - Plataforma de Inteligencia Electoral

## Descripcion
Plataforma integral de inteligencia artificial para analisis electoral en tiempo real. Procesa tweets sobre los 10 ejes del Plan Nacional de Desarrollo (PND 2022-2026) con analisis de sentimiento BETO (99% precision), genera resumenes ejecutivos, analisis tematicos, planes estrategicos y discursos automaticos. Incluye OCR de documentos electorales E14 con Claude Vision.

## Stack Tecnologico

| Componente | Tecnologia |
|------------|------------|
| Backend | Python 3.10+ / Flask 3.0 |
| ML/NLP | BETO (Transformers) + OpenAI GPT-4o + Claude |
| Database | PostgreSQL 15 + SQLite + Redis 7 |
| Twitter | Tweepy (API v2) |
| OCR | Tesseract + Claude Vision |
| Frontend | React + Next.js 14 (pendiente) |
| Auth | JWT (SQLAlchemy) |
| Containers | Docker + Docker Compose |
| Gateway | Nginx |
| Messaging | Twilio (WhatsApp) |

---

## Arquitectura de Microservicios

```mermaid
graph TB
    subgraph "API Gateway"
        NGINX[Nginx :80/:443]
    end

    subgraph "Microservices"
        CORE[core-service :5001]
        E14[e14-service :5002]
        DASHBOARD[dashboard-service :5003]
    end

    subgraph "Infrastructure"
        POSTGRES[(PostgreSQL :5432)]
        REDIS[(Redis :6379)]
    end

    subgraph "External APIs"
        TWITTER[Twitter API]
        OPENAI[OpenAI API]
        ANTHROPIC[Anthropic API]
    end

    NGINX --> CORE
    NGINX --> E14
    NGINX --> DASHBOARD

    CORE --> POSTGRES
    E14 --> POSTGRES
    DASHBOARD --> POSTGRES

    CORE --> REDIS
    E14 --> REDIS
    DASHBOARD --> REDIS

    DASHBOARD --> TWITTER
    DASHBOARD --> OPENAI
    E14 --> ANTHROPIC
```

```mermaid
sequenceDiagram
    participant U as Usuario
    participant GW as Nginx
    participant DASH as Dashboard
    participant TW as Twitter
    participant BETO as BETO Model
    participant GPT as GPT-4o
    participant DB as PostgreSQL

    U->>GW: POST /api/analyze
    GW->>DASH: Forward
    DASH->>TW: Search tweets
    TW-->>DASH: Tweets
    DASH->>BETO: Sentiment analysis
    BETO-->>DASH: Scores
    DASH->>GPT: Generate report
    GPT-->>DASH: Summary + Speech
    DASH->>DB: Save analysis
    DASH-->>U: Results
```

---

## Estructura del Proyecto

```
castor/
├── backend/                      # Backend principal (monolito)
│   ├── app/
│   │   ├── routes/              # API endpoints (Flask blueprints)
│   │   ├── schemas/             # Pydantic models (validation)
│   │   ├── services/            # Business logic (app-level)
│   │   └── interfaces/          # Abstractions
│   ├── services/                # Core services (integrations)
│   │   ├── twitter_service.py   # Twitter integration
│   │   ├── sentiment_service.py # BETO analysis
│   │   ├── openai_service.py    # GPT-4 generation
│   │   ├── e14_ocr_service.py   # OCR processing
│   │   ├── rag_service.py       # RAG pipeline
│   │   └── llm_service.py       # LLM abstraction
│   ├── models/                  # SQLAlchemy models
│   ├── repositories/            # Data access layer
│   ├── utils/                   # Helpers
│   └── tests/                   # Unit tests
│
├── services/                    # Microservices (Docker)
│   ├── core-service/           # Auth, users, campaigns (:5001)
│   ├── e14-service/            # Electoral documents OCR (:5002)
│   └── dashboard-ia/           # Analytics + AI (:5003)
│
├── diagramas/                   # Architecture diagrams
├── docs/                        # Documentation
├── static/                      # Static files (CSS, JS, images)
│   ├── data/                   # GeoJSON, datasets
│   └── js/                     # Frontend JavaScript
├── templates/                   # Jinja2 HTML templates
├── scripts/                     # Utility scripts
└── docker-compose.yml           # Container orchestration
```

> **Nota**: `backend/services/` contiene integraciones core (Twitter, OpenAI, etc).
> `backend/app/services/` contiene logica de negocio especifica de la app.

---

## Microservicios

| Servicio | Puerto | DB | Proposito |
|----------|--------|-----|-----------|
| `core-service` | 5001 | core_db | Auth, usuarios, campanas |
| `e14-service` | 5002 | e14_db | OCR documentos E14 |
| `dashboard-service` | 5003 | dashboard_db | Analytics, Twitter, AI |

---

## Archivos Clave

| Archivo | Proposito |
|---------|-----------|
| `backend/main.py` | Entry point Flask |
| `backend/config.py` | Configuracion centralizada |
| `backend/services/twitter_service.py` | Busqueda de tweets |
| `backend/services/sentiment_service.py` | Analisis BETO |
| `backend/services/openai_service.py` | Generacion GPT-4 |
| `backend/services/e14_ocr_service.py` | OCR formularios E14 |
| `backend/services/llm_service.py` | Abstraccion LLM |
| `backend/services/rag_service.py` | RAG pipeline |
| `docker-compose.yml` | Orquestacion servicios |

---

## API Routes (Backend)

| Route File | Proposito |
|------------|-----------|
| `backend/app/routes/auth.py` | Autenticacion JWT |
| `backend/app/routes/analysis.py` | Analisis electoral |
| `backend/app/routes/campaign.py` | Gestion de campanas |
| `backend/app/routes/campaign_team.py` | Equipos de campana |
| `backend/app/routes/chat.py` | Chat IA |
| `backend/app/routes/electoral.py` | Datos electorales |
| `backend/app/routes/e14_data.py` | Datos E14 procesados |
| `backend/app/routes/forecast.py` | Predicciones electorales |
| `backend/app/routes/geography.py` | Mapa choropleth, datos geoespaciales |
| `backend/app/routes/health.py` | Health checks |
| `backend/app/routes/incidents.py` | Cola de incidentes War Room |
| `backend/app/routes/ingestion.py` | Ingestion de datos |
| `backend/app/routes/leads.py` | Gestion de leads |
| `backend/app/routes/media.py` | Manejo de archivos |
| `backend/app/routes/review.py` | HITL review system |
| `backend/app/routes/scraper.py` | Control scraper E14, batch OCR |
| `backend/app/routes/web.py` | Rutas web/templates |
| `backend/app/routes/witness.py` | Testigos electorales, QR, push notifications |
| `backend/app/routes/advisor.py` | Asesor IA |

---

## Comandos Principales

### Desarrollo Local
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py                    # Puerto 5001

# Con Docker
docker-compose up -d              # Todos los servicios
docker-compose up postgres redis  # Solo infra
docker-compose logs -f dashboard-service
```

### Testing
```bash
cd backend
pytest tests/                     # Todos los tests
pytest --cov=. tests/             # Con cobertura
```

### OCR E14
```bash
python backend/services/e14_ocr_service.py --input documento.pdf
```

### Base de Datos
```bash
cd backend
flask db migrate -m "descripcion"
flask db upgrade
```

---

## API Endpoints

### Analisis Electoral
```
POST /api/analyze
{
  "location": "Bogota",
  "theme": "Seguridad",
  "candidate_name": "Juan Perez",
  "politician": "@juanperez",
  "max_tweets": 100
}
```

### Chat IA
```
POST /api/chat
{
  "message": "Como mejorar mi campana?",
  "context": {...}
}
```

### E14 OCR
```
POST /api/e14/process
Content-Type: multipart/form-data
file: <documento.pdf>
```

### Testigos Electorales
```
POST /api/witness/register     # Registrar testigo via QR
GET  /api/witness/list         # Listar testigos
POST /api/witness/qr/generate  # Generar codigo QR
POST /api/witness/push/subscribe  # Suscribir push notifications
GET  /api/witness/nearby       # Testigos cercanos
```

### Incidentes War Room
```
GET  /api/incidents            # Listar incidentes
POST /api/incidents            # Crear incidente
PUT  /api/incidents/{id}/assign    # Asignar incidente
PUT  /api/incidents/{id}/resolve   # Resolver incidente
PUT  /api/incidents/{id}/escalate  # Escalar incidente
GET  /api/incidents/stats      # Estadisticas
GET  /api/incidents/kpis       # KPIs War Room
```

### Geografia
```
GET /api/geography/geojson     # GeoJSON Colombia
GET /api/geography/departments # Metricas por departamento
GET /api/geography/stats       # Estadisticas geograficas
```

### Scraper E14
```
GET  /api/scraper/health       # Health check scraper
POST /api/scraper/batch/start  # Iniciar batch OCR
GET  /api/scraper/batch/status # Estado del batch
GET  /api/scraper/metrics      # Metricas OCR
```

### Health Check
```
GET /api/health
```

---

## Modulos Funcionales

| Modulo | Descripcion | Routes |
|--------|-------------|--------|
| **War Room** | Centro de operaciones: incidentes, KPIs, mapa en vivo | `incidents.py`, `geography.py` |
| **Testigos** | Gestion testigos electorales, QR, push notifications | `witness.py` |
| **E14 OCR** | Procesamiento actas E14 con Claude Vision + Tesseract | `e14_data.py`, `scraper.py` |
| **Analytics** | Analisis Twitter, sentimiento BETO, reportes IA | `analysis.py`, `chat.py` |
| **Campanas** | Gestion campanas y equipos | `campaign.py`, `campaign_team.py` |

---

## Temas PND Soportados

1. Seguridad
2. Infraestructura
3. Gobernanza y Transparencia
4. Educacion
5. Salud
6. Igualdad y Equidad
7. Paz y Reinsercion
8. Economia y Empleo
9. Medio Ambiente
10. Alimentacion

---

## Configuracion (.env)

```env
# Flask
FLASK_ENV=development
SECRET_KEY=xxx

# Database
DATABASE_URL=postgresql://castor:xxx@localhost:5432/core_db
# O SQLite para desarrollo local:
# DATABASE_URL=sqlite:///data/castor.db

# Twitter
TWITTER_BEARER_TOKEN=xxx
TWITTER_DAILY_TWEET_LIMIT=500
TWITTER_MONTHLY_LIMIT=15000

# AI - OpenAI
OPENAI_API_KEY=xxx
OPENAI_MODEL=gpt-4o

# AI - Anthropic (E-14 OCR)
ANTHROPIC_API_KEY=xxx
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_VISION_MODEL=claude-sonnet-4-20250514

# E-14 OCR Configuration
E14_OCR_MAX_PAGES=20
E14_OCR_TIMEOUT=120
E14_OCR_DPI=150
E14_COST_PER_PROCESS=0.10
E14_HOURLY_COST_LIMIT=2.00
E14_DAILY_COST_LIMIT=5.00
E14_MAX_FILE_SIZE_MB=10

# E-14 Scraper
SCRAPER_NUM_WORKERS=10
SCRAPER_REQUESTS_PER_MINUTE=30
SCRAPER_MAX_RETRIES=3
SCRAPER_REQUEST_TIMEOUT=30
CAPTCHA_2_API_KEY=xxx
CAPTCHA_SOLVER_ENABLED=true

# Server
HOST=0.0.0.0
PORT=5001
DEBUG=false
```

---

## AI Thinking Rules

### Antes de escribir codigo SIEMPRE preguntate:

```yaml
reflexion_obligatoria:
  - "Este codigo se parece a otra parte del proyecto?"
  - "Puedo extraer esto en una funcion reutilizable?"
  - "Estoy creando una dependencia circular?"
  - "Este archivo va a superar 300 lineas?"
  - "Esta funcion va a superar 30 lineas?"
  - "El nombre explica claramente que hace?"
  - "Estoy hardcodeando algo que deberia ser config?"
```

### Principios Core

```yaml
codigo:
  max_file_lines: 300
  max_function_lines: 30
  max_class_methods: 10
  max_parameters: 5

naming:
  functions: snake_case
  classes: PascalCase
  constants: UPPER_SNAKE_CASE
  private: _prefixed

principios:
  - "Cada funcion debe hacer UNA cosa"
  - "Preferir composicion sobre herencia"
  - "Fail fast - validar inputs temprano"
  - "Usar type hints en todas las funciones"
  - "Validar con Pydantic en boundaries"
  - "DRY - 3 repeticiones = refactor"
```

---

## CTO Rules - Cuando codigo crece 2x

### Checklist Obligatorio

```markdown
## Documentacion
- [ ] README.md actualizado
- [ ] API_DOCUMENTATION.md al dia
- [ ] Diagramas actualizados

## Testing
- [ ] Tests para nuevos endpoints
- [ ] Cobertura > 70%

## Arquitectura
- [ ] Sin dependencias circulares
- [ ] Archivos < 300 lineas
- [ ] Funciones < 30 lineas

## Seguridad
- [ ] Sin secrets hardcodeados
- [ ] Rate limiting activo
- [ ] JWT en endpoints protegidos
```

---

## Patrones del Proyecto

### Service Pattern
```python
from typing import List
from models.schemas import TweetData, SentimentResult

class SentimentService:
    def __init__(self, model_path: str):
        self.model = self._load_model(model_path)

    def analyze(self, tweets: List[TweetData]) -> SentimentResult:
        """Analyze sentiment of tweets using BETO."""
        scores = [self._predict(t.text) for t in tweets]
        return SentimentResult(scores=scores)
```

### LLM Abstraction
```python
from services.llm_service import LLMService

llm = LLMService(provider="anthropic")  # or "openai"
response = await llm.generate(
    prompt="Genera discurso sobre seguridad",
    max_tokens=1000
)
```

---

## Anti-Patterns a Evitar

```python
# MAL - Sin type hints
def process(data):
    return data["value"]

# MAL - Secrets hardcodeados
api_key = "sk-xxx"

# MAL - Sin validacion
@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.json  # Sin validar!

# BIEN - Con todo
from pydantic import BaseModel

class AnalysisRequest(BaseModel):
    location: str
    theme: str

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = AnalysisRequest(**request.json)
    return service.analyze(data)
```

---

## Scripts de Calidad

```bash
# Revision de codigo
bash scripts/ai-review.sh

# Verificacion CTO
bash scripts/cto-check.sh

# Linting
cd backend && flake8 . && mypy .

# Formateo
black . && isort .
```

---

## Quick Start

```bash
# 1. Configurar
cd castor
cp backend/.env.example backend/.env

# 2. Docker (recomendado)
docker-compose up -d
curl http://localhost:5001/api/health

# 3. O local
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

**Version**: 2.1.0 - CASTOR Elecciones
**Ultima actualizacion**: 2026-02-03

# Diagrama de Despliegue - CASTOR ELECCIONES

## Vista General de Infraestructura

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    INTERNET                                          │
└─────────────────────────────────────────┬───────────────────────────────────────────┘
                                          │
                                          │ HTTPS (443)
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              <<cloud>>                                               │
│                         SERVIDOR DE PRODUCCIÓN                                       │
│                     (AWS EC2 / DigitalOcean / VPS)                                  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                        <<docker-compose>>                                      │  │
│  │                      DOCKER ENVIRONMENT                                        │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                    <<container>>                                         │  │  │
│  │  │                  NGINX (API Gateway)                                     │  │  │
│  │  │                                                                          │  │  │
│  │  │  Image: nginx:alpine                                                     │  │  │
│  │  │  Ports: 80:80, 443:443                                                   │  │  │
│  │  │                                                                          │  │  │
│  │  │  Artifacts:                                                              │  │  │
│  │  │  ├── nginx.conf (378 líneas)                                             │  │  │
│  │  │  ├── ssl/cert.pem                                                        │  │  │
│  │  │  └── ssl/key.pem                                                         │  │  │
│  │  │                                                                          │  │  │
│  │  │  Config:                                                                 │  │  │
│  │  │  ├── Rate Limit: 10 req/s (general), 5 req/s (auth)                      │  │  │
│  │  │  ├── SSL/TLS: TLSv1.2, TLSv1.3                                           │  │  │
│  │  │  ├── HSTS: max-age=31536000                                              │  │  │
│  │  │  └── Gzip: enabled                                                       │  │  │
│  │  └──────────────────────────────┬──────────────────────────────────────────┘  │  │
│  │                                 │                                              │  │
│  │            ┌────────────────────┼────────────────────┐                         │  │
│  │            │                    │                    │                         │  │
│  │            ▼                    ▼                    ▼                         │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │  │
│  │  │  <<container>>  │  │  <<container>>  │  │  <<container>>  │                │  │
│  │  │  CORE SERVICE   │  │  E-14 SERVICE   │  │DASHBOARD SERVICE│                │  │
│  │  │                 │  │                 │  │                 │                │  │
│  │  │ Image: python:  │  │ Image: python:  │  │ Image: python:  │                │  │
│  │  │   3.11-slim     │  │   3.11-slim     │  │   3.11-slim     │                │  │
│  │  │ Port: 5001      │  │ Port: 5002      │  │ Port: 5003      │                │  │
│  │  │                 │  │                 │  │                 │                │  │
│  │  │ Artifacts:      │  │ Artifacts:      │  │ Artifacts:      │                │  │
│  │  │ ├── main.py     │  │ ├── main.py     │  │ ├── main.py     │                │  │
│  │  │ ├── app/        │  │ ├── app/        │  │ ├── app/        │                │  │
│  │  │ ├── services/   │  │ ├── services/   │  │ ├── services/   │                │  │
│  │  │ └── config.py   │  │ └── config.py   │  │ └── config.py   │                │  │
│  │  │                 │  │                 │  │                 │                │  │
│  │  │ Health: /health │  │ Health: /health │  │ Health: /health │                │  │
│  │  │ Interval: 30s   │  │ Interval: 30s   │  │ Interval: 30s   │                │  │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘                │  │
│  │           │                    │                    │                         │  │
│  │           └────────────────────┼────────────────────┘                         │  │
│  │                                │                                              │  │
│  │            ┌───────────────────┴───────────────────┐                          │  │
│  │            │                                       │                          │  │
│  │            ▼                                       ▼                          │  │
│  │  ┌─────────────────────────┐          ┌─────────────────────────┐            │  │
│  │  │     <<container>>       │          │     <<container>>       │            │  │
│  │  │      POSTGRESQL         │          │        REDIS            │            │  │
│  │  │                         │          │                         │            │  │
│  │  │ Image: postgres:15-     │          │ Image: redis:7-alpine   │            │  │
│  │  │        alpine           │          │                         │            │  │
│  │  │ Port: 5432              │          │ Port: 6379              │            │  │
│  │  │                         │          │                         │            │  │
│  │  │ Databases:              │          │ Databases:              │            │  │
│  │  │ ├── core_db             │          │ ├── DB 0 (Core)         │            │  │
│  │  │ ├── e14_db              │          │ ├── DB 1 (E-14)         │            │  │
│  │  │ └── dashboard_db        │          │ └── DB 2 (Dashboard)    │            │  │
│  │  │                         │          │                         │            │  │
│  │  │ Volume:                 │          │ Config:                 │            │  │
│  │  │ └── pgdata:/var/lib/    │          │ └── maxmemory: 256mb    │            │  │
│  │  │     postgresql/data     │          │                         │            │  │
│  │  └─────────────────────────┘          └─────────────────────────┘            │  │
│  │                                                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                         VOLÚMENES PERSISTENTES                                 │  │
│  │                                                                                │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │  │
│  │  │  pgdata         │  │  chromadb_data  │  │  logs           │                │  │
│  │  │  PostgreSQL     │  │  Vector Store   │  │  Application    │                │  │
│  │  │  persistent     │  │  embeddings     │  │  logs           │                │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘                │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Diagrama de Red y Comunicación

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              NETWORK TOPOLOGY                                         │
└──────────────────────────────────────────────────────────────────────────────────────┘

                                    INTERNET
                                       │
                                       │ HTTPS/443
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              DOCKER NETWORK: castor_network                           │
│                                    (bridge)                                           │
│                                                                                       │
│     ┌─────────────────────────────────────────────────────────────────────────┐      │
│     │                           FRONTEND TIER                                  │      │
│     │                                                                          │      │
│     │                      ┌──────────────────┐                                │      │
│     │                      │      NGINX       │                                │      │
│     │                      │   172.20.0.2     │                                │      │
│     │                      │   :80, :443      │                                │      │
│     │                      └────────┬─────────┘                                │      │
│     │                               │                                          │      │
│     └───────────────────────────────┼──────────────────────────────────────────┘      │
│                                     │                                                 │
│     ┌───────────────────────────────┼──────────────────────────────────────────┐      │
│     │                           APPLICATION TIER                                │      │
│     │                               │                                           │      │
│     │         ┌─────────────────────┼─────────────────────┐                    │      │
│     │         │                     │                     │                    │      │
│     │         ▼                     ▼                     ▼                    │      │
│     │  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐              │      │
│     │  │    CORE     │      │    E-14     │      │  DASHBOARD  │              │      │
│     │  │ 172.20.0.3  │      │ 172.20.0.4  │      │ 172.20.0.5  │              │      │
│     │  │   :5001     │      │   :5002     │      │   :5003     │              │      │
│     │  └──────┬──────┘      └──────┬──────┘      └──────┬──────┘              │      │
│     │         │                    │                    │                     │      │
│     └─────────┼────────────────────┼────────────────────┼─────────────────────┘      │
│               │                    │                    │                            │
│     ┌─────────┼────────────────────┼────────────────────┼─────────────────────┐      │
│     │         │              DATA TIER                  │                      │      │
│     │         │                    │                    │                      │      │
│     │         └────────────────────┼────────────────────┘                      │      │
│     │                              │                                           │      │
│     │              ┌───────────────┴───────────────┐                          │      │
│     │              ▼                               ▼                          │      │
│     │       ┌─────────────┐               ┌─────────────┐                     │      │
│     │       │ POSTGRESQL  │               │    REDIS    │                     │      │
│     │       │ 172.20.0.6  │               │ 172.20.0.7  │                     │      │
│     │       │   :5432     │               │   :6379     │                     │      │
│     │       └─────────────┘               └─────────────┘                     │      │
│     │                                                                          │      │
│     └──────────────────────────────────────────────────────────────────────────┘      │
│                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘

                              EXTERNAL SERVICES
        ┌─────────────────────────────────────────────────────────────┐
        │                                                             │
        ▼                         ▼                         ▼         │
┌───────────────┐        ┌───────────────┐        ┌───────────────┐  │
│  Twitter API  │        │  OpenAI API   │        │ Anthropic API │  │
│  api.twitter  │        │ api.openai    │        │api.anthropic  │  │
│  .com:443     │        │ .com:443      │        │.com:443       │  │
└───────────────┘        └───────────────┘        └───────────────┘  │
        │                         │                         │         │
        └─────────────────────────┴─────────────────────────┴─────────┘
                                  │
                          HTTPS (outbound)
                                  │
                      ┌───────────┴───────────┐
                      │   Dashboard Service   │
                      │      (5003)           │
                      └───────────────────────┘
```

---

## Docker Compose - Configuración de Despliegue

```yaml
# docker-compose.yml
version: '3.8'

networks:
  castor_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  pgdata:
  chromadb_data:
  logs:

services:
  # ═══════════════════════════════════════════════════════════════
  # INFRASTRUCTURE TIER
  # ═══════════════════════════════════════════════════════════════

  nginx:
    image: nginx:alpine
    container_name: castor-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - core-service
      - e14-service
      - dashboard-service
    networks:
      castor_network:
        ipv4_address: 172.20.0.2
    restart: unless-stopped

  # ═══════════════════════════════════════════════════════════════
  # DATA TIER
  # ═══════════════════════════════════════════════════════════════

  postgres:
    image: postgres:15-alpine
    container_name: castor-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-castor}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_MULTIPLE_DATABASES: core_db,e14_db,dashboard_db
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init-db:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    networks:
      castor_network:
        ipv4_address: 172.20.0.6
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U castor"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: castor-redis
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    networks:
      castor_network:
        ipv4_address: 172.20.0.7
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # ═══════════════════════════════════════════════════════════════
  # APPLICATION TIER
  # ═══════════════════════════════════════════════════════════════

  core-service:
    build:
      context: ./services/core
      dockerfile: Dockerfile
    container_name: castor-core
    environment:
      - FLASK_ENV=${FLASK_ENV:-production}
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - DATABASE_URL=postgresql://castor:${POSTGRES_PASSWORD}@postgres:5432/core_db
      - REDIS_URL=redis://redis:6379/0
    ports:
      - "5001:5001"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      castor_network:
        ipv4_address: 172.20.0.3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  e14-service:
    build:
      context: ./services/e14-service
      dockerfile: Dockerfile
    container_name: castor-e14
    environment:
      - FLASK_ENV=${FLASK_ENV:-production}
      - DATABASE_URL=postgresql://castor:${POSTGRES_PASSWORD}@postgres:5432/e14_db
      - REDIS_URL=redis://redis:6379/1
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - E14_OCR_MAX_PAGES=20
      - E14_OCR_DPI=150
      - E14_MAX_FILE_SIZE_MB=10
    ports:
      - "5002:5002"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      castor_network:
        ipv4_address: 172.20.0.4
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5002/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  dashboard-service:
    build:
      context: ./services/dashboard-ia
      dockerfile: Dockerfile
    container_name: castor-dashboard
    environment:
      - FLASK_ENV=${FLASK_ENV:-production}
      - DATABASE_URL=postgresql://castor:${POSTGRES_PASSWORD}@postgres:5432/dashboard_db
      - REDIS_URL=redis://redis:6379/2
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=gpt-4o
      - TWITTER_BEARER_TOKEN=${TWITTER_BEARER_TOKEN}
      - TWITTER_DAILY_TWEET_LIMIT=3
      - CACHE_TTL_TWITTER=86400
      - CACHE_TTL_SENTIMENT=86400
      - CACHE_TTL_OPENAI=43200
    volumes:
      - chromadb_data:/app/chromadb
    ports:
      - "5003:5003"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      castor_network:
        ipv4_address: 172.20.0.5
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5003/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

---

## Diagrama de Nodos y Artefactos

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                           DEPLOYMENT NODES & ARTIFACTS                                │
└──────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│ <<execution environment>>                                                            │
│ Docker Host (Linux Ubuntu 22.04 / Amazon Linux 2)                                   │
│                                                                                      │
│ Hardware Requirements:                                                               │
│ ├── CPU: 4 vCPU (mínimo), 8 vCPU (recomendado)                                      │
│ ├── RAM: 8 GB (mínimo), 16 GB (recomendado)                                         │
│ ├── Storage: 50 GB SSD                                                              │
│ └── Network: 100 Mbps                                                               │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │ <<container>> nginx:alpine                                                      │ │
│  │                                                                                 │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │ │
│  │  │ <<artifact>>    │  │ <<artifact>>    │  │ <<artifact>>    │                 │ │
│  │  │ nginx.conf      │  │ cert.pem        │  │ key.pem         │                 │ │
│  │  │ (378 lines)     │  │ SSL Certificate │  │ Private Key     │                 │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘                 │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │ <<container>> core-service (python:3.11-slim)                                   │ │
│  │                                                                                 │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │ │
│  │  │ <<artifact>>    │  │ <<artifact>>    │  │ <<artifact>>    │                 │ │
│  │  │ main.py         │  │ requirements.txt│  │ config.py       │                 │ │
│  │  │ Entry point     │  │ Dependencies    │  │ Configuration   │                 │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘                 │ │
│  │                                                                                 │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐   │ │
│  │  │ <<component>> Flask Application                                          │   │ │
│  │  │ ├── app/__init__.py (Application Factory)                                │   │ │
│  │  │ ├── app/routes/auth.py (Authentication Blueprint)                        │   │ │
│  │  │ ├── app/routes/users.py (User Management)                                │   │ │
│  │  │ ├── app/models/user.py (SQLAlchemy Models)                               │   │ │
│  │  │ └── services/token_service.py (JWT Handler)                              │   │ │
│  │  └─────────────────────────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │ <<container>> e14-service (python:3.11-slim)                                    │ │
│  │                                                                                 │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐   │ │
│  │  │ <<component>> Flask Application                                          │   │ │
│  │  │ ├── services/e14_ocr_service.py (Claude Vision OCR)                      │   │ │
│  │  │ ├── services/validation_service.py (Arithmetic Validation)               │   │ │
│  │  │ ├── services/alert_service.py (Alert Management)                         │   │ │
│  │  │ ├── services/reconciliation_service.py (Truth Selection)                 │   │ │
│  │  │ ├── services/audit_service.py (Immutable Logging)                        │   │ │
│  │  │ └── migrations/*.sql (Database Schema)                                   │   │ │
│  │  └─────────────────────────────────────────────────────────────────────────┘   │ │
│  │                                                                                 │ │
│  │  Dependencies: anthropic==0.39, pdf2image, Pillow, PyMuPDF                     │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │ <<container>> dashboard-service (python:3.11-slim)                              │ │
│  │                                                                                 │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐   │ │
│  │  │ <<component>> Flask Application                                          │   │ │
│  │  │ ├── services/twitter_service.py (Twitter API v2)                         │   │ │
│  │  │ ├── services/sentiment_service.py (BETO Model)                           │   │ │
│  │  │ ├── services/openai_service.py (GPT-4o Generation)                       │   │ │
│  │  │ ├── services/rag_service.py (RAG + ChromaDB)                             │   │ │
│  │  │ ├── services/forecast_service.py (Holt-Winters)                          │   │ │
│  │  │ └── services/campaign_agent.py (Automated Analysis)                      │   │ │
│  │  └─────────────────────────────────────────────────────────────────────────┘   │ │
│  │                                                                                 │ │
│  │  Dependencies: transformers==4.35, tweepy==4.14, openai==1.3, chromadb        │ │
│  │                                                                                 │ │
│  │  ┌─────────────────┐                                                           │ │
│  │  │ <<artifact>>    │                                                           │ │
│  │  │ BETO Model      │  ML Model for Spanish Sentiment Analysis                  │ │
│  │  │ (~500MB)        │  dccuchile/bert-base-spanish-wwm-cased                    │ │
│  │  └─────────────────┘                                                           │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │ <<container>> postgres:15-alpine                                                │ │
│  │                                                                                 │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │ │
│  │  │ <<database>>    │  │ <<database>>    │  │ <<database>>    │                 │ │
│  │  │ core_db         │  │ e14_db          │  │ dashboard_db    │                 │ │
│  │  │                 │  │                 │  │                 │                 │ │
│  │  │ Tables:         │  │ Tables:         │  │ Tables:         │                 │ │
│  │  │ - users         │  │ - form_instance │  │ - analyses      │                 │ │
│  │  │ - sessions      │  │ - ocr_field     │  │ - tweets        │                 │ │
│  │  │ - leads         │  │ - vote_tally    │  │ - chat_history  │                 │ │
│  │  │                 │  │ - alert         │  │ - forecasts     │                 │ │
│  │  │                 │  │ - audit_log     │  │                 │                 │ │
│  │  │                 │  │ - 25+ tables    │  │                 │                 │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘                 │ │
│  │                                                                                 │ │
│  │  Volume: pgdata (persistent)                                                   │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │ <<container>> redis:7-alpine                                                    │ │
│  │                                                                                 │ │
│  │  Config: maxmemory=256mb, policy=allkeys-lru                                   │ │
│  │                                                                                 │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │ │
│  │  │ <<cache>>       │  │ <<cache>>       │  │ <<cache>>       │                 │ │
│  │  │ DB 0 (Core)     │  │ DB 1 (E-14)     │  │ DB 2 (Dashboard)│                 │ │
│  │  │                 │  │                 │  │                 │                 │ │
│  │  │ - JWT tokens    │  │ - OCR results   │  │ - Twitter TTL   │                 │ │
│  │  │ - Sessions      │  │ - Form cache    │  │   24h           │                 │ │
│  │  │                 │  │                 │  │ - Sentiment TTL │                 │ │
│  │  │                 │  │                 │  │   24h           │                 │ │
│  │  │                 │  │                 │  │ - OpenAI TTL    │                 │ │
│  │  │                 │  │                 │  │   12h           │                 │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘                 │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Diagrama de Escalabilidad Horizontal

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                        ESCALABILIDAD HORIZONTAL (Futuro)                              │
└──────────────────────────────────────────────────────────────────────────────────────┘

                                    Load Balancer
                                   (AWS ALB / Nginx)
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
         ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
         │  Docker Host 1   │ │  Docker Host 2   │ │  Docker Host 3   │
         │                  │ │                  │ │                  │
         │ ┌──────────────┐ │ │ ┌──────────────┐ │ │ ┌──────────────┐ │
         │ │ Core Service │ │ │ │ Core Service │ │ │ │ Core Service │ │
         │ │   Replica 1  │ │ │ │   Replica 2  │ │ │ │   Replica 3  │ │
         │ └──────────────┘ │ │ └──────────────┘ │ │ └──────────────┘ │
         │                  │ │                  │ │                  │
         │ ┌──────────────┐ │ │ ┌──────────────┐ │ │ ┌──────────────┐ │
         │ │E-14 Service  │ │ │ │E-14 Service  │ │ │ │E-14 Service  │ │
         │ │   Replica 1  │ │ │ │   Replica 2  │ │ │ │   Replica 3  │ │
         │ └──────────────┘ │ │ └──────────────┘ │ │ └──────────────┘ │
         │                  │ │                  │ │                  │
         │ ┌──────────────┐ │ │ ┌──────────────┐ │ │ ┌──────────────┐ │
         │ │  Dashboard   │ │ │ │  Dashboard   │ │ │ │  Dashboard   │ │
         │ │   Replica 1  │ │ │ │   Replica 2  │ │ │ │   Replica 3  │ │
         │ └──────────────┘ │ │ └──────────────┘ │ │ └──────────────┘ │
         └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
                  │                    │                    │
                  └────────────────────┼────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
                    ▼                                     ▼
         ┌─────────────────────┐            ┌─────────────────────┐
         │   PostgreSQL        │            │   Redis Cluster     │
         │   Primary/Replica   │            │   (Sentinel)        │
         │                     │            │                     │
         │ ┌───────┐ ┌───────┐ │            │ ┌───────┐ ┌───────┐ │
         │ │Primary│ │Replica│ │            │ │Master │ │Replica│ │
         │ └───────┘ └───────┘ │            │ └───────┘ └───────┘ │
         └─────────────────────┘            └─────────────────────┘
```

---

## Puertos y Protocolos

| Servicio | Puerto Interno | Puerto Externo | Protocolo | Descripción |
|----------|----------------|----------------|-----------|-------------|
| Nginx | 80 | 80 | HTTP | Redirect to HTTPS |
| Nginx | 443 | 443 | HTTPS | TLS 1.2/1.3 |
| Core Service | 5001 | - | HTTP | Internal only |
| E-14 Service | 5002 | - | HTTP | Internal only |
| Dashboard Service | 5003 | - | HTTP | Internal only |
| PostgreSQL | 5432 | 5432* | TCP | *Dev only |
| Redis | 6379 | 6379* | TCP | *Dev only |

---

## Variables de Entorno por Servicio

### Core Service
```env
FLASK_ENV=production
SECRET_KEY=<min-32-chars>
JWT_SECRET_KEY=<secret>
JWT_ACCESS_TOKEN_EXPIRES=3600
DATABASE_URL=postgresql://castor:***@postgres:5432/core_db
REDIS_URL=redis://redis:6379/0
```

### E-14 Service
```env
FLASK_ENV=production
DATABASE_URL=postgresql://castor:***@postgres:5432/e14_db
REDIS_URL=redis://redis:6379/1
ANTHROPIC_API_KEY=sk-ant-***
E14_OCR_MAX_PAGES=20
E14_OCR_DPI=150
E14_MAX_FILE_SIZE_MB=10
```

### Dashboard Service
```env
FLASK_ENV=production
DATABASE_URL=postgresql://castor:***@postgres:5432/dashboard_db
REDIS_URL=redis://redis:6379/2
OPENAI_API_KEY=sk-***
OPENAI_MODEL=gpt-4o
TWITTER_BEARER_TOKEN=AAAA***
TWITTER_DAILY_TWEET_LIMIT=3
CACHE_TTL_TWITTER=86400
CACHE_TTL_SENTIMENT=86400
CACHE_TTL_OPENAI=43200
```

---

## Comandos de Despliegue

```bash
# Desarrollo
docker-compose up -d

# Producción
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Ver logs
docker-compose logs -f

# Escalar servicios
docker-compose up -d --scale core-service=3 --scale dashboard-service=3

# Health check
curl http://localhost/api/health

# Rebuild específico
docker-compose build --no-cache dashboard-service
docker-compose up -d dashboard-service
```

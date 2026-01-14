# CASTOR Elecciones - C4 Architecture Diagrams

## Level 1: System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CONTEXTO DEL SISTEMA                           │
└─────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │   Estratega     │
                    │   de Campaña    │
                    │   [Persona]     │
                    └────────┬────────┘
                             │ Consulta análisis,
                             │ recibe recomendaciones
                             ▼
┌──────────────┐    ┌─────────────────────────┐    ┌──────────────┐
│   Twitter    │◄───│                         │───►│   OpenAI     │
│   [External] │    │   CASTOR ELECCIONES     │    │   [External] │
│              │    │   [Software System]     │    │              │
│ Datos de     │    │                         │    │ Generación   │
│ conversación │    │ Plataforma de IA        │    │ de contenido │
│ pública      │    │ electoral para análisis │    │ estratégico  │
└──────────────┘    │ de narrativa y          │    └──────────────┘
                    │ estrategia de campaña   │
                    │                         │
                    └────────────┬────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
           ┌──────────────┐          ┌──────────────┐
           │  PostgreSQL  │          │    Redis     │
           │  [External]  │          │  [External]  │
           │              │          │              │
           │ Persistencia │          │ Cache        │
           │ de datos     │          │ distribuido  │
           └──────────────┘          └──────────────┘
```

---

## Level 2: Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CASTOR ELECCIONES                              │
│                         [Software System]                                │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Web Application                             │   │
│  │                      [Container: HTML/JS]                        │   │
│  │                                                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │  Landing    │  │  Dashboard  │  │  Chat RAG   │              │   │
│  │  │  Page       │  │  Unificado  │  │  Widget     │              │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │   │
│  │                                                                  │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │ HTTP/REST                            │
│                                 ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      API Backend                                 │   │
│  │                      [Container: Flask/Python]                   │   │
│  │                                                                  │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │                    API Routes                              │  │   │
│  │  │  /api/media  /api/campaign  /api/forecast  /api/chat      │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  │                              │                                   │   │
│  │  ┌───────────────────────────┴───────────────────────────────┐  │   │
│  │  │                   Service Layer                            │  │   │
│  │  │                                                            │  │   │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │  │   │
│  │  │  │ Twitter  │ │Sentiment │ │ OpenAI   │ │ Forecast │     │  │   │
│  │  │  │ Service  │ │ Service  │ │ Service  │ │ Service  │     │  │   │
│  │  │  │          │ │ (BETO)   │ │ (GPT-4o) │ │          │     │  │   │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │  │   │
│  │  │                                                            │  │   │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │  │   │
│  │  │  │ RAG      │ │ Campaign │ │ Trending │ │ Topic    │     │  │   │
│  │  │  │ Service  │ │ Agent    │ │ Service  │ │Classifier│     │  │   │
│  │  │  │          │ │          │ │          │ │ (PND)    │     │  │   │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │  │   │
│  │  │                                                            │  │   │
│  │  └────────────────────────────────────────────────────────────┘  │   │
│  │                              │                                   │   │
│  │  ┌───────────────────────────┴───────────────────────────────┐  │   │
│  │  │                   Infrastructure                           │  │   │
│  │  │                                                            │  │   │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │  │   │
│  │  │  │ Circuit  │ │  Cache   │ │  Rate    │ │  Audit   │     │  │   │
│  │  │  │ Breaker  │ │  (TTL)   │ │ Limiter  │ │  Logger  │     │  │   │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │  │   │
│  │  │                                                            │  │   │
│  │  └────────────────────────────────────────────────────────────┘  │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │  PostgreSQL  │    │    Redis     │    │   ChromaDB   │
    │  [Database]  │    │   [Cache]    │    │ [Vector DB]  │
    │              │    │              │    │              │
    │ Campaigns,   │    │ Sessions,    │    │ RAG Index,   │
    │ Leads,       │    │ API cache,   │    │ Embeddings   │
    │ Strategies   │    │ Rate limits  │    │              │
    └──────────────┘    └──────────────┘    └──────────────┘
```

---

## Level 3: Component Diagram (API Backend)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         API BACKEND [Flask]                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                            ROUTES LAYER                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │ media.py    │ │ campaign.py │ │ forecast.py │ │  chat.py    │       │
│  │             │ │             │ │             │ │             │       │
│  │ POST /media │ │POST /campaign│ │POST /forecast│ │POST /chat  │       │
│  │ /analyze    │ │/analyze     │ │/icce        │ │/rag         │       │
│  │             │ │/rivals      │ │/momentum    │ │             │       │
│  │             │ │/trending    │ │/scenario    │ │             │       │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘       │
│         │               │               │               │              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │ health.py   │ │  auth.py    │ │  leads.py   │ │   web.py    │       │
│  │             │ │             │ │             │ │             │       │
│  │ GET /health │ │POST /login  │ │POST /leads  │ │GET /        │       │
│  │ /ready      │ │/refresh     │ │             │ │/dashboard   │       │
│  │ /live       │ │             │ │             │ │             │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           SERVICE LAYER                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    AnalysisCorePipeline                            │ │
│  │  [Component: Orchestrates analysis flow]                          │ │
│  │                                                                    │ │
│  │  1. Fetch tweets → 2. Classify sentiment → 3. Group topics        │ │
│  │  4. Calculate metrics → 5. Generate insights                      │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                    │                                    │
│         ┌──────────────────────────┼──────────────────────────┐        │
│         │                          │                          │        │
│         ▼                          ▼                          ▼        │
│  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐  │
│  │ Twitter     │           │ Sentiment   │           │ OpenAI      │  │
│  │ Service     │           │ Service     │           │ Service     │  │
│  │             │           │             │           │             │  │
│  │ - search()  │           │ - analyze() │           │ - generate()│  │
│  │ - stream()  │           │ - batch()   │           │ - summarize│  │
│  │             │           │ - BETO model│           │ - speech()  │  │
│  └─────────────┘           └─────────────┘           └─────────────┘  │
│         │                          │                          │        │
│         │                          │                          │        │
│  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐  │
│  │ Forecast    │           │ RAG         │           │ Campaign    │  │
│  │ Service     │           │ Service     │           │ Agent       │  │
│  │             │           │             │           │             │  │
│  │ - icce()    │           │ - index()   │           │ - analyze() │  │
│  │ - momentum()│           │ - query()   │           │ - recommend│  │
│  │ - project() │           │ - sync()    │           │ - compare() │  │
│  └─────────────┘           └─────────────┘           └─────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        INFRASTRUCTURE LAYER                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │ Circuit     │ │ Cache       │ │ Rate        │ │ Audit       │       │
│  │ Breaker     │ │ Manager     │ │ Limiter     │ │ Logger      │       │
│  │             │ │             │ │             │ │             │       │
│  │ States:     │ │ TTL: 15min  │ │ Global:     │ │ Events:     │       │
│  │ - closed    │ │ Redis +     │ │ 100/min     │ │ - auth      │       │
│  │ - open      │ │ In-memory   │ │ Per-user:   │ │ - analysis  │       │
│  │ - half-open │ │ fallback    │ │ 10/min      │ │ - security  │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
│                                                                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────┐       │
│  │ Database    │ │ Model       │ │ Health Check                 │       │
│  │ Service     │ │ Singleton   │ │                              │       │
│  │             │ │             │ │ - /health (basic)            │       │
│  │ PostgreSQL  │ │ BETO loaded │ │ - /health/full (complete)    │       │
│  │ connection  │ │ once        │ │ - /health/sla (metrics)      │       │
│  │ pooling     │ │             │ │ - /health/ready (K8s)        │       │
│  └─────────────┘ └─────────────┘ └─────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW: ANÁLISIS                              │
└─────────────────────────────────────────────────────────────────────────┘

Usuario                                                              Resultado
  │                                                                      ▲
  │ 1. Request                                                          │
  │    {location, topic, candidate}                                     │
  ▼                                                                      │
┌─────────────────────────────────────────────────────────────────────────┐
│                           API Gateway (Flask)                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 2. Validation (Pydantic) → 3. Rate Limit Check → 4. Auth Check  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
  │
  │ 5. Cache Check (Redis/Memory)
  │    HIT? → Return cached ─────────────────────────────────────────────┐
  │    MISS? ↓                                                           │
  ▼                                                                      │
┌─────────────────┐                                                      │
│ Twitter Service │ 6. Fetch tweets                                      │
│  [Circuit Breaker]   query: "{topic} {candidate} {location}"          │
└────────┬────────┘                                                      │
         │                                                               │
         │ tweets[]                                                      │
         ▼                                                               │
┌─────────────────┐                                                      │
│Sentiment Service│ 7. Analyze sentiment (BETO)                          │
│  [Model Singleton]   for each tweet → {positive, negative, neutral}   │
└────────┬────────┘                                                      │
         │                                                               │
         │ tweets[] + sentiment                                          │
         ▼                                                               │
┌─────────────────┐                                                      │
│ Topic Classifier│ 8. Classify by PND topics                            │
│                 │    Seguridad, Economía, Salud, Paz, etc.            │
└────────┬────────┘                                                      │
         │                                                               │
         │ topics[] + sentiment                                          │
         ▼                                                               │
┌─────────────────┐                                                      │
│Forecast Service │ 9. Calculate metrics                                 │
│                 │    ICCE, Momentum, SNA, SVE                         │
└────────┬────────┘                                                      │
         │                                                               │
         │ metrics + forecast                                            │
         ▼                                                               │
┌─────────────────┐                                                      │
│ OpenAI Service  │ 10. Generate insights (GPT-4o)                       │
│  [Circuit Breaker]    Executive summary, strategy, speech             │
└────────┬────────┘                                                      │
         │                                                               │
         │ analysis complete                                             │
         ▼                                                               │
┌─────────────────┐                                                      │
│  Cache Write    │ 11. Store in cache (TTL: 15min)                      │
│  RAG Index      │ 12. Index for retrieval                              │
│  Audit Log      │ 13. Log audit event                                  │
└────────┬────────┘                                                      │
         │                                                               │
         └───────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                              Response JSON
                              {
                                summary, sentiment, topics,
                                metrics, forecast, insights
                              }
```

---

## Deployment Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │    Internet     │
                              │   [Cloud]       │
                              └────────┬────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
           ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
           │   Vercel     │   │    Ngrok     │   │  Railway/    │
           │   [CDN]      │   │   [Tunnel]   │   │  Heroku      │
           │              │   │              │   │              │
           │ Static files │   │ Dev access   │   │ Production   │
           │ Landing page │   │ to local     │   │ deployment   │
           └──────────────┘   └──────────────┘   └──────────────┘
                    │                  │                  │
                    └──────────────────┼──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │        CASTOR Backend               │
                    │        [Gunicorn + Flask]           │
                    │                                     │
                    │  Workers: 4 (2 × CPU + 1)          │
                    │  Timeout: 120s                     │
                    │  Preload: BETO model               │
                    └─────────────────────────────────────┘
                              │         │
               ┌──────────────┘         └──────────────┐
               ▼                                       ▼
    ┌─────────────────┐                    ┌─────────────────┐
    │    Supabase     │                    │     Upstash     │
    │   [PostgreSQL]  │                    │     [Redis]     │
    │                 │                    │                 │
    │ - Campaigns     │                    │ - Sessions      │
    │ - Leads         │                    │ - Cache         │
    │ - Strategies    │                    │ - Rate limits   │
    └─────────────────┘                    └─────────────────┘


External Services:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    Twitter      │  │     OpenAI      │  │   Hugging Face  │
│   [API v2]      │  │    [GPT-4o]     │  │     [BETO]      │
│                 │  │                 │  │                 │
│ Rate: 100/month │  │ Rate: by tokens │  │ Model download  │
│ (Free tier)     │  │                 │  │ at startup      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Referencias

- [C4 Model](https://c4model.com/)
- [Structurizr](https://structurizr.com/)
- Simon Brown - "The C4 Model for Software Architecture"

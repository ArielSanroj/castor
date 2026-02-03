# Diagramas C4 - CASTOR ELECCIONES

## Nivel 1: Diagrama de Contexto

Muestra el sistema Castor y sus interacciones con usuarios y sistemas externos.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   CONTEXTO                                       │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
    │   Analista    │     │  Observador   │     │ Administrador │
    │  de Campaña   │     │   Electoral   │     │  del Sistema  │
    │   [Persona]   │     │   [Persona]   │     │   [Persona]   │
    └───────┬───────┘     └───────┬───────┘     └───────┬───────┘
            │                     │                     │
            │  Analiza            │  Registra           │  Gestiona
            │  sentimiento        │  incidentes         │  usuarios
            │  y estrategias      │  y formularios      │  y alertas
            │                     │                     │
            └─────────────────────┼─────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │                         │
                    │    CASTOR ELECCIONES    │
                    │    [Sistema Software]   │
                    │                         │
                    │  Plataforma de IA para  │
                    │  análisis electoral y   │
                    │  procesamiento de       │
                    │  formularios E-14       │
                    │                         │
                    └───────────┬─────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
            ▼                   ▼                   ▼
    ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
    │  Twitter/X    │   │    OpenAI     │   │   Anthropic   │
    │  [Sistema     │   │  [Sistema     │   │  [Sistema     │
    │   Externo]    │   │   Externo]    │   │   Externo]    │
    │               │   │               │   │               │
    │ API v2 para   │   │ GPT-4o para   │   │ Claude 3.5    │
    │ búsqueda de   │   │ generación    │   │ para OCR de   │
    │ tweets        │   │ de contenido  │   │ formularios   │
    └───────────────┘   └───────────────┘   └───────────────┘
```

---

## Nivel 2: Diagrama de Contenedores

Muestra los contenedores (servicios, bases de datos) que componen Castor.

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                    CONTENEDORES                                       │
└──────────────────────────────────────────────────────────────────────────────────────┘

                            ┌─────────────────────┐
                            │   Navegador Web     │
                            │   [Cliente]         │
                            │   HTML5/JS/CSS      │
                            └──────────┬──────────┘
                                       │
                                       │ HTTPS
                                       ▼
                        ┌──────────────────────────────┐
                        │         NGINX                │
                        │      [API Gateway]           │
                        │   Reverse Proxy + SSL        │
                        │   Rate Limiting              │
                        │   Puerto: 80/443             │
                        └──────────────┬───────────────┘
                                       │
         ┌─────────────────┬───────────┴───────────┬─────────────────┐
         │                 │                       │                 │
         ▼                 ▼                       ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Core Service   │ │  E-14 Service   │ │Dashboard Service│ │Backend Monolito │
│  [Contenedor]   │ │  [Contenedor]   │ │  [Contenedor]   │ │  [Contenedor]   │
│                 │ │                 │ │                 │ │                 │
│  Flask 3.0      │ │  Flask 3.0      │ │  Flask 3.0      │ │  Flask 3.0      │
│  Puerto: 5001   │ │  Puerto: 5002   │ │  Puerto: 5003   │ │  Puerto: 5001   │
│                 │ │                 │ │                 │ │                 │
│  - Auth JWT     │ │  - OCR Claude   │ │  - Sentiment    │ │  - Templates    │
│  - Usuarios     │ │  - Validación   │ │  - RAG Chat     │ │  - Rutas Web    │
│  - Sesiones     │ │  - Alertas      │ │  - Pronósticos  │ │  - Blueprints   │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │                   │
         │                   │                   │                   │
         └───────────────────┴─────────┬─────────┴───────────────────┘
                                       │
                     ┌─────────────────┴─────────────────┐
                     │                                   │
                     ▼                                   ▼
          ┌─────────────────────┐             ┌─────────────────────┐
          │    PostgreSQL 15    │             │     Redis 7.0       │
          │    [Base de Datos]  │             │     [Cache]         │
          │                     │             │                     │
          │  - core_db          │             │  - DB 0: Core       │
          │  - e14_db           │             │  - DB 1: E-14       │
          │  - dashboard_db     │             │  - DB 2: Dashboard  │
          │                     │             │                     │
          │  Puerto: 5432       │             │  Puerto: 6379       │
          └─────────────────────┘             └─────────────────────┘

                              SISTEMAS EXTERNOS
         ┌─────────────────┬─────────────────┬─────────────────┐
         │                 │                 │                 │
         ▼                 ▼                 ▼                 ▼
  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
  │ Twitter API │   │ OpenAI API  │   │Anthropic API│   │  ChromaDB   │
  │   v2        │   │   GPT-4o    │   │ Claude 3.5  │   │ [Vector DB] │
  │  [Externo]  │   │  [Externo]  │   │  [Externo]  │   │  [Interno]  │
  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
```

---

## Nivel 3: Diagrama de Componentes

### 3.1 Core Service - Componentes

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         CORE SERVICE (Puerto 5001)                            │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                           API Layer (Flask Blueprints)                 │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │  │
│  │  │  /api/auth   │  │  /api/users  │  │  /api/leads  │  │ /api/health│  │  │
│  │  │  [Blueprint] │  │  [Blueprint] │  │  [Blueprint] │  │ [Blueprint]│  │  │
│  │  │              │  │              │  │              │  │            │  │  │
│  │  │ - login      │  │ - profile    │  │ - create     │  │ - status   │  │  │
│  │  │ - register   │  │ - update     │  │ - list       │  │ - ready    │  │  │
│  │  │ - logout     │  │ - delete     │  │ - delete     │  │            │  │  │
│  │  │ - refresh    │  │              │  │              │  │            │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────────────┘  │  │
│  └─────────┼─────────────────┼─────────────────┼──────────────────────────┘  │
│            │                 │                 │                              │
│            └─────────────────┼─────────────────┘                              │
│                              ▼                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                         Service Layer                                  │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │  │
│  │  │   AuthService    │  │   UserService    │  │   TokenService       │  │  │
│  │  │   [Componente]   │  │   [Componente]   │  │   [Componente]       │  │  │
│  │  │                  │  │                  │  │                      │  │  │
│  │  │ - validate_creds │  │ - get_user       │  │ - generate_jwt       │  │  │
│  │  │ - hash_password  │  │ - create_user    │  │ - verify_jwt         │  │  │
│  │  │ - verify_token   │  │ - update_user    │  │ - refresh_token      │  │  │
│  │  └────────┬─────────┘  └────────┬─────────┘  └──────────────────────┘  │  │
│  └───────────┼─────────────────────┼─────────────────────────────────────┘  │
│              │                     │                                         │
│              └──────────┬──────────┘                                         │
│                         ▼                                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                         Data Layer                                     │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │  │
│  │  │   User Model     │  │  Session Model   │  │   Lead Model         │  │  │
│  │  │   [SQLAlchemy]   │  │  [SQLAlchemy]    │  │   [SQLAlchemy]       │  │  │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
└──────────────────────────────────────┼───────────────────────────────────────┘
                                       ▼
                              ┌─────────────────┐
                              │   PostgreSQL    │
                              │    core_db      │
                              └─────────────────┘
```

### 3.2 E-14 Service - Componentes

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         E-14 SERVICE (Puerto 5002)                            │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                           API Layer (Flask Blueprints)                 │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │  │
│  │  │ /api/e14     │  │/api/pipeline │  │ /api/review  │  │ /api/alerts│  │  │
│  │  │ [Blueprint]  │  │ [Blueprint]  │  │ [Blueprint]  │  │ [Blueprint]│  │  │
│  │  │              │  │              │  │              │  │            │  │  │
│  │  │ - process    │  │ - ingest     │  │ - pending    │  │ - list     │  │  │
│  │  │ - validate   │  │ - status     │  │ - approve    │  │ - ack      │  │  │
│  │  │ - status     │  │ - batch      │  │ - reject     │  │ - resolve  │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │  │
│  └─────────┼─────────────────┼─────────────────┼────────────────┼─────────┘  │
│            │                 │                 │                │            │
│            └─────────────────┴────────┬────────┴────────────────┘            │
│                                       ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                         Service Layer                                  │  │
│  │                                                                        │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐ │  │
│  │  │  E14OCRService  │  │ValidationService│  │  ReconciliationService  │ │  │
│  │  │  [Componente]   │  │  [Componente]   │  │     [Componente]        │ │  │
│  │  │                 │  │                 │  │                         │ │  │
│  │  │ - extract_cells │  │ - arithmetic    │  │ - compare_sources       │ │  │
│  │  │ - ocr_with_     │  │ - detect_       │  │ - choose_truth          │ │  │
│  │  │   confidence    │  │   discrepancy   │  │ - generate_report       │ │  │
│  │  │ - parallel_ocr  │  │ - create_alert  │  │                         │ │  │
│  │  └────────┬────────┘  └────────┬────────┘  └────────────┬────────────┘ │  │
│  │           │                    │                        │              │  │
│  │  ┌────────┴────────┐  ┌────────┴────────┐  ┌────────────┴────────────┐ │  │
│  │  │IngestionPipeline│  │  AlertService   │  │    AuditLogService      │ │  │
│  │  │  [Componente]   │  │  [Componente]   │  │     [Componente]        │ │  │
│  │  │                 │  │                 │  │                         │ │  │
│  │  │ - batch_process │  │ - CRITICAL      │  │ - log_action            │ │  │
│  │  │ - queue_forms   │  │ - HIGH/MEDIUM   │  │ - immutable_record      │ │  │
│  │  │ - retry_failed  │  │ - notify        │  │ - audit_trail           │ │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                         Data Layer (Models)                            │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐          │  │
│  │  │FormInstance│ │  OCRField  │ │ VoteTally  │ │Discrepancy │          │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘          │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐          │  │
│  │  │   Alert    │ │Reconciliat.│ │  AuditLog  │ │ Validation │          │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
└──────────────────────────────────────┼───────────────────────────────────────┘
                      ┌────────────────┼────────────────┐
                      ▼                ▼                ▼
             ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
             │ PostgreSQL  │   │    Redis    │   │  Anthropic  │
             │   e14_db    │   │   Cache     │   │  Claude API │
             └─────────────┘   └─────────────┘   └─────────────┘
```

### 3.3 Dashboard Service - Componentes

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       DASHBOARD SERVICE (Puerto 5003)                         │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                           API Layer (Flask Blueprints)                 │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │  │
│  │  │ /api/media   │  │ /api/chat    │  │/api/forecast │  │/api/campaign│ │  │
│  │  │ [Blueprint]  │  │ [Blueprint]  │  │ [Blueprint]  │  │ [Blueprint]│  │  │
│  │  │              │  │              │  │              │  │            │  │  │
│  │  │ - analyze    │  │ - rag        │  │ - predict    │  │ - analyze  │  │  │
│  │  │ - history    │  │ - history    │  │ - metrics    │  │ - strategy │  │  │
│  │  │ - export     │  │ - clear      │  │ - trends     │  │ - speech   │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │  │
│  └─────────┼─────────────────┼─────────────────┼────────────────┼─────────┘  │
│            │                 │                 │                │            │
│            └─────────────────┴────────┬────────┴────────────────┘            │
│                                       ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                         Service Layer                                  │  │
│  │                                                                        │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐ │  │
│  │  │ TwitterService  │  │SentimentService │  │    OpenAIService        │ │  │
│  │  │  [Componente]   │  │  [Componente]   │  │     [Componente]        │ │  │
│  │  │                 │  │                 │  │                         │ │  │
│  │  │ - search_tweets │  │ - analyze_beto  │  │ - generate_summary      │ │  │
│  │  │ - get_trending  │  │ - classify_     │  │ - generate_strategy     │ │  │
│  │  │ - rate_limit    │  │   sentiment     │  │ - generate_speech       │ │  │
│  │  └────────┬────────┘  └────────┬────────┘  └────────────┬────────────┘ │  │
│  │           │                    │                        │              │  │
│  │  ┌────────┴────────┐  ┌────────┴────────┐  ┌────────────┴────────────┐ │  │
│  │  │   RAGService    │  │ ForecastService │  │  CampaignAgentService   │ │  │
│  │  │  [Componente]   │  │  [Componente]   │  │     [Componente]        │ │  │
│  │  │                 │  │                 │  │                         │ │  │
│  │  │ - index_tweets  │  │ - holt_winters  │  │ - auto_analysis         │ │  │
│  │  │ - semantic_     │  │ - calc_icce     │  │ - recommendations       │ │  │
│  │  │   search        │  │ - calc_momentum │  │ - optimize_message      │ │  │
│  │  │ - chat_response │  │                 │  │                         │ │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘ │  │
│  │                                                                        │  │
│  │  ┌─────────────────┐  ┌─────────────────┐                              │  │
│  │  │TopicClassifier  │  │TrendingService  │                              │  │
│  │  │  [Componente]   │  │  [Componente]   │                              │  │
│  │  │                 │  │                 │                              │  │
│  │  │ - classify_pnd  │  │ - detect_topics │                              │  │
│  │  │ - categorize    │  │ - rank_trending │                              │  │
│  │  └─────────────────┘  └─────────────────┘                              │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                      External Integrations                             │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐          │  │
│  │  │ Twitter    │ │  OpenAI    │ │  BETO      │ │  ChromaDB  │          │  │
│  │  │ API v2     │ │  GPT-4o    │ │Transformers│ │ VectorDB   │          │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
└──────────────────────────────────────┼───────────────────────────────────────┘
                      ┌────────────────┼────────────────┐
                      ▼                ▼                ▼
             ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
             │ PostgreSQL  │   │    Redis    │   │  ChromaDB   │
             │ dashboard_db│   │   Cache     │   │  Embeddings │
             └─────────────┘   └─────────────┘   └─────────────┘
```

---

## Nivel 4: Diagrama de Código (Clases Principales)

### 4.1 E14 OCR Service - Detalle de Código

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         E14OCRService - Class Diagram                         │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│           <<interface>>                 │
│           OCRProvider                   │
├─────────────────────────────────────────┤
│ + extract_text(image: bytes): str       │
│ + extract_cells(image: bytes): List     │
│ + get_confidence(): float               │
└────────────────────┬────────────────────┘
                     │
                     │ implements
                     │
┌────────────────────┴────────────────────┐
│           ClaudeOCRAdapter              │
├─────────────────────────────────────────┤
│ - api_key: str                          │
│ - model: str = "claude-3-5-sonnet"      │
│ - max_tokens: int = 4096                │
├─────────────────────────────────────────┤
│ + extract_text(image: bytes): str       │
│ + extract_cells(image: bytes): List     │
│ + extract_with_confidence(): OCRResult  │
│ - _encode_image(image: bytes): str      │
│ - _parse_response(response): dict       │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│           E14OCRService                 │
├─────────────────────────────────────────┤
│ - ocr_provider: OCRProvider             │
│ - db_session: Session                   │
│ - config: E14Config                     │
├─────────────────────────────────────────┤
│ + process_form(file: bytes): FormResult │
│ + validate_arithmetic(): ValidationRes  │
│ + detect_discrepancies(): List[Discrep] │
│ + parallel_ocr(files: List): List       │
│ - _preprocess_image(image): bytes       │
│ - _extract_vote_tallies(): VoteTally    │
│ - _save_to_database(result): None       │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│           ValidationService             │
├─────────────────────────────────────────┤
│ - rules: List[ValidationRule]           │
│ - alert_service: AlertService           │
├─────────────────────────────────────────┤
│ + validate(form: FormInstance): Result  │
│ + check_arithmetic(votes: VoteTally)    │
│ + compare_sources(sources: List): Diff  │
│ - _apply_rule(rule, data): bool         │
│ - _create_alert(severity, message)      │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│           AlertService                  │
├─────────────────────────────────────────┤
│ - db_session: Session                   │
│ - notification_service: NotificationSvc │
├─────────────────────────────────────────┤
│ + create_alert(severity, type, msg)     │
│ + acknowledge(alert_id): None           │
│ + resolve(alert_id, resolution): None   │
│ + list_open_alerts(): List[Alert]       │
│ - _notify_stakeholders(alert): None     │
└─────────────────────────────────────────┘
```

### 4.2 Sentiment Analysis - Detalle de Código

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    SentimentService - Class Diagram                           │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│           <<interface>>                 │
│           SentimentAnalyzer             │
├─────────────────────────────────────────┤
│ + analyze(text: str): SentimentResult   │
│ + batch_analyze(texts: List): List      │
└────────────────────┬────────────────────┘
                     │
                     │ implements
                     │
┌────────────────────┴────────────────────┐
│           BETOSentimentAnalyzer         │
├─────────────────────────────────────────┤
│ - model: AutoModelForSeqClassification  │
│ - tokenizer: AutoTokenizer              │
│ - device: str = "cpu"                   │
│ - model_name: str = "dccuchile/bert-   │
│                      base-spanish-wwm"  │
├─────────────────────────────────────────┤
│ + analyze(text: str): SentimentResult   │
│ + batch_analyze(texts: List): List      │
│ - _preprocess(text: str): str           │
│ - _predict(tokens): Tensor              │
│ - _to_sentiment(logits): str            │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│           SentimentService              │
├─────────────────────────────────────────┤
│ - analyzer: SentimentAnalyzer           │
│ - cache: Redis                          │
│ - cache_ttl: int = 86400                │
├─────────────────────────────────────────┤
│ + analyze_tweets(tweets: List): Result  │
│ + get_sentiment_distribution(): dict    │
│ + calculate_isn(): float                │
│ - _cache_key(text: str): str            │
│ - _get_cached(key: str): Optional       │
│ - _set_cached(key, value): None         │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│           TopicClassifierService        │
├─────────────────────────────────────────┤
│ - pnd_categories: Dict[str, List[str]]  │
│ - embeddings_model: str                 │
├─────────────────────────────────────────┤
│ + classify(text: str): str              │
│ + batch_classify(texts: List): List     │
│ + get_pnd_distribution(): dict          │
│ - _match_keywords(text, category): float│
│ - _semantic_similarity(text, cat): float│
└─────────────────────────────────────────┘
```

### 4.3 RAG Chat Service - Detalle de Código

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       RAGService - Class Diagram                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│           RAGService                    │
├─────────────────────────────────────────┤
│ - vector_store: ChromaDB                │
│ - embeddings: OpenAIEmbeddings          │
│ - llm: OpenAI                           │
│ - collection_name: str                  │
├─────────────────────────────────────────┤
│ + index_documents(docs: List): None     │
│ + search(query: str, k: int): List      │
│ + chat(query: str, history: List): str  │
│ - _embed_text(text: str): List[float]   │
│ - _build_context(docs: List): str       │
│ - _generate_response(ctx, query): str   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│           OpenAIService                 │
├─────────────────────────────────────────┤
│ - client: OpenAI                        │
│ - model: str = "gpt-4o"                 │
│ - max_tokens: int = 4096                │
│ - temperature: float = 0.7              │
├─────────────────────────────────────────┤
│ + generate_summary(data: dict): str     │
│ + generate_strategy(analysis): str      │
│ + generate_speech(context: dict): str   │
│ + chat_completion(messages: List): str  │
│ - _build_prompt(template, data): str    │
│ - _handle_rate_limit(): None            │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│           ForecastService               │
├─────────────────────────────────────────┤
│ - historical_data: DataFrame            │
│ - forecast_days: int = 14               │
├─────────────────────────────────────────┤
│ + predict(candidate: str): Forecast     │
│ + calculate_icce(): float               │
│ + calculate_momentum(): float           │
│ + calculate_sve(): float                │
│ - _holt_winters(data: Series): Series   │
│ - _trend_analysis(data: Series): dict   │
└─────────────────────────────────────────┘
```

---

## Diagrama de Flujo de Datos

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    FLUJO: Análisis de Campaña Electoral                       │
└──────────────────────────────────────────────────────────────────────────────┘

  Usuario                                Sistema
     │
     │  1. POST /api/campaign/analyze
     │     {location, topic, candidate}
     ▼
┌─────────┐
│ Request │───────────────────────────────────────────────────────┐
└─────────┘                                                       │
                                                                  ▼
                                              ┌───────────────────────────────┐
                                              │      TrendingService          │
                                              │  Detectar trending topics     │
                                              └───────────────┬───────────────┘
                                                              │
                                                              ▼
                                              ┌───────────────────────────────┐
                                              │      TwitterService           │
                                              │  Buscar tweets por tema       │
                                              │  + ubicación (max 15/request) │
                                              └───────────────┬───────────────┘
                                                              │
                                              ┌───────────────┴───────────────┐
                                              ▼                               ▼
                              ┌─────────────────────────┐   ┌─────────────────────────┐
                              │   SentimentService      │   │  TopicClassifierService │
                              │   Análisis BETO         │   │  Clasificar por PND     │
                              │   (español)             │   │                         │
                              └───────────┬─────────────┘   └───────────┬─────────────┘
                                          │                             │
                                          └──────────────┬──────────────┘
                                                         │
                                                         ▼
                                              ┌───────────────────────────────┐
                                              │      OpenAIService            │
                                              │  Generar:                     │
                                              │  - Executive Summary          │
                                              │  - Strategic Plan             │
                                              │  - Speech                     │
                                              │  - Chart Data                 │
                                              └───────────────┬───────────────┘
                                                              │
                                                              ▼
                                              ┌───────────────────────────────┐
                                              │      DatabaseService          │
                                              │  Guardar análisis             │
                                              └───────────────┬───────────────┘
                                                              │
     ┌────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────┐
│ Response │  {summary, strategy, speech, charts, metrics}
└──────────┘
```

---

## Resumen de Notación C4

| Nivel | Descripción | Audiencia |
|-------|-------------|-----------|
| **1. Contexto** | Sistema + actores externos | Todos los stakeholders |
| **2. Contenedores** | Servicios, DBs, colas | Arquitectos, DevOps |
| **3. Componentes** | Módulos internos por servicio | Desarrolladores senior |
| **4. Código** | Clases, interfaces, métodos | Desarrolladores |

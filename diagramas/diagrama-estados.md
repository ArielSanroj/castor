# Diagramas de Estados - CASTOR ELECCIONES

## 1. Vista General de Entidades con Estados

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         ENTIDADES CON MÁQUINAS DE ESTADO                             │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   FormInstance      │  │       Alert         │  │   Reconciliation    │
│   (6 estados)       │  │   (5 estados)       │  │   (3 estados)       │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘

┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   User Session      │  │       Lead          │  │     Analysis        │
│   (4 estados)       │  │   (5 estados)       │  │   (4 estados)       │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘

┌─────────────────────┐  ┌─────────────────────┐
│   Election          │  │   CircuitBreaker    │
│   (4 estados)       │  │   (3 estados)       │
└─────────────────────┘  └─────────────────────┘
```

---

## 2. FormInstance (Formulario E-14)

### Diagrama de Estados

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    FORMULARIO E-14 - DIAGRAMA DE ESTADOS                             │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌───┐
                                    │ ● │  Estado Inicial
                                    └─┬─┘
                                      │
                                      │ upload(file)
                                      ▼
                            ┌─────────────────────┐
                            │                     │
                            │      PENDING        │
                            │                     │
                            │  Formulario subido  │
                            │  esperando OCR      │
                            │                     │
                            └──────────┬──────────┘
                                       │
                                       │ start_ocr()
                                       ▼
                            ┌─────────────────────┐
                            │                     │
                            │    PROCESSING       │
                            │                     │
                            │  OCR en ejecución   │
                            │  con Claude Vision  │
                            │                     │
                            └──────────┬──────────┘
                                       │
                     ┌─────────────────┼─────────────────┐
                     │                 │                 │
                     │ ocr_failed()    │ ocr_success()   │ needs_review()
                     │                 │                 │ [confidence < 0.85
                     ▼                 │                 │  OR discrepancies]
            ┌─────────────────┐        │                 ▼
            │                 │        │        ┌─────────────────────┐
            │     FAILED      │        │        │                     │
            │                 │        │        │   NEEDS_REVIEW      │
            │  Error en OCR   │        │        │                     │
            │  o validación   │        │        │  Requiere revisión  │
            │                 │        │        │  manual (HITL)      │
            └────────┬────────┘        │        │                     │
                     │                 │        └──────────┬──────────┘
                     │                 │                   │
                     │ retry()         │        ┌──────────┼──────────┐
                     │                 │        │          │          │
                     ▼                 │        │ approve()│          │ reject()
            ┌─────────────────┐        │        │          │          │
            │   (PENDING)     │◄───────┘        │          │          ▼
            └─────────────────┘                 │          │  ┌─────────────────┐
                                               │          │  │   (FAILED)      │
                                               ▼          │  └─────────────────┘
                                    ┌─────────────────────┐
                                    │                     │
                                    │    COMPLETED        │
                                    │                     │
                                    │  OCR exitoso,       │
                                    │  pendiente válida.  │
                                    │                     │
                                    └──────────┬──────────┘
                                               │
                                               │ validate()
                                               │ [all_rules_pass]
                                               ▼
                                    ┌─────────────────────┐
                                    │                     │
                                    │    VALIDATED        │◄─────────┘
                                    │                     │
                                    │  Formulario válido  │
                                    │  y reconciliado     │
                                    │                     │
                                    └──────────┬──────────┘
                                               │
                                               ▼
                                           ┌───────┐
                                           │   ◉   │  Estado Final
                                           └───────┘
```

### Tabla de Transiciones

| Estado Actual | Evento | Condición/Guarda | Estado Siguiente | Acción |
|---------------|--------|------------------|------------------|--------|
| - | upload(file) | file_valid | PENDING | Guardar archivo, crear registro |
| PENDING | start_ocr() | - | PROCESSING | Encolar job OCR |
| PROCESSING | ocr_success() | confidence >= 0.85 AND no_discrepancies | COMPLETED | Guardar resultados OCR |
| PROCESSING | needs_review() | confidence < 0.85 OR has_discrepancies | NEEDS_REVIEW | Crear alerta, notificar admin |
| PROCESSING | ocr_failed() | error | FAILED | Log error, notificar |
| FAILED | retry() | retry_count < 3 | PENDING | Incrementar contador, re-encolar |
| NEEDS_REVIEW | approve(corrections) | admin_approved | VALIDATED | Aplicar correcciones, audit log |
| NEEDS_REVIEW | reject(reason) | admin_rejected | FAILED | Log razón, notificar observador |
| COMPLETED | validate() | all_rules_pass | VALIDATED | Marcar como fuente de verdad |
| COMPLETED | validate() | rules_fail | NEEDS_REVIEW | Crear discrepancias |

---

## 3. Alert (Alerta)

### Diagrama de Estados

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          ALERTA - DIAGRAMA DE ESTADOS                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌───┐
                                    │ ● │
                                    └─┬─┘
                                      │
                                      │ create_alert(severity, message)
                                      ▼
                            ┌─────────────────────┐
                            │                     │
                            │        OPEN         │
                            │                     │
                            │  Alerta creada,     │
                            │  sin atender        │
                            │                     │
                            │  [notifica según    │
                            │   severidad]        │
                            │                     │
                            └──────────┬──────────┘
                                       │
                                       │ acknowledge(user)
                                       ▼
                            ┌─────────────────────┐
                            │                     │
                            │   ACKNOWLEDGED      │
                            │                     │
                            │  Admin ha visto     │
                            │  la alerta          │
                            │                     │
                            └──────────┬──────────┘
                                       │
                         ┌─────────────┼─────────────┐
                         │             │             │
                         │ investigate()            │ mark_false_positive()
                         │             │             │
                         ▼             │             ▼
            ┌─────────────────────┐    │    ┌─────────────────────┐
            │                     │    │    │                     │
            │   INVESTIGATING     │    │    │   FALSE_POSITIVE    │
            │                     │    │    │                     │
            │  En proceso de      │    │    │  Alerta incorrecta  │
            │  investigación      │    │    │  o duplicada        │
            │                     │    │    │                     │
            └──────────┬──────────┘    │    └──────────┬──────────┘
                       │               │               │
                       │ resolve()     │               │
                       │               │               │
                       ▼               │               │
            ┌─────────────────────┐    │               │
            │                     │◄───┘               │
            │      RESOLVED       │                    │
            │                     │                    │
            │  Problema resuelto  │                    │
            │  con notas          │                    │
            │                     │                    │
            └──────────┬──────────┘                    │
                       │                               │
                       │                               │
                       ▼                               ▼
                   ┌───────┐                       ┌───────┐
                   │   ◉   │                       │   ◉   │
                   └───────┘                       └───────┘


═══════════════════════════════════════════════════════════════════════════════════════
                              NOTIFICACIONES POR SEVERIDAD
═══════════════════════════════════════════════════════════════════════════════════════

    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    │   CRITICAL   │     │     HIGH     │     │    MEDIUM    │     │     LOW      │
    ├──────────────┤     ├──────────────┤     ├──────────────┤     ├──────────────┤
    │ - SMS        │     │ - Email      │     │ - Email      │     │ - Dashboard  │
    │ - Email      │     │ - Dashboard  │     │ - Dashboard  │     │   solo       │
    │ - Dashboard  │     │ - Push       │     │              │     │              │
    │ - Push       │     │              │     │              │     │              │
    │ - Llamada    │     │              │     │              │     │              │
    └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

### Tabla de Transiciones

| Estado Actual | Evento | Guarda | Estado Siguiente | Acción |
|---------------|--------|--------|------------------|--------|
| - | create_alert() | - | OPEN | Notificar según severidad |
| OPEN | acknowledge(user) | user.is_admin | ACKNOWLEDGED | Registrar timestamp y usuario |
| ACKNOWLEDGED | investigate() | - | INVESTIGATING | Asignar investigador |
| ACKNOWLEDGED | mark_false_positive() | - | FALSE_POSITIVE | Documentar razón |
| ACKNOWLEDGED | resolve(notes) | - | RESOLVED | Guardar resolución |
| INVESTIGATING | resolve(notes) | - | RESOLVED | Guardar resolución, audit log |
| INVESTIGATING | mark_false_positive() | - | FALSE_POSITIVE | Documentar razón |

---

## 4. Reconciliation (Reconciliación)

### Diagrama de Estados

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                      RECONCILIACIÓN - DIAGRAMA DE ESTADOS                            │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌───┐
                                    │ ● │
                                    └─┬─┘
                                      │
                                      │ create_reconciliation(table_id)
                                      │ [multiple_forms_exist]
                                      ▼
                            ┌─────────────────────┐
                            │                     │
                            │    PROVISIONAL      │
                            │                     │
                            │  Reconciliación     │
                            │  automática basada  │
                            │  en confianza OCR   │
                            │                     │
                            │  [selecciona form   │
                            │   con mayor conf.]  │
                            │                     │
                            └──────────┬──────────┘
                                       │
                         ┌─────────────┼─────────────┐
                         │             │             │
                         │             │             │
              dispute(reason)    finalize()     auto_finalize()
                         │             │        [all_forms_match]
                         │             │             │
                         ▼             │             │
            ┌─────────────────────┐    │             │
            │                     │    │             │
            │      DISPUTED       │    │             │
            │                     │    │             │
            │  Discrepancia no    │    │             │
            │  resuelta, requiere │    │             │
            │  intervención       │    │             │
            │                     │    │             │
            └──────────┬──────────┘    │             │
                       │               │             │
                       │ resolve()     │             │
                       │               │             │
                       └───────────────┼─────────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │                     │
                            │       FINAL         │
                            │                     │
                            │  Fuente de verdad   │
                            │  establecida        │
                            │                     │
                            │  [datos usados en   │
                            │   resultados]       │
                            │                     │
                            └──────────┬──────────┘
                                       │
                                       ▼
                                   ┌───────┐
                                   │   ◉   │
                                   └───────┘


═══════════════════════════════════════════════════════════════════════════════════════
                              FLUJO DE RECONCILIACIÓN
═══════════════════════════════════════════════════════════════════════════════════════

    Form A (Witness)          Form B (Official)         Form C (Scraper)
    Confidence: 0.92          Confidence: 0.88          Confidence: 0.75
         │                          │                         │
         └──────────────────────────┼─────────────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  COMPARE & SELECT   │
                         │                     │
                         │  1. Ordenar por     │
                         │     confianza       │
                         │  2. Validar         │
                         │     aritmética      │
                         │  3. Seleccionar     │
                         │     ganador         │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Form A = WINNER    │
                         │  (PROVISIONAL)      │
                         └─────────────────────┘
```

### Tabla de Transiciones

| Estado Actual | Evento | Guarda | Estado Siguiente | Acción |
|---------------|--------|--------|------------------|--------|
| - | create() | multiple_forms | PROVISIONAL | Seleccionar por confianza |
| PROVISIONAL | finalize(admin) | admin_approved | FINAL | Marcar como fuente de verdad |
| PROVISIONAL | auto_finalize() | all_forms_match | FINAL | Verificar coincidencia |
| PROVISIONAL | dispute(reason) | discrepancy_found | DISPUTED | Crear alerta CRITICAL |
| DISPUTED | resolve(winner_id) | admin_decision | FINAL | Aplicar decisión, audit log |

---

## 5. User Session (Sesión de Usuario)

### Diagrama de Estados

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                      SESIÓN DE USUARIO - DIAGRAMA DE ESTADOS                         │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌───┐
                                    │ ● │
                                    └─┬─┘
                                      │
                                      │ login(email, password)
                                      │ [credentials_valid]
                                      ▼
                            ┌─────────────────────┐
                            │                     │
                            │       ACTIVE        │
                            │                     │
                            │  Sesión activa      │
                            │  Token JWT válido   │
                            │                     │
                            │  [access_token      │
                            │   TTL: 1 hora]      │
                            │                     │
                            └──────────┬──────────┘
                                       │
                     ┌─────────────────┼─────────────────┐
                     │                 │                 │
                     │ token_expired() │ logout()        │ invalidate()
                     │                 │                 │ [admin_action]
                     ▼                 │                 │
            ┌─────────────────────┐    │                 │
            │                     │    │                 │
            │      EXPIRED        │    │                 │
            │                     │    │                 │
            │  Access token       │    │                 │
            │  expirado           │    │                 │
            │                     │    │                 │
            │  [puede usar        │    │                 │
            │   refresh_token]    │    │                 │
            │                     │    │                 │
            └──────────┬──────────┘    │                 │
                       │               │                 │
         ┌─────────────┼───────────┐   │                 │
         │             │           │   │                 │
         │ refresh()   │           │   │                 │
         │ [valid]     │ refresh() │   │                 │
         │             │ [invalid] │   │                 │
         ▼             │           │   │                 │
    ┌──────────┐       │           │   │                 │
    │ (ACTIVE) │       │           │   │                 │
    └──────────┘       │           │   │                 │
                       │           │   │                 │
                       └───────────┼───┼─────────────────┘
                                   │   │
                                   ▼   ▼
                            ┌─────────────────────┐
                            │                     │
                            │    INVALIDATED      │
                            │                     │
                            │  Sesión terminada   │
                            │  Requiere re-login  │
                            │                     │
                            └──────────┬──────────┘
                                       │
                                       ▼
                                   ┌───────┐
                                   │   ◉   │
                                   └───────┘


═══════════════════════════════════════════════════════════════════════════════════════
                              DIAGRAMA DE TOKENS
═══════════════════════════════════════════════════════════════════════════════════════

    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                              TIMELINE                                        │
    │                                                                              │
    │  Login         1 hora              Refresh           24 horas               │
    │    │             │                    │                  │                   │
    │    ▼             ▼                    ▼                  ▼                   │
    │    ┌─────────────────────────────────┐                                      │
    │    │      ACCESS TOKEN (1h)          │                                      │
    │    └─────────────────────────────────┘                                      │
    │    ┌─────────────────────────────────────────────────────────────────────┐  │
    │    │                    REFRESH TOKEN (24h)                              │  │
    │    └─────────────────────────────────────────────────────────────────────┘  │
    │                                                                              │
    └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Lead (Prospecto)

### Diagrama de Estados

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           LEAD - DIAGRAMA DE ESTADOS                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌───┐
                                    │ ● │
                                    └─┬─┘
                                      │
                                      │ create_lead(data)
                                      ▼
                            ┌─────────────────────┐
                            │                     │
                            │        NEW          │
                            │                     │
                            │  Lead recién        │
                            │  creado, sin        │
                            │  contactar          │
                            │                     │
                            └──────────┬──────────┘
                                       │
                                       │ contact(notes)
                                       ▼
                            ┌─────────────────────┐
                            │                     │
                            │     CONTACTED       │
                            │                     │
                            │  Primer contacto    │
                            │  realizado          │
                            │                     │
                            └──────────┬──────────┘
                                       │
                         ┌─────────────┼─────────────┐
                         │             │             │
                         │ qualify()   │             │ mark_lost(reason)
                         │             │             │
                         ▼             │             ▼
            ┌─────────────────────┐    │    ┌─────────────────────┐
            │                     │    │    │                     │
            │     QUALIFIED       │    │    │        LOST         │
            │                     │    │    │                     │
            │  Lead calificado    │    │    │  Lead perdido       │
            │  como oportunidad   │    │    │  (sin interés,      │
            │                     │    │    │   competencia, etc) │
            └──────────┬──────────┘    │    │                     │
                       │               │    └──────────┬──────────┘
                       │ convert()     │               │
                       │               │               │
                       ▼               │               │
            ┌─────────────────────┐    │               │
            │                     │    │               │
            │     CONVERTED       │    │               │
            │                     │    │               │
            │  Lead convertido    │    │               │
            │  a cliente          │    │               │
            │                     │    │               │
            └──────────┬──────────┘    │               │
                       │               │               │
                       └───────────────┼───────────────┘
                                       │
                                       ▼
                                   ┌───────┐
                                   │   ◉   │
                                   └───────┘


═══════════════════════════════════════════════════════════════════════════════════════
                              MÉTRICAS DE CONVERSIÓN
═══════════════════════════════════════════════════════════════════════════════════════

    NEW ──────► CONTACTED ──────► QUALIFIED ──────► CONVERTED
     │              │                  │                │
     │   Tasa de    │    Tasa de       │   Tasa de      │
     │   contacto   │    calificación  │   conversión   │
     │              │                  │                │
     └──────────────┴──────────────────┴────────────────┘
            │                │                  │
            ▼                ▼                  ▼
         ~80%             ~40%              ~25%
```

---

## 7. Analysis (Análisis de Campaña)

### Diagrama de Estados

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    ANÁLISIS DE CAMPAÑA - DIAGRAMA DE ESTADOS                         │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌───┐
                                    │ ● │
                                    └─┬─┘
                                      │
                                      │ request_analysis(params)
                                      ▼
                            ┌─────────────────────┐
                            │                     │
                            │     REQUESTED       │
                            │                     │
                            │  Análisis           │
                            │  solicitado         │
                            │                     │
                            └──────────┬──────────┘
                                       │
                                       │ start_processing()
                                       ▼
                            ┌─────────────────────┐
                            │                     │
                            │    PROCESSING       │◄──────────────────────┐
                            │                     │                       │
                            │  ┌───────────────┐  │                       │
                            │  │ 1. Trending   │  │                       │
                            │  │ 2. Tweets     │  │                       │
                            │  │ 3. Sentiment  │  │                       │
                            │  │ 4. Classify   │  │                       │
                            │  │ 5. Generate   │  │                       │
                            │  └───────────────┘  │                       │
                            │                     │                       │
                            └──────────┬──────────┘                       │
                                       │                                  │
                         ┌─────────────┼─────────────┐                    │
                         │             │             │                    │
                         │ success()   │             │ error()            │
                         │             │             │                    │
                         ▼             │             ▼                    │
            ┌─────────────────────┐    │    ┌─────────────────────┐      │
            │                     │    │    │                     │      │
            │     COMPLETED       │    │    │       FAILED        │      │
            │                     │    │    │                     │      │
            │  Análisis completo  │    │    │  Error en API       │      │
            │  con todos los      │    │    │  externa o proceso  │      │
            │  resultados         │    │    │                     │      │
            │                     │    │    └──────────┬──────────┘      │
            │  - Summary          │    │               │                  │
            │  - Strategy         │    │               │ retry()          │
            │  - Speech           │    │               │ [retries < 3]    │
            │  - Charts           │    │               │                  │
            │                     │    │               └──────────────────┘
            └──────────┬──────────┘    │
                       │               │
                       │               │
                       └───────────────┘
                               │
                               ▼
                           ┌───────┐
                           │   ◉   │
                           └───────┘


═══════════════════════════════════════════════════════════════════════════════════════
                              SUBPROCESOS DE ANÁLISIS
═══════════════════════════════════════════════════════════════════════════════════════

┌───────────────────────────────────────────────────────────────────────────────────┐
│                                                                                   │
│    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐      │
│    │Trending │───>│ Tweets  │───>│Sentiment│───>│Classify │───>│Generate │      │
│    │ Topics  │    │ Search  │    │ Analysis│    │   PND   │    │   AI    │      │
│    └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘      │
│         │              │              │              │              │            │
│         ▼              ▼              ▼              ▼              ▼            │
│    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐      │
│    │Twitter  │    │Twitter  │    │  BETO   │    │Keywords │    │ GPT-4o  │      │
│    │  API    │    │  API    │    │  Model  │    │ + Embed │    │ OpenAI  │      │
│    └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘      │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Election (Elección)

### Diagrama de Estados

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         ELECCIÓN - DIAGRAMA DE ESTADOS                               │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌───┐
                                    │ ● │
                                    └─┬─┘
                                      │
                                      │ create_election(data)
                                      ▼
                            ┌─────────────────────┐
                            │                     │
                            │     SCHEDULED       │
                            │                     │
                            │  Elección           │
                            │  programada         │
                            │                     │
                            │  [fecha futura]     │
                            │                     │
                            └──────────┬──────────┘
                                       │
                         ┌─────────────┼─────────────┐
                         │             │             │
                         │ start()     │             │ cancel(reason)
                         │ [date=today]│             │
                         ▼             │             ▼
            ┌─────────────────────┐    │    ┌─────────────────────┐
            │                     │    │    │                     │
            │    IN_PROGRESS      │    │    │     CANCELLED       │
            │                     │    │    │                     │
            │  Elección en        │    │    │  Elección           │
            │  curso              │    │    │  cancelada          │
            │                     │    │    │                     │
            │  [recibiendo        │    │    └──────────┬──────────┘
            │   formularios]      │    │               │
            │                     │    │               │
            └──────────┬──────────┘    │               │
                       │               │               │
                       │ complete()    │               │
                       │ [voting_ended]│               │
                       ▼               │               │
            ┌─────────────────────┐    │               │
            │                     │    │               │
            │     COMPLETED       │    │               │
            │                     │    │               │
            │  Elección           │    │               │
            │  finalizada         │    │               │
            │                     │    │               │
            │  [resultados        │    │               │
            │   publicados]       │    │               │
            │                     │    │               │
            └──────────┬──────────┘    │               │
                       │               │               │
                       └───────────────┼───────────────┘
                                       │
                                       ▼
                                   ┌───────┐
                                   │   ◉   │
                                   └───────┘
```

---

## 9. Circuit Breaker (Patrón de Resiliencia)

### Diagrama de Estados

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     CIRCUIT BREAKER - DIAGRAMA DE ESTADOS                            │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌───┐
                                    │ ● │
                                    └─┬─┘
                                      │
                                      │ initialize()
                                      ▼
                  ┌─────────────────────────────────────────┐
                  │                                         │
                  │               CLOSED                    │◄─────────────────┐
                  │                                         │                  │
                  │  Circuito cerrado - operación normal    │                  │
                  │                                         │                  │
                  │  [todas las llamadas pasan]             │                  │
                  │  [failure_count se monitorea]           │                  │
                  │                                         │                  │
                  └────────────────────┬────────────────────┘                  │
                                       │                                       │
                                       │ failure()                             │
                                       │ [failure_count >= threshold]          │
                                       │ [threshold = 5]                       │
                                       ▼                                       │
                  ┌─────────────────────────────────────────┐                  │
                  │                                         │                  │
                  │                OPEN                     │                  │
                  │                                         │                  │
                  │  Circuito abierto - bloquea llamadas    │                  │
                  │                                         │                  │
                  │  [retorna error inmediatamente]         │                  │
                  │  [protege el sistema]                   │                  │
                  │                                         │                  │
                  └────────────────────┬────────────────────┘                  │
                                       │                                       │
                                       │ timeout()                             │
                                       │ [recovery_timeout = 30s]              │
                                       ▼                                       │
                  ┌─────────────────────────────────────────┐                  │
                  │                                         │                  │
                  │             HALF_OPEN                   │                  │
                  │                                         │                  │
                  │  Prueba de recuperación                 │                  │
                  │                                         │                  │
                  │  [permite una llamada de prueba]        │                  │
                  │                                         │                  │
                  └────────────────────┬────────────────────┘                  │
                                       │                                       │
                         ┌─────────────┴─────────────┐                         │
                         │                           │                         │
                         │ success()                 │ failure()               │
                         │                           │                         │
                         │                           ▼                         │
                         │              ┌────────────────────┐                 │
                         │              │      (OPEN)        │                 │
                         │              └────────────────────┘                 │
                         │                                                     │
                         └─────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════════════
                              TIMELINE DE CIRCUIT BREAKER
═══════════════════════════════════════════════════════════════════════════════════════

    Normal      5 failures     Timeout 30s      Test         Success
       │            │              │              │              │
       ▼            ▼              ▼              ▼              ▼
    ┌──────────────────┐  ┌──────────────────┐  ┌────┐  ┌──────────────────┐
    │     CLOSED       │  │      OPEN        │  │HALF│  │     CLOSED       │
    │  ████████████    │  │  ░░░░░░░░░░░░    │  │OPEN│  │  ████████████    │
    │  Requests pass   │  │  Requests fail   │  │    │  │  Requests pass   │
    └──────────────────┘  └──────────────────┘  └────┘  └──────────────────┘
```

---

## 10. Resumen de Estados por Entidad

| Entidad | Estados | Transiciones | Estado Inicial | Estados Finales |
|---------|---------|--------------|----------------|-----------------|
| **FormInstance** | 6 | 10 | PENDING | VALIDATED, FAILED |
| **Alert** | 5 | 6 | OPEN | RESOLVED, FALSE_POSITIVE |
| **Reconciliation** | 3 | 5 | PROVISIONAL | FINAL |
| **User Session** | 4 | 5 | ACTIVE | INVALIDATED |
| **Lead** | 5 | 5 | NEW | CONVERTED, LOST |
| **Analysis** | 4 | 5 | REQUESTED | COMPLETED, FAILED |
| **Election** | 4 | 4 | SCHEDULED | COMPLETED, CANCELLED |
| **CircuitBreaker** | 3 | 4 | CLOSED | - (cíclico) |

---

## 11. Matriz de Estados y Eventos

### FormInstance

```
                          EVENTOS
              ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
              │ upload  │start_ocr│ocr_ok   │ocr_fail │approve  │validate │
    ┌─────────┼─────────┼─────────┼─────────┼─────────┼─────────┼─────────┤
    │    -    │ PENDING │    -    │    -    │    -    │    -    │    -    │
E   │ PENDING │    -    │PROCESSING   -    │    -    │    -    │    -    │
S   │PROCESSING   -    │    -    │COMPLETED│ FAILED  │    -    │    -    │
T   │COMPLETED│    -    │    -    │    -    │    -    │    -    │VALIDATED│
A   │NEEDS_REV│    -    │    -    │    -    │    -    │VALIDATED│    -    │
D   │ FAILED  │ PENDING*│    -    │    -    │    -    │    -    │    -    │
O   │VALIDATED│    -    │    -    │    -    │    -    │    -    │    -    │
    └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘

    * Con retry() si retry_count < 3
```

### Alert

```
                          EVENTOS
              ┌─────────┬─────────┬─────────┬─────────┬─────────┐
              │ create  │   ack   │investig.│ resolve │false_pos│
    ┌─────────┼─────────┼─────────┼─────────┼─────────┼─────────┤
    │    -    │  OPEN   │    -    │    -    │    -    │    -    │
E   │  OPEN   │    -    │  ACK    │    -    │    -    │    -    │
S   │  ACK    │    -    │    -    │ INVEST. │RESOLVED │FALSE_POS│
T   │ INVEST. │    -    │    -    │    -    │RESOLVED │FALSE_POS│
A   │RESOLVED │    -    │    -    │    -    │    -    │    -    │
D   │FALSE_POS│    -    │    -    │    -    │    -    │    -    │
O   └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘
```

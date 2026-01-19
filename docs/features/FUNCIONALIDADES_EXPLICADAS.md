# FUNCIONALIDADES_EXPLICADAS.md

## 0) Visión general
CASTOR ELECCIONES expone tres productos principales que comparten una base de análisis común:

- **MEDIOS (Media Analysis)**: análisis neutral para prensa y observatorios.
- **CAMPAÑA (Campaign Agent)**: estrategias para ganar votos con lenguaje estratégico.
- **FORECAST (Pronóstico Electoral)**: métricas y proyecciones de conversación narrativa.

Todos los flujos parten de **inputs del usuario** (ubicación, tema, candidato, etc.) y producen **outputs de analytics** (sentimiento, temas, métricas ICCE/Momentum, forecast, etc.).

---

## 1) Componentes y servicios (mapa técnico)

### Backend (Flask)
- **App factory**: `backend/app/__init__.py`
- **Rutas**:
  - Medios: `backend/app/routes/media.py`
  - Campaña: `backend/app/routes/campaign.py`
  - Forecast: `backend/app/routes/forecast.py`
  - Salud/diagnóstico: `backend/app/routes/health.py`
  - Web: `backend/app/routes/web.py`

### Servicios principales
- **TwitterService**: `backend/services/twitter_service.py`
- **SentimentService**: `backend/services/sentiment_service.py`
- **TrendingService**: `backend/services/trending_service.py`
- **OpenAIService**: `backend/services/openai_service.py`
- **DatabaseService**: `backend/services/database_service.py`
- **AnalysisCorePipeline**: `backend/app/services/analysis_core.py`
- **ForecastService**: `backend/app/services/forecast_service.py`

### Utilidades
- **Rate limiter**: `backend/utils/rate_limiter.py`
- **Cache**: `backend/utils/cache.py`
- **Validaciones**: `backend/utils/validators.py`

---

## 2) Funcionalidad: MEDIOS (Media Analysis)

### 2.1 Propósito
Análisis neutral y descriptivo de la conversación pública para prensa y observatorios.

### 2.2 Inputs del usuario
Endpoint: `POST /api/media/analyze`

Parámetros clave:
- `location` (obligatorio)
- `topic` (opcional)
- `candidate_name` (opcional)
- `politician` (opcional)
- `max_tweets` (opcional, default 15)
- `time_window_days` (opcional, default 7)
- `language` (opcional, default es)

### 2.3 Flujo detallado
1) **Validación** con Pydantic: `MediaAnalysisRequest`.
2) **Core pipeline**: `AnalysisCorePipeline.run_core_pipeline(...)`.
3) **Extracción de tweets**: `TwitterService.search_tweets(...)`.
4) **Sentimiento** (BETO) por tweet: `SentimentService.analyze_tweets(...)`.
5) **Clasificación por temas**: `TopicClassifierService.classify_tweets_by_pnd_topic(...)`.
6) **Resumen GPT**: `OpenAIService.generate_media_summary(...)`.
7) **Chart data**: `ChartService.build_media_charts(...)`.
8) **Respuesta**: `MediaAnalysisResponse`.

### 2.4 Outputs
- `summary.overview`
- `summary.key_stats`
- `summary.key_findings`
- `sentiment_overview`
- `topics` (lista de temas + conteos)
- `peaks` (picos si aplica)
- `chart_data` (Chart.js)
- `metadata` (ventanas de tiempo, query, trending topic)

### 2.5 Ejemplo request
```json
POST /api/media/analyze
{
  "location": "Bogota",
  "topic": "Seguridad",
  "candidate_name": "Juan Perez",
  "politician": "@juanperez",
  "max_tweets": 15,
  "time_window_days": 7,
  "language": "es"
}
```

### 2.6 Ejemplo response (parcial)
```json
{
  "success": true,
  "summary": {
    "overview": "La conversacion ciudadana...",
    "key_stats": ["120 menciones", "65% positivo"],
    "key_findings": ["Se intensifica el tema X", "Aumento en Y"]
  },
  "sentiment_overview": {"positive": 0.41, "neutral": 0.36, "negative": 0.23},
  "topics": [{"topic": "Seguridad", "tweet_count": 64, "sentiment": {"positive": 0.4, "neutral": 0.35, "negative": 0.25}}],
  "chart_data": {"by_topic_sentiment": {}, "volume_over_time": {}},
  "metadata": {"tweets_analyzed": 15, "location": "Bogota"}
}
```

---

## 3) Funcionalidad: CAMPAÑA (Campaign Agent)

### 3.1 Propósito
Generar estrategias para ganar votos basadas en señales narrativas y conversación ciudadana.

### 3.2 Inputs del usuario
Endpoint: `POST /api/campaign/analyze`

Parámetros clave:
- `location` (obligatorio)
- `theme` (obligatorio)
- `candidate_name` (opcional)
- `politician` (opcional)
- `max_tweets` (opcional, default 120)
- `language` (opcional)

### 3.3 Flujo detallado
1) **Validación** con `CampaignAnalysisRequest`.
2) **Core pipeline** (igual que medios).
3) **Adaptación a esquema legacy** para prompts GPT.
4) **OpenAIService**:
   - `generate_executive_summary(...)`
   - `generate_strategic_plan(...)`
   - `generate_speech(...)`
5) **Chart data** incluido en respuesta.

### 3.4 Outputs
- `executive_summary` (overview + hallazgos + recomendaciones)
- `strategic_plan` (objetivos + acciones + impacto)
- `speech` (discurso sugerido)
- `topic_analyses` (temas y sentimiento)
- `chart_data` (Chart.js)
- `metadata` (incluye `trending_topic` y `raw_query`)

### 3.5 Ejemplo request
```json
POST /api/campaign/analyze
{
  "location": "Bogota",
  "theme": "Seguridad",
  "candidate_name": "Juan Perez",
  "politician": "@juanperez",
  "max_tweets": 120,
  "language": "es"
}
```

### 3.6 Ejemplo response (parcial)
```json
{
  "success": true,
  "executive_summary": {"overview": "...", "key_findings": ["..."], "recommendations": ["..."]},
  "strategic_plan": {"objectives": ["..."], "actions": [{"action": "..."}]},
  "speech": {"title": "...", "content": "..."},
  "topic_analyses": [{"topic": "Seguridad", "tweet_count": 80, "sentiment": {"positive": 0.45, "neutral": 0.35, "negative": 0.2}}],
  "metadata": {"location": "Bogota", "theme": "Seguridad"}
}
```

---

## 4) Funcionalidad: FORECAST (Pronostico Electoral)

### 4.1 Propósito
Calcular métricas narrativas y proyectar la conversación en el corto plazo.

### 4.2 Inputs del usuario
Endpoints:
- `POST /api/forecast/icce`
- `POST /api/forecast/momentum`
- `POST /api/forecast/forecast`
- `POST /api/forecast/dashboard`

Parámetros comunes:
- `location` (obligatorio)
- `candidate_name` (opcional)
- `politician` (opcional)
- `days_back` (opcional, default 30)
- `forecast_days` (opcional, default 14)

### 4.3 Fórmulas matemáticas (simplificadas)

**ICCE (0-100)**
- `ICCE = 0.5 * SentimentScore + 0.5 * VolumeScore`
- `SentimentScore` normalizado [0, 100]
- `VolumeScore` normalizado [0, 100]

**Momentum**
- `Momentum(t) = EMA(ICCE(t) - ICCE(t-1))`
- Suavizado con promedio movil exponencial para evitar ruido.

**Forecast**
- Modelo de proyeccion por defecto: **Holt-Winters**
- Produccion de intervalos: `pred_low`, `pred_high`

### 4.4 Flujo detallado
1) **Historico ICCE** con `ForecastService.calculate_icce(...)`.
2) **Momentum** con `ForecastService.calculate_momentum(...)`.
3) **Suavizado** con `ForecastService.calculate_ema_smooth(...)`.
4) **Proyeccion** con `ForecastService.forecast_icce(...)`.
5) **Dashboard** combina todo en un response unificado.

### 4.5 Output
- Serie historica ICCE (0-100)
- Momentum diario
- Forecast con intervalos
- Metadata: modelo y ventana temporal

### 4.6 Ejemplo request
```json
POST /api/forecast/dashboard
{
  "location": "Bogota",
  "candidate_name": "Juan Perez",
  "days_back": 30,
  "forecast_days": 14
}
```

### 4.7 Ejemplo response (parcial)
```json
{
  "success": true,
  "candidate": "juanperez",
  "location": "Bogota",
  "series": {
    "dates": ["2024-01-01", "2024-01-02"],
    "icce": [0.52, 0.57],
    "icce_smooth": [0.51, 0.55],
    "momentum": [0.0, 0.03]
  },
  "forecast": {
    "dates": ["2024-01-03", "2024-01-04"],
    "icce_pred": [0.58, 0.60],
    "pred_low": [0.53, 0.55],
    "pred_high": [0.62, 0.66]
  },
  "metadata": {"model_type": "holt_winters"}
}
```

---

## 5) Comparacion entre funcionalidades

| Dimension | Medios | Campana | Forecast |
| --- | --- | --- | --- |
| Propósito | Neutral / prensa | Estrategia política | Métricas y proyección |
| Inputs clave | location, topic | location, theme | location, days_back |
| Output | resumen + sentimiento | plan + discurso | ICCE + momentum + forecast |
| GPT | Resumen descriptivo | Estrategia + discurso | No necesariamente |
| Frecuencia | Diario / semanal | Semanal / campaña | Diario / continuo |

---

## 6) Relacion Inputs → Outputs

1) **Usuario define inputs** (location, tema, candidato, ventana temporal).
2) **Sistema recolecta tweets** y calcula sentimiento y temas.
3) **Outputs** se renderizan en dashboard (resumen, sentimiento, métricas, forecast).

---

## 7) Dashboard unificado (Power BI style)

El dashboard unificado consolida:
- **KPIs**: ICCE, Momentum, Sentimiento neto, Volumen.
- **Flujos**: Medios, Campana, Forecast en tarjetas separadas.
- **Geografia**: mapa sintetico con top ciudades.

Ruta web:
- `GET /dashboard` -> `templates/unified_dashboard.html`

Script frontend:
- `static/js/unified_dashboard.js`


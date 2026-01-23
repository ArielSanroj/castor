# CASTOR ELECCIONES - API Documentation

## Base URL
```
http://localhost:5001/api
```

---

## 1. Health & Status

### GET /health
Health check del servicio.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-01-23T12:00:00Z"
}
```

### GET /twitter-usage
Uso actual de la API de Twitter.

**Response:**
```json
{
  "success": true,
  "plan": "Basic Tier (500/day, 15K/month)",
  "stats": {
    "today": {
      "used": 398,
      "limit": 500,
      "remaining": 102,
      "percentage": 79.6,
      "api_calls": 6
    },
    "month": {
      "used": 398,
      "limit": 15000,
      "remaining": 14602,
      "percentage": 2.7
    }
  },
  "total_tweets_in_db": 504
}
```

---

## 2. Análisis de Medios

### POST /media/analyze
Ejecuta un análisis de tweets para un candidato.

**Request Body:**
```json
{
  "candidate_name": "Abelardo de la Espriella",
  "location": "Colombia",
  "topic": "seguridad",
  "max_tweets": 100,
  "time_window_days": 7,
  "language": "es"
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "tweets_analyzed": 100,
    "location": "Colombia",
    "sentiment_overview": {
      "positive": 0.45,
      "neutral": 0.30,
      "negative": 0.25
    },
    "topics": [...],
    "narrative_metrics": {
      "icce": 65.5,
      "sov": 12.3,
      "sna": 15.7,
      "momentum": 0.05
    }
  }
}
```

### GET /media/history
Lista de análisis completados con datos.

**Query Parameters:**
- `limit` (optional): Número máximo de resultados (default: 20)
- `candidate` (optional): Filtrar por candidato
- `location` (optional): Filtrar por ubicación

**Response:**
```json
{
  "success": true,
  "count": 4,
  "api_calls": [
    {
      "id": "uuid",
      "candidate_name": "Abelardo de la Espriella",
      "location": "Colombia",
      "tweets_retrieved": 292,
      "pnd_metrics_count": 10,
      "fetched_at": "2026-01-23T00:35:07Z",
      "status": "completed"
    }
  ]
}
```

### GET /media/analysis/{api_call_id}
Detalle completo de un análisis.

**Response:**
```json
{
  "success": true,
  "api_call_id": "uuid",
  "candidate_name": "Abelardo de la Espriella",
  "tweetsCount": 292,
  "mediaData": {
    "topics": [...],
    "sentiment_overview": {...}
  },
  "analysisSnapshot": {
    "icce": 50.3,
    "sov": 73.0,
    "sna": -5.2,
    "momentum": 0.018
  },
  "pndMetrics": [...],
  "tweets": [...]
}
```

### GET /media/tweets/{api_call_id}
Tweets de un análisis específico.

**Query Parameters:**
- `limit` (optional): Máximo de tweets (default: 500)
- `offset` (optional): Offset para paginación

**Response:**
```json
{
  "success": true,
  "api_call_id": "uuid",
  "count": 100,
  "tweets": [
    {
      "tweet_id": "123456",
      "author_username": "usuario",
      "content": "texto del tweet",
      "sentiment_label": "positivo",
      "pnd_topic": "seguridad",
      "retweet_count": 10,
      "like_count": 25
    }
  ]
}
```

---

## 3. Chat RAG

### POST /chat/rag
Pregunta al sistema RAG basado en los datos indexados.

**Request Body:**
```json
{
  "message": "¿Qué dicen sobre Abelardo en temas de seguridad?",
  "conversation_id": "optional-uuid"
}
```

**Response:**
```json
{
  "success": true,
  "answer": "Basado en los tweets analizados...",
  "conversation_id": "uuid",
  "documents_retrieved": 5,
  "sources": [
    {
      "id": "doc_id",
      "type": "tweets",
      "preview": "TWEETS SOBRE SEGURIDAD...",
      "score": 0.85,
      "location": "Colombia",
      "date": "2026-01-23"
    }
  ]
}
```

### GET /chat/rag/stats
Estadísticas del sistema RAG.

**Response:**
```json
{
  "success": true,
  "documents_indexed": 1050,
  "embedding_model": "text-embedding-3-small",
  "generation_model": "gpt-4o"
}
```

### POST /chat/rag/search
Búsqueda semántica en documentos indexados.

**Request Body:**
```json
{
  "query": "seguridad ciudadana Colombia",
  "top_k": 5
}
```

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "content": "...",
      "metadata": {...},
      "score": 0.87
    }
  ]
}
```

### POST /chat/rag/sync-latest
Sincroniza el RAG con el último análisis en BD.

**Response:**
```json
{
  "success": true,
  "message": "Sincronizado con análisis de X",
  "documents_synced": 15,
  "total_indexed": 1050
}
```

---

## 4. Forecast

### POST /forecast/predict
Genera predicción electoral.

**Request Body:**
```json
{
  "candidate_name": "Abelardo de la Espriella",
  "location": "Colombia",
  "days_ahead": 30
}
```

**Response:**
```json
{
  "success": true,
  "forecast": {
    "current_icce": 65.5,
    "predicted_icce": 68.2,
    "confidence": 0.75,
    "trend": "up",
    "factors": [...]
  }
}
```

---

## Códigos de Error

| Código | Descripción |
|--------|-------------|
| 200 | Éxito |
| 400 | Bad Request - Parámetros inválidos |
| 404 | Not Found - Recurso no encontrado |
| 429 | Rate Limit - Límite de API excedido |
| 500 | Internal Server Error |

## Rate Limits

- **Twitter API**: 500 tweets/día, 15,000 tweets/mes
- **Chat RAG**: Sin límite (depende de OpenAI)
- Reset diario: 00:00 UTC (7:00 PM Colombia)

---

## Autenticación

Actualmente el API es público. Para producción, agregar:

```
Authorization: Bearer <token>
```

---

## Ejemplos con cURL

### Analizar candidato
```bash
curl -X POST http://localhost:5001/api/media/analyze \
  -H "Content-Type: application/json" \
  -d '{"candidate_name": "Abelardo", "location": "Colombia", "max_tweets": 50}'
```

### Preguntar al RAG
```bash
curl -X POST http://localhost:5001/api/chat/rag \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Cuál es el sentimiento general?"}'
```

### Ver histórico
```bash
curl http://localhost:5001/api/media/history
```

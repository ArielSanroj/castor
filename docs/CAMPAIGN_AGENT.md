# 🤖 Agente de Campaña - CASTOR ELECCIONES

## ¿Qué hace el Agente de Campaña?

El **Agente de Campaña** es un sistema de IA que:

1. **Analiza qué gana votos** - Entiende qué estrategias funcionan mejor
2. **Detecta trending topics** - Lee en tiempo real lo que está pasando
3. **Genera discursos alineados** - Crea discursos basados en lo trending del momento
4. **Recolecta firmas** - Estrategias para conseguir firmas digitales
5. **Aprende de acciones pasadas** - Analiza qué funcionó y qué no

## 🎯 Funcionalidades Principales

### 1. Análisis de Qué Gana Votos

**Endpoint**: `POST /api/campaign/analyze-votes`

Analiza qué estrategias ganan votos en una ubicación específica.

**Request**:
```json
{
  "location": "Bogotá",
  "candidate_name": "Juan Pérez"
}
```

**Response**:
```json
{
  "success": true,
  "location": "Bogotá",
  "candidate_name": "Juan Pérez",
  "trending_topics": ["Seguridad", "Educación", "Salud"],
  "strategies": [
    {
      "strategy_name": "Enfoque en Seguridad",
      "description": "Estrategia detallada...",
      "key_messages": ["Mensaje 1", "Mensaje 2"],
      "channels": ["Twitter", "Facebook", "Eventos"],
      "timing": "Inmediato",
      "target_demographic": "Jóvenes 18-35",
      "predicted_votes": 1500,
      "confidence_score": 0.85,
      "risk_level": "medio"
    }
  ],
  "vote_predictions": {
    "total_predicted": 5000,
    "best_strategy": "Enfoque en Seguridad"
  },
  "key_insights": [
    "El tema más trending es 'Seguridad'...",
    "La acción más exitosa fue..."
  ],
  "recommendations": [
    "Estrategia recomendada: ...",
    "Ejecutar en los próximos 7 días..."
  ]
}
```

### 2. Detección de Trending Topics

**Endpoint**: `GET /api/campaign/trending?location=Bogotá`

Detecta qué está trending en tiempo real.

**Response**:
```json
{
  "success": true,
  "location": "Bogotá",
  "trending_topics": [
    {
      "topic": "#SeguridadBogotá",
      "tweet_count": 250,
      "engagement_score": 5000,
      "sentiment_positive": 0.45,
      "sentiment_negative": 0.35,
      "sentiment_neutral": 0.20,
      "keywords": ["seguridad", "delincuencia", "policía"],
      "sample_tweets": ["Tweet 1...", "Tweet 2..."]
    }
  ]
}
```

### 3. Recolección de Firmas

**Endpoint**: `POST /api/campaign/signatures/collect`

Recolecta una firma digital para una campaña.

**Request**:
```json
{
  "campaign_id": "campaign-123",
  "signer_name": "María García",
  "signer_email": "maria@example.com",
  "signer_phone": "+573001234567",
  "signer_id_number": "1234567890",
  "location": "Bogotá"
}
```

**Response**:
```json
{
  "success": true,
  "signature_id": "uuid-123",
  "current_signatures": 150,
  "message": "Signature collected successfully"
}
```

**Endpoint**: `GET /api/campaign/signatures/{campaign_id}/count`

Obtiene el conteo de firmas.

**Endpoint**: `POST /api/campaign/signatures/strategy`

Genera estrategia para recolectar firmas.

**Request**:
```json
{
  "campaign_id": "campaign-123",
  "location": "Bogotá",
  "target_signatures": 1000
}
```

**Response**:
```json
{
  "success": true,
  "current_signatures": 150,
  "target": 1000,
  "remaining": 850,
  "strategy": {
    "channels": ["Redes sociales", "WhatsApp", "Eventos presenciales"],
    "key_messages": ["Tu firma cuenta", "Juntos por el cambio"],
    "timing": "Próximos 7 días",
    "incentives": ["Incentivo 1", "Incentivo 2"]
  },
  "recommendations": [
    "Usar múltiples canales para recolección",
    "Enfocarse en mensajes: Tu firma cuenta, Juntos por el cambio",
    "Ejecutar en: Próximos 7 días"
  ]
}
```

## 🧠 Cómo Funciona

### 1. Detección de Trending Topics

El sistema:
- Busca tweets recientes en la ubicación
- Extrae keywords y hashtags
- Agrupa tweets por tema
- Calcula engagement (likes + retweets + replies)
- Analiza sentimiento (positivo/negativo/neutral)
- Identifica los temas más relevantes

### 2. Análisis de Qué Gana Votos

El agente:
- Analiza trending topics (qué preocupa a la gente AHORA)
- Revisa acciones exitosas pasadas (qué funcionó antes)
- Calcula patrones de sentimiento
- Genera estrategias usando GPT-4o
- Predice votos por estrategia
- Calcula ROI y riesgo

### 3. Generación de Discursos

Los discursos ahora:
- **Se alinean con trending topics** - Mencionan lo que está trending
- **Conectan con el momento** - Usan lenguaje que resuena AHORA
- **Se posicionan estratégicamente** - Toman posición sobre temas trending
- **Son relevantes** - Hablan de lo que la gente está discutiendo

### 4. Recolección de Firmas

El sistema:
- Valida que el email no haya firmado antes
- Guarda información del firmante
- Genera estrategias para conseguir más firmas
- Calcula progreso hacia meta
- Proporciona recomendaciones

## 📊 Base de Datos

### Tablas Principales

1. **trending_topics** - Temas trending detectados
2. **speeches** - Discursos generados
3. **signatures** - Firmas recolectadas
4. **campaign_actions** - Acciones de campaña y efectividad
5. **vote_strategies** - Estrategias para ganar votos

## 🚀 Uso

### Inicializar Base de Datos

```bash
cd backend
python init_db.py
```

### Ejemplo de Uso Completo

```python
# 1. Analizar qué gana votos
POST /api/campaign/analyze-votes
{
  "location": "Bogotá",
  "candidate_name": "Juan Pérez"
}

# 2. Ver trending topics
GET /api/campaign/trending?location=Bogotá

# 3. Generar análisis (incluye discurso alineado con trending)
POST /api/analyze
{
  "location": "Bogotá",
  "theme": "Seguridad",
  "candidate_name": "Juan Pérez"
}

# 4. Recolectar firmas
POST /api/campaign/signatures/collect
{
  "campaign_id": "campaign-123",
  "signer_name": "María García",
  "signer_email": "maria@example.com"
}

# 5. Obtener estrategia para más firmas
POST /api/campaign/signatures/strategy
{
  "campaign_id": "campaign-123",
  "location": "Bogotá",
  "target_signatures": 1000
}
```

## 🎯 Ventajas

1. **Tiempo Real** - Lee lo que está pasando AHORA
2. **Estrategias Basadas en Datos** - No adivina, analiza
3. **Aprende** - Mejora con cada acción
4. **Predice Votos** - Estima impacto de estrategias
5. **Recolecta Firmas** - Sistema completo de firmas digitales

---

**El Agente de Campaña hace que CASTOR ELECCIONES sea verdaderamente inteligente: lee el momento, entiende qué funciona, y genera estrategias ganadoras.**


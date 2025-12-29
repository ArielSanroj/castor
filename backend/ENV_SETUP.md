# Configuración de Variables de Entorno

Este documento describe las variables de entorno necesarias para ejecutar CASTOR ELECCIONES, incluyendo los nuevos timeouts configurables.

## Variables Requeridas

### Flask Configuration
```bash
SECRET_KEY=dev-secret-key-change-in-production  # Cambiar en producción
DEBUG=True
HOST=0.0.0.0
PORT=5001
```

### CORS
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:5000
```

### JWT
```bash
JWT_SECRET_KEY=dev-jwt-secret-key-change-in-production  # Cambiar en producción
JWT_ACCESS_TOKEN_EXPIRES=3600
```

### Twitter API (Tweepy)
```bash
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here
TWITTER_API_KEY=your_twitter_api_key_here
TWITTER_API_SECRET=your_twitter_api_secret_here
TWITTER_ACCESS_TOKEN=your_twitter_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret_here
TWITTER_TIMEOUT_SECONDS=15  # Timeout en segundos para llamadas a Twitter API
```

### OpenAI
```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
OPENAI_TIMEOUT_SECONDS=15  # Timeout en segundos para llamadas a OpenAI API
```

### Database (PostgreSQL)
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/castor_elecciones
```

### Twilio WhatsApp (Opcional)
```bash
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+34637909472
TWILIO_CONTENT_SID=HX899df0cc78b682c1a96c5bc83c5b4d3b
```

### BETO Model
```bash
BETO_MODEL_PATH=dccuchile/bert-base-spanish-wwm-uncased
```

### Rate Limiting
```bash
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_STORAGE_URI=memory://
```

### Caching
```bash
CACHE_MAX_SIZE=64
SENTIMENT_CACHE_TTL=900
OPENAI_CACHE_TTL=1800
TRENDING_CACHE_TTL=600
TRENDING_CACHE_STALE_TTL=300
```

### Redis (Opcional - fallback a memoria si no está configurado)
```bash
REDIS_URL=redis://localhost:6379/0
```

### Cache TTLs (Optimizado para Twitter Free tier - 100 posts/month)
```bash
CACHE_TTL_TWITTER=86400
CACHE_TTL_SENTIMENT=86400
CACHE_TTL_OPENAI=43200
CACHE_TTL_TRENDING=21600
```

### Twitter Free Tier Limits
```bash
TWITTER_MAX_TWEETS_PER_REQUEST=15
TWITTER_DAILY_TWEET_LIMIT=3
TWITTER_MONTHLY_LIMIT=100
```

### Logging
```bash
LOG_LEVEL=INFO
LOG_FILE=
```

## Nuevos Timeouts Configurables

Se han añadido dos nuevas variables de entorno para controlar los timeouts de las APIs externas:

- **`OPENAI_TIMEOUT_SECONDS`**: Timeout para llamadas a la API de OpenAI (default: 15 segundos)
- **`TWITTER_TIMEOUT_SECONDS`**: Timeout para llamadas a la API de Twitter (default: 15 segundos)

### Recomendaciones

- **Desarrollo**: 15-30 segundos es suficiente
- **Producción**: 15-20 segundos para balancear entre tiempo de respuesta y tolerancia a latencia
- **Entornos con latencia alta**: Considera aumentar a 30-60 segundos

### Ejemplo de Configuración

```bash
# Para desarrollo local
OPENAI_TIMEOUT_SECONDS=15
TWITTER_TIMEOUT_SECONDS=15

# Para producción con conexión estable
OPENAI_TIMEOUT_SECONDS=20
TWITTER_TIMEOUT_SECONDS=20

# Para entornos con alta latencia
OPENAI_TIMEOUT_SECONDS=30
TWITTER_TIMEOUT_SECONDS=30
```

## Verificación

Después de configurar las variables de entorno, puedes verificar que todo esté correcto ejecutando:

```bash
# Verificar arranque en desarrollo
python backend/run.py

# Verificar health check
curl http://localhost:5001/api/health
```

El endpoint `/api/health` ahora incluye checks de:
- Base de datos
- Redis (si está configurado)
- Estado de circuit breakers (OpenAI y Twitter)




# 🐦 Twitter Free Tier Configuration

## Optimización para 100 Posts/Mes

Castor Elecciones está configurado para funcionar con el **Twitter API Free Tier** (100 posts por mes).

---

## 📊 Límites Actuales

### **Twitter API Free Tier**
- 🔢 **100 posts/mes** total
- 📅 **~3 posts/día** (100/30 días)
- ⏱️ **15 tweets máximo** por análisis
- 🔄 **Caché de 24 horas** para queries repetidas

### **Límites por Request**
- Mínimo: 5 tweets
- Máximo: 20 tweets
- Predeterminado: 15 tweets

---

## 🔍 Monitoreo de Uso

### **Ver Uso Actual**
```bash
curl http://localhost:5001/api/twitter-usage
```

Respuesta:
```json
{
  "plan": "Free Tier (100 posts/month)",
  "stats": {
    "today": {
      "used": 0,
      "limit": 3,
      "remaining": 3,
      "percentage": 0.0
    },
    "month": {
      "used": 0,
      "limit": 100,
      "remaining": 100,
      "percentage": 0.0
    },
    "month_start": "2025-11-01T00:00:00"
  }
}
```

---

## ⚙️ Configuración (`.env`)

```bash
# Twitter Free Tier Optimization
CACHE_TTL_TWITTER=86400              # 24 horas (conservar rate limit)
CACHE_TTL_SENTIMENT=86400            # 24 horas
CACHE_TTL_OPENAI=43200               # 12 horas
CACHE_TTL_TRENDING=21600             # 6 horas
TWITTER_MAX_TWEETS_PER_REQUEST=15    # Máximo por análisis
TWITTER_DAILY_TWEET_LIMIT=3          # Límite diario recomendado
```

---

## 📈 Estrategia de Uso

### **Buenas Prácticas**

1. **Reutilizar Análisis**
   - El caché dura 24 horas
   - Evita repetir queries similares el mismo día

2. **Limitar Análisis Diarios**
   - Máximo 1-2 análisis por día (3 tweets cada uno)
   - Planificar análisis importantes

3. **Combinar Locations**
   - Analizar múltiples temas en una sola query cuando sea posible

4. **Usar Trending Conservadoramente**
   - El servicio de trending también consume del límite

### **Ejemplo de Uso Mensual**

```
Semana 1: 3 análisis × 15 tweets = 45 tweets
Semana 2: 2 análisis × 15 tweets = 30 tweets  
Semana 3: 1 análisis × 15 tweets = 15 tweets
Semana 4: 1 análisis × 10 tweets = 10 tweets
--------------
Total: 100 tweets ✅
```

---

## 🚨 Errores Comunes

### **429 Too Many Requests**
```
Error: 429 Too Many Requests
```
**Solución**: Espera 15-60 minutos o hasta el siguiente día.

### **Daily Limit Reached**
```
Daily limit reached (3/3). Try again tomorrow.
```
**Solución**: Espera hasta el día siguiente (reseteo UTC).

### **Monthly Limit Reached**
```
Monthly limit reached (100/100).
```
**Solución**: 
- Espera hasta el siguiente mes
- Upgrade a plan de pago ($100/mes = 10,000 tweets)

---

## 📁 Archivos de Tracking

El sistema guarda el uso en:
```
/tmp/twitter_usage.json
```

Formato:
```json
{
  "daily": {
    "2025-11-28": 3,
    "2025-11-27": 2
  },
  "monthly_total": 45,
  "month_start": "2025-11-01T00:00:00"
}
```

---

## 🔧 Código Relevante

### **Rate Tracker**
`/backend/utils/twitter_rate_tracker.py`

### **Twitter Service con Límites**
`/backend/services/twitter_service.py`

### **Configuración**
`/backend/config.py`

---

## 📊 Endpoints API

### **1. Health Check**
```bash
GET /api/health
```

### **2. Twitter Usage**
```bash
GET /api/twitter-usage
```

### **3. Media Analysis (Optimizado)**
```bash
POST /api/media/analyze
Content-Type: application/json

{
  "location": "Colombia",
  "topic": "Seguridad",
  "max_tweets": 15,  # Máximo recomendado
  "time_window_days": 7
}
```

---

## 💡 Tips Avanzados

### **Resetear Contador Manualmente**
```bash
rm /tmp/twitter_usage.json
# El sistema creará uno nuevo automáticamente
```

### **Cambiar Límites**
Edita `/Users/arielsanroj/castor/.env`:
```bash
TWITTER_DAILY_TWEET_LIMIT=5  # Aumentar límite diario
TWITTER_MAX_TWEETS_PER_REQUEST=20  # Máximo permitido
```

### **Desactivar Rate Limiting (NO RECOMENDADO)**
Comenta las líneas en `twitter_service.py`:
```python
# can_proceed, reason = can_make_twitter_request(max_results)
# if not can_proceed:
#     logger.warning(f"Twitter rate limit check failed: {reason}")
#     return []
```

---

## 🎯 Resumen

✅ **Configurado para**: 100 posts/mes  
✅ **Límite diario**: 3 posts  
✅ **Por análisis**: 15 tweets  
✅ **Caché agresivo**: 24 horas  
✅ **Monitoreo**: `/api/twitter-usage`  

🎉 **¡Tu aplicación está optimizada para el Free Tier!**

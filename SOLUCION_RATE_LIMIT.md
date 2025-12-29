# 🔧 Solución: Rate Limit de Twitter

**Problema identificado:** El sistema está bloqueando búsquedas porque el límite diario es muy bajo (3 tweets/día).

---

## 📊 Límites de Twitter Free Tier

- **Mensual:** 100 tweets/mes
- **Diario:** ~3 tweets/día (100/30 días)
- **Por request:** Máximo 15 tweets (configurado en `TWITTER_MAX_TWEETS_PER_REQUEST`)

---

## ⚠️ Problema Actual

Cuando se solicita `max_tweets: 15` pero el límite diario es solo 3, el rate tracker bloquea la solicitud.

**Solución implementada:** El código ahora ajusta automáticamente `max_results` al límite diario disponible antes de hacer la búsqueda.

---

## ✅ Cambios Realizados

### Archivo: `backend/services/twitter_service.py`

Se ajustó la lógica para respetar el límite diario:

```python
# Ajustar max_results al límite diario disponible
daily_limit = Config.TWITTER_DAILY_TWEET_LIMIT  # 3 tweets/día
adjusted_max = min(max_results, daily_limit)

can_proceed, reason = can_make_twitter_request(adjusted_max)
if not can_proceed:
    logger.warning(f"Twitter rate limit check failed: {reason}")
    return []

# Usar adjusted_max para la búsqueda real
max_results = adjusted_max
```

---

## 🧪 Pruebas Recomendadas

### Test 1: Con límite diario disponible
```bash
curl -X POST http://localhost:5001/api/media/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Colombia",
    "topic": "seguridad",
    "max_tweets": 3,
    "time_window_days": 7
  }'
```

### Test 2: Verificar uso actual
```bash
curl http://localhost:5001/api/twitter-usage
```

---

## 📝 Notas

- El límite diario se resetea cada día a las 00:00 UTC
- El límite mensual se resetea el primer día de cada mes
- Los datos se guardan en `/tmp/twitter_usage.json`

---

## 🔄 Resetear Contadores (si es necesario)

```python
from utils.twitter_rate_tracker import TwitterRateTracker
from datetime import datetime

tracker = TwitterRateTracker()
new_data = {
    "daily": {},
    "monthly_total": 0,
    "month_start": datetime.utcnow().replace(day=1).isoformat()
}
tracker._save_usage(new_data)
```

---

**Última actualización:** 30 de Noviembre, 2025














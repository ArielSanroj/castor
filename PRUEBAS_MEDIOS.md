# 📰 Pruebas de Funcionalidad CASTOR Medios

**Fecha:** 30 de Noviembre, 2025

---

## 🎯 ¿Qué hace CASTOR Medios?

**CASTOR Medios** es un producto diseñado para **medios de comunicación y prensa**. Proporciona análisis **neutral y descriptivo** de la conversación en X/Twitter sobre temas políticos y sociales.

### Propósito Principal:
- ✅ Análisis **neutral y no partidista** para dashboards de prensa
- ✅ Resúmenes descriptivos de lo que está ocurriendo en redes sociales
- ✅ Métricas de sentimiento y temas sin recomendaciones de acción
- ✅ Visualizaciones para medios de comunicación

### Diferencias con CASTOR Campañas:
- **Medios**: Análisis neutral, descriptivo, sin recomendaciones
- **Campañas**: Análisis estratégico con recomendaciones y discursos

---

## 🔧 Funcionalidad Técnica

### Endpoint: `POST /api/media/analyze`

**Flujo de procesamiento:**

1. **Recibe parámetros de búsqueda:**
   - `location`: Ubicación (Colombia, Bogotá, etc.)
   - `topic`: Tema PND (Seguridad, Educación, Salud, etc.) - Opcional
   - `candidate_name`: Nombre de candidato - Opcional
   - `politician`: Usuario de Twitter (@usuario) - Opcional
   - `max_tweets`: Máximo de tweets a analizar (5-20, default: 15)
   - `time_window_days`: Días hacia atrás (1-30, default: 7)
   - `language`: Idioma (default: "es")

2. **Ejecuta Pipeline Core:**
   - Busca tweets en Twitter API según los parámetros
   - Analiza sentimiento con BETO (modelo de ML en español)
   - Clasifica tweets por temas del PND
   - Detecta temas trending
   - Genera datos para gráficos

3. **Genera Resumen para Medios:**
   - Usa OpenAI para generar resumen neutral y descriptivo
   - **NO** incluye recomendaciones de acción
   - **NO** incluye lenguaje prescriptivo
   - Solo describe lo que está ocurriendo

4. **Retorna respuesta estructurada:**
   - Resumen ejecutivo neutral
   - Estadísticas clave
   - Hallazgos descriptivos
   - Métricas de sentimiento
   - Análisis por temas
   - Datos para gráficos
   - Metadata (tweets analizados, ventana de tiempo, etc.)

---

## 📊 Estructura de Respuesta

```json
{
  "success": true,
  "summary": {
    "overview": "Resumen descriptivo neutral...",
    "key_stats": ["Estadística 1", "Estadística 2"],
    "key_findings": ["Hallazgo 1", "Hallazgo 2"]
  },
  "sentiment_overview": {
    "positive": 0.45,
    "neutral": 0.30,
    "negative": 0.25
  },
  "topics": [
    {
      "topic": "Seguridad",
      "sentiment": {...},
      "tweet_count": 10,
      "key_insights": [...]
    }
  ],
  "peaks": [...],
  "chart_data": {
    "by_topic_sentiment": {...},
    "volume_over_time": {...},
    "sentiment_overall": {...},
    "peaks_over_time": {...}
  },
  "metadata": {
    "tweets_analyzed": 15,
    "location": "Colombia",
    "topic": "Seguridad",
    "time_window_from": "2025-11-23T...",
    "time_window_to": "2025-11-30T...",
    "trending_topic": "Tema trending actual",
    "raw_query": "Query usado para búsqueda"
  }
}
```

---

## 🧪 Pruebas Realizadas

### Test 1: Análisis básico con tema
```bash
curl -X POST http://localhost:5001/api/media/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Colombia",
    "topic": "Seguridad",
    "max_tweets": 15,
    "time_window_days": 7
  }'
```

**Resultado:**
- ✅ Endpoint responde correctamente
- ✅ Validación de parámetros funciona
- ⚠️ No encuentra tweets (puede ser por configuración de Twitter API o falta de tweets que coincidan)

### Test 2: Análisis sin tema específico
```bash
curl -X POST http://localhost:5001/api/media/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Bogotá",
    "max_tweets": 15
  }'
```

### Test 3: Análisis con candidato
```bash
curl -X POST http://localhost:5001/api/media/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Colombia",
    "topic": "Educación",
    "candidate_name": "Juan Pérez",
    "max_tweets": 15
  }'
```

---

## ✅ Validaciones Implementadas

1. **Parámetros requeridos:**
   - `location`: Requerido

2. **Parámetros opcionales:**
   - `topic`: Opcional
   - `candidate_name`: Opcional
   - `politician`: Opcional

3. **Límites:**
   - `max_tweets`: Entre 5 y 20 (default: 15)
   - `time_window_days`: Entre 1 y 30 (default: 7)
   - `language`: Default "es"

4. **Manejo de errores:**
   - Validación con Pydantic
   - Respuestas de error claras
   - Manejo cuando no hay tweets

---

## 🔍 Estado Actual

### ✅ Funcionando:
- Endpoint responde correctamente
- Validación de parámetros
- Estructura de respuesta correcta
- Pipeline core ejecuta correctamente
- Manejo de casos sin tweets

### ⚠️ Limitaciones:
- Requiere configuración de Twitter API para obtener tweets reales
- Requiere OpenAI API key válida para generar resúmenes (actualmente falla silenciosamente)
- Sin tweets, el resumen es genérico: "Resumen no disponible por el momento"

### 🔧 Mejoras Sugeridas:
1. Mejor manejo cuando OpenAI falla (usar resumen alternativo)
2. Logs más detallados para debugging
3. Cache de resultados para evitar búsquedas duplicadas

---

## 📝 Notas Técnicas

- **Pipeline Core**: Reutiliza servicios existentes (Twitter, Sentiment, Trending, etc.)
- **Neutralidad**: El prompt de OpenAI está diseñado específicamente para ser neutral
- **Límites Twitter Free Tier**: Máximo 20 tweets por análisis para respetar límites
- **BETO Model**: Modelo de ML en español para análisis de sentimiento

---

**Última actualización:** 30 de Noviembre, 2025


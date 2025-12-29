# ✅ Flujo del Dashboard Unificado - Confirmación

## 🎯 Sí, exactamente así funciona

El usuario llena **UN SOLO FORMULARIO** y el sistema muestra **TODO EL DASHBOARD** con todos los outputs.

---

## 📝 Input del Usuario (Formulario Único)

```
┌─────────────────────────────────────────────────┐
│ Configurar dashboard                            │
│                                                 │
│ Ubicación *          [Colombia]                │
│ Tema (opcional)      [Seguridad]               │
│ Candidato (opcional) [Candidato Demo]         │
│ Usuario X/Twitter    [@candidato]              │
│ Días hacia atrás    [30]                       │
│ Días a proyectar     [14]                       │
│                                                 │
│ [Prueba con un ejemplo] [Generar dashboard]    │
└─────────────────────────────────────────────────┘
```

---

## 🔄 Procesamiento Interno

### 1. El sistema toma TODOS los inputs del formulario:

```javascript
location = "Colombia"
topic = "Seguridad"
candidate_name = "Candidato Demo"
politician = "@candidato" → se convierte a "candidato" (sin @)
days_back = 30
forecast_days = 14
```

### 2. Prepara 3 payloads diferentes:

#### Payload para Medios:
```javascript
{
  location: "Colombia",
  topic: "Seguridad",
  candidate_name: "Candidato Demo",
  politician: "candidato",  // sin @
  max_tweets: 15,           // fijo
  time_window_days: 30,      // min(daysBack, 30)
  language: "es"             // fijo
}
```

#### Payload para Forecast:
```javascript
{
  location: "Colombia",
  topic: "Seguridad",
  candidate_name: "Candidato Demo",
  politician: "candidato",  // sin @
  days_back: 30,            // del formulario
  forecast_days: 14         // del formulario
}
```

#### Payload para Trending (solo location):
```javascript
GET /api/campaign/trending?location=Colombia&limit=6
```

### 3. Hace 3 llamadas PARALELAS:

```javascript
Promise.allSettled([
  POST /api/media/analyze        → mediaData
  POST /api/forecast/dashboard   → forecastData
  GET  /api/campaign/trending    → trendingData
])
```

---

## 📊 Output del Dashboard (Todo se muestra)

Después de recibir las respuestas, el dashboard muestra:

### 1. **KPIs (4 métricas)**
```
┌──────────┬──────────┬──────────┬──────────┐
│ ICCE     │ Momentum │ Sentiment│ Volume   │
│ 65.3     │ 0.02     │ +18.5%   │ 150      │
│ Forecast │ Positivo │ Pos/Neg  │ tweets   │
└──────────┴──────────┴──────────┴──────────┘
```

**Fuentes:**
- ICCE y Momentum → `forecastData`
- Sentiment → `mediaData`
- Volume → `mediaData`

### 2. **Resumen Narrativo**
```
┌─────────────────────────────────────────┐
│ La conversación en Colombia sobre      │
│ Seguridad muestra una dinámica mixta... │
│                                         │
│ #Seguridad #120menciones #65%positivo   │
└─────────────────────────────────────────┘
```

**Fuentes:**
- Overview → `mediaData.summary.overview`
- Tags → `mediaData.summary.key_stats` + `trendingData.trending_topics`

### 3. **Gráfico Forecast**
```
┌─────────────────────────────────────────┐
│ Tracción y forecast                     │
│                                         │
│ [Gráfico de líneas: ICCE histórico +    │
│  forecast proyectado]                   │
└─────────────────────────────────────────┘
```

**Fuente:** `forecastData.series` + `forecastData.forecast`

### 4. **Streams (3 listas)**

#### Stream Medios:
```
┌─────────────────────────────────────────┐
│ Stream Medios                           │
│ • Se intensifica el tema de seguridad  │
│ • Aumento en menciones                 │
│ • Seguridad: 64 menciones              │
└─────────────────────────────────────────┘
```
**Fuente:** `mediaData.summary.key_findings` + `mediaData.topics`

#### Stream Campaña:
```
┌─────────────────────────────────────────┐
│ Stream Campaña                          │
│ • Tema caliente: Seguridad             │
│ • Tema caliente: Educación             │
└─────────────────────────────────────────┘
```
**Fuente:** `trendingData.trending_topics`

#### Stream Forecast:
```
┌─────────────────────────────────────────┐
│ Stream Forecast                         │
│ • Forecast sube 2.5 pts                │
│ • Momentum positivo                     │
│ • ICCE actual 65.3                      │
└─────────────────────────────────────────┘
```
**Fuente:** `forecastData` (procesado con `extractForecastSignals()`)

### 5. **Panel Geográfico**
```
┌─────────────────────────────────────────┐
│ Mapa de conversación                    │
│ [Mapa con puntos]                       │
│                                         │
│ Ciudades con más conversación:          │
│ 1. Bogotá        35.2%                  │
│ 2. Medellín      22.1%                  │
└─────────────────────────────────────────┘
```
**Fuente:** `mediaData.metadata.geo_distribution` (o fallback generado)

---

## 🎯 Resumen del Flujo Completo

```
USUARIO LLENA FORMULARIO
         ↓
SISTEMA PREPARA 3 PAYLOADS
         ↓
3 LLAMADAS PARALELAS A APIs
         ↓
PROCESAMIENTO DE RESPUESTAS
         ↓
RENDERIZADO DEL DASHBOARD COMPLETO:
  ✅ 4 KPIs
  ✅ Resumen narrativo
  ✅ Gráfico forecast
  ✅ 3 Streams (Medios, Campaña, Forecast)
  ✅ Panel geográfico
```

---

## ✅ Confirmación

**Sí, es exactamente así:**

1. ✅ Usuario llena **UN SOLO formulario** con todos los inputs
2. ✅ Sistema toma esos inputs y los distribuye a 3 APIs diferentes
3. ✅ Cada API recibe los parámetros que necesita (algunos compartidos, algunos específicos)
4. ✅ Dashboard muestra **TODOS los outputs** en una sola vista unificada

**Ventajas:**
- ✅ Usuario solo llena un formulario (no 3)
- ✅ Todo se muestra en una sola vista
- ✅ Datos sincronizados (mismo location, topic, candidate)
- ✅ Resiliente (si una API falla, las otras continúan)

---

## 🔍 Detalles Técnicos

### Mapeo de Inputs a APIs

| Input del Formulario | Media API | Forecast API | Trending API |
|---------------------|-----------|--------------|--------------|
| `location` | ✅ | ✅ | ✅ |
| `topic` | ✅ | ✅ | ❌ |
| `candidate_name` | ✅ | ✅ | ❌ |
| `politician` | ✅ | ✅ | ❌ |
| `days_back` | ⚠️ (como `time_window_days`, max 30) | ✅ | ❌ |
| `forecast_days` | ❌ | ✅ | ❌ |

### Valores Fijos/Calculados

- **Media API**: `max_tweets = 15` (fijo), `language = "es"` (fijo)
- **Forecast API**: Usa `days_back` y `forecast_days` directamente
- **Trending API**: Solo necesita `location`, `limit = 6` (fijo)

---

**Conclusión:** El dashboard unificado es exactamente eso: **un solo formulario → un solo dashboard con todos los outputs**.


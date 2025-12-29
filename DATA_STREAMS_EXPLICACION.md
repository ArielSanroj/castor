# 📊 Cómo Funcionan los Data Streams del Dashboard

## 🎯 Visión General

El dashboard unificado obtiene datos de **3 APIs en paralelo** y los renderiza en **3 streams separados** más otros componentes (KPIs, gráfico, geo).

---

## 🔄 Flujo Completo de Datos

```
1. USUARIO ENVÍA FORMULARIO
   ↓
2. PREPARACIÓN DE PAYLOADS
   - mediaPayload: para análisis de medios
   - forecastPayload: para pronóstico
   - trendingPayload: para temas trending
   ↓
3. LLAMADAS PARALELAS (Promise.allSettled)
   ├─ POST /api/media/analyze (timeout: 25s)
   ├─ POST /api/forecast/dashboard (timeout: 25s)
   └─ GET /api/campaign/trending (timeout: 15s)
   ↓
4. PROCESAMIENTO DE RESULTADOS
   - pickSuccessful(): extrae solo respuestas exitosas
   - Si todas fallan → error
   - Si alguna funciona → continúa
   ↓
5. RENDERIZADO
   - KPIs (4 métricas)
   - Resumen narrativo
   - Streams (3 listas)
   - Gráfico forecast
   - Panel geográfico
```

---

## 📡 Los 3 Data Streams

### 1. **Stream Medios** (`media-stream-list`)

**Fuente de datos:** `POST /api/media/analyze`

**Datos utilizados:**
```javascript
// Primarios (key_findings)
mediaData?.summary?.key_findings
// Ejemplo: ["Se intensifica el tema de seguridad", "Aumento en menciones"]

// Secundarios (topics con conteos)
mediaData?.topics?.map((t) => `${t.topic}: ${t.tweet_count} menciones`)
// Ejemplo: ["Seguridad: 64 menciones", "Educación: 32 menciones"]
```

**Código:**
```javascript
fillList(
  mediaList,
  mediaData?.summary?.key_findings,  // Items primarios
  mediaData?.topics?.map(...),       // Items secundarios
  "Sin hallazgos de medios."        // Fallback
);
```

**Renderizado:**
- Muestra hasta 6 items (primarios + secundarios combinados)
- Si no hay datos, muestra mensaje fallback

---

### 2. **Stream Campaña** (`campaign-stream-list`)

**Fuente de datos:** `GET /api/campaign/trending?location=...&limit=6`

**Datos utilizados:**
```javascript
// Trending topics (temas calientes)
trendingData?.trending_topics?.map((topic) => `Tema caliente: ${topic}`)
// Ejemplo: ["Tema caliente: Seguridad", "Tema caliente: Educación"]
```

**Código:**
```javascript
fillList(
  campaignList,
  trendingData?.trending_topics?.map(...),  // Items primarios
  [],                                       // Sin items secundarios
  "Sin tendencias disponibles."             // Fallback
);
```

**Renderizado:**
- Muestra temas trending detectados
- Formato: "Tema caliente: [nombre del tema]"
- Si no hay datos, muestra fallback

---

### 3. **Stream Forecast** (`forecast-stream-list`)

**Fuente de datos:** `POST /api/forecast/dashboard`

**Datos utilizados:**
```javascript
// Señales extraídas del forecast
const forecastSignals = extractForecastSignals(forecastData);
const forecastItems = [
  forecastSignals.forecastDirection,  // "Forecast sube 2.5 pts"
  forecastSignals.momentumLabel,      // "Momentum positivo"
  forecastSignals.icceLabel           // "ICCE actual 65.3"
].filter(Boolean);  // Elimina valores null/undefined
```

**Código:**
```javascript
fillList(
  forecastList,
  forecastItems,              // Items primarios (señales)
  [],                         // Sin items secundarios
  "Sin forecast disponible."   // Fallback
);
```

**Renderizado:**
- Muestra señales de pronóstico:
  - Dirección del forecast (sube/baja)
  - Etiqueta de momentum
  - ICCE actual
- Si no hay datos, muestra fallback

---

## 🛠️ Función `fillList()` - Motor de Renderizado

Esta función es la que realmente renderiza los streams:

```javascript
function fillList(listEl, primaryItems, secondaryItems, fallback) {
  if (!listEl) return;  // Si no existe el elemento, salir
  
  listEl.innerHTML = "";  // Limpiar contenido anterior
  
  // Combinar items primarios y secundarios
  const items = [...(primaryItems || []), ...(secondaryItems || [])]
    .filter(Boolean)  // Eliminar null/undefined/empty
    .slice(0, 6);     // Limitar a 6 items máximo
  
  if (!items.length) {
    // Si no hay items, mostrar fallback
    const li = document.createElement("li");
    li.textContent = fallback;
    listEl.appendChild(li);
    return;
  }
  
  // Crear un <li> por cada item
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    listEl.appendChild(li);
  });
}
```

**Características:**
- ✅ Limpia contenido anterior
- ✅ Combina items primarios y secundarios
- ✅ Filtra valores vacíos/null
- ✅ Limita a 6 items máximo
- ✅ Maneja casos sin datos (fallback)

---

## 🔀 Manejo de Errores y Resiliencia

### Promise.allSettled
```javascript
const [mediaResult, forecastResult, trendingResult] = await Promise.allSettled([
  fetchJsonWithTimeout(...),
  fetchJsonWithTimeout(...),
  fetchJsonWithTimeout(...)
]);
```

**Ventajas:**
- ✅ No falla si una API falla
- ✅ Continúa con las que funcionan
- ✅ Permite renderizado parcial

### pickSuccessful()
```javascript
function pickSuccessful(result) {
  if (!result || result.status !== "fulfilled") return null;
  return result.value;
}
```

**Comportamiento:**
- Si la promesa fue exitosa → retorna los datos
- Si falló → retorna `null`
- El código maneja `null` con fallbacks

### Validación Final
```javascript
if (!mediaData && !forecastData && !trendingData) {
  throw new Error("No se pudo obtener datos de los streams...");
}
```

Solo lanza error si **todas** las APIs fallaron.

---

## 📋 Estructura de Datos por Stream

### Stream Medios - Estructura Esperada
```json
{
  "summary": {
    "key_findings": [
      "Hallazgo 1",
      "Hallazgo 2"
    ]
  },
  "topics": [
    {
      "topic": "Seguridad",
      "tweet_count": 64
    }
  ]
}
```

### Stream Campaña - Estructura Esperada
```json
{
  "trending_topics": [
    "Seguridad",
    "Educación",
    "Salud"
  ]
}
```

### Stream Forecast - Estructura Esperada
```json
{
  "series": {
    "icce": [0.65, 0.67, ...],
    "momentum": [0.0, 0.02, ...]
  },
  "forecast": {
    "icce_pred": [0.70, 0.72, ...]
  }
}
```

**Nota:** Los datos del forecast se procesan con `extractForecastSignals()` para generar las señales legibles.

---

## 🎨 Renderizado Visual

Cada stream se renderiza como una lista (`<ul>`) con items (`<li>`):

```html
<!-- Stream Medios -->
<ul id="media-stream-list" class="dashboard-list">
  <li>Hallazgo 1</li>
  <li>Hallazgo 2</li>
  <li>Seguridad: 64 menciones</li>
</ul>

<!-- Stream Campaña -->
<ul id="campaign-stream-list" class="dashboard-list">
  <li>Tema caliente: Seguridad</li>
  <li>Tema caliente: Educación</li>
</ul>

<!-- Stream Forecast -->
<ul id="forecast-stream-list" class="dashboard-list">
  <li>Forecast sube 2.5 pts</li>
  <li>Momentum positivo</li>
  <li>ICCE actual 65.3</li>
</ul>
```

---

## 🔍 Función `extractForecastSignals()` - Procesamiento de Forecast

Esta función extrae señales legibles del forecast:

```javascript
function extractForecastSignals(forecastData) {
  // Extrae ICCE actual
  const icceNow = (series.icce[series.icce.length - 1] || 0) * 100;
  
  // Extrae Momentum actual
  const momentumNow = series.momentum?.[series.momentum.length - 1] || 0;
  
  // Construye dirección del forecast
  const forecastDirection = buildForecastDirection(series, forecast);
  // Ejemplo: "Forecast sube 2.5 pts"
  
  return {
    icce: icceNow,
    momentum: momentumNow,
    forecastDirection,
    momentumLabel: momentumLabel(momentumNow),  // "Momentum positivo"
    icceLabel: `ICCE actual ${icceNow.toFixed(1)}`
  };
}
```

---

## ⚡ Timeouts y Performance

Cada API tiene su timeout:
- **Media Analyze**: 25 segundos
- **Forecast Dashboard**: 25 segundos
- **Campaign Trending**: 15 segundos

**Razón:** Las APIs de análisis son más pesadas que trending.

---

## 🎯 Resumen Ejecutivo

### Flujo de Datos por Stream

1. **Stream Medios**
   - API: `/api/media/analyze`
   - Datos: `key_findings` + `topics`
   - Renderizado: Lista de hallazgos y temas

2. **Stream Campaña**
   - API: `/api/campaign/trending`
   - Datos: `trending_topics`
   - Renderizado: Lista de temas calientes

3. **Stream Forecast**
   - API: `/api/forecast/dashboard`
   - Datos: Procesados con `extractForecastSignals()`
   - Renderizado: Señales de pronóstico

### Características Clave

- ✅ **Paralelo**: Las 3 APIs se llaman simultáneamente
- ✅ **Resiliente**: Si una falla, las otras continúan
- ✅ **Limitado**: Máximo 6 items por stream
- ✅ **Fallback**: Mensajes cuando no hay datos
- ✅ **Dinámico**: Se actualiza con cada submit del formulario

---

## 🐛 Debugging

Para ver qué datos llegan a cada stream:

```javascript
// En la consola del navegador (F12)
console.log("Media Data:", mediaData);
console.log("Forecast Data:", forecastData);
console.log("Trending Data:", trendingData);
```

O agregar logs en `renderStreamLists()`:

```javascript
function renderStreamLists(mediaData, forecastData, trendingData) {
  console.log("Media key_findings:", mediaData?.summary?.key_findings);
  console.log("Trending topics:", trendingData?.trending_topics);
  console.log("Forecast signals:", extractForecastSignals(forecastData));
  // ... resto del código
}
```

---

**Última actualización:** 2025-12-28


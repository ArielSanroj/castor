# ✅ Implementación Completa de CASTOR Forecast según Modelo Teórico

## 🎯 Resumen

Se ha refactorizado completamente `ForecastService` para seguir **exactamente** el modelo teórico descrito, con las fórmulas matemáticas precisas y la estructura de JSON de salida especificada.

## 📊 Cambios Implementados

### 1. **Cálculo de ICCE según Modelo Teórico**

**Antes:**
```python
ICCE = (Volume_Normalized * 0.4) + (Sentiment_Score * 0.4) + (Conversation_Share * 0.2)
```

**Ahora:**
```python
# ISN (Índice de Sentimiento Neto)
ISN = P_c - N_c  # Range: [-1, 1]

# ISN normalizado
ISN' = (ISN + 1) / 2  # Range: [0, 1]

# ICR (Índice de Conversación Relativa)
ICR = V_c / V_total  # Range: [0, 1]

# ICCE según modelo teórico
ICCE = α * ISN' + (1-α) * ICR  # Default α=0.5
```

**Cambios clave:**
- ✅ Calcula `ISN` explícitamente como `P - N`
- ✅ Calcula `ICR` comparando con `V_total` real del día (no divisor fijo)
- ✅ Usa fórmula teórica exacta: `α * ISN' + (1-α) * ICR`
- ✅ Obtiene `V_total` buscando tweets sin filtro de candidato

### 2. **EMA (Exponential Moving Average) para Suavizado**

**Implementado:**
```python
def calculate_ema_smooth(icce_values, lambda_param=0.3):
    """
    EMA formula: S_t = λ * ICCE_t + (1-λ) * S_{t-1}
    """
    smoothed = [values[0]]  # Initialize
    for i in range(1, len(values)):
        ema_value = lambda_param * values[i] + (1 - lambda_param) * smoothed[i-1]
        smoothed.append(ema_value)
    return smoothed
```

**Características:**
- ✅ Usa `λ = 0.3` como valor por defecto (según ejemplo)
- ✅ Suaviza valores ICCE para reducir ruido
- ✅ Se usa tanto en Momentum como en Forecast

### 3. **Momentum con EMA**

**Antes:**
```python
# Media móvil simple
recent_avg = np.mean([v.value for v in icce_values[i-window:i]])
momentum = recent_avg - previous_avg
```

**Ahora:**
```python
# EMA smoothing
smoothed_values = calculate_ema_smooth(icce_values)

# Momentum = diferencia de EMA
MEC_t = S_t - S_{t-1}
```

**Características:**
- ✅ Usa EMA en lugar de media móvil simple
- ✅ Momentum = diferencia entre valores EMA consecutivos
- ✅ Requiere mínimo 2 días (antes requería 8)

### 4. **Forecast sobre Valores Suavizados**

**Implementado:**
```python
def forecast_icce(icce_values, use_smoothed=True, lambda_param=0.3):
    if use_smoothed:
        smoothed_values = calculate_ema_smooth(icce_values, lambda_param)
        values = [v * 100.0 for v in smoothed_values]
    # ... forecast on smoothed values
```

**Características:**
- ✅ Por defecto usa valores EMA suavizados para mejor detección de tendencias
- ✅ Opción de usar valores raw si se necesita

### 5. **Estructura JSON Exacta del Ejemplo**

**Estructura de respuesta del endpoint `/api/forecast/dashboard`:**

```json
{
  "success": true,
  "candidate": "@juanperez",
  "candidate_name": "Juan Pérez",
  "location": "Bogotá",
  "series": {
    "dates": ["2025-05-01", "2025-05-02", ...],
    "icce": [0.358, 0.370, 0.310, ...],
    "icce_smooth": [0.358, 0.364, 0.340, ...],
    "momentum": [0.0, 0.006, -0.024, ...]
  },
  "forecast": {
    "dates": ["2025-05-08", "2025-05-09", ...],
    "icce_pred": [0.336, 0.338, 0.340, ...],
    "pred_low": [0.320, 0.322, 0.324, ...],
    "pred_high": [0.350, 0.354, 0.356, ...]
  },
  "metadata": {
    "calculated_at": "2025-05-07T12:00:00",
    "days_back": 30,
    "forecast_days": 14,
    "model_type": "holt_winters"
  }
}
```

**Características:**
- ✅ Valores en escala [0, 1] (no 0-100) para coincidir con ejemplo
- ✅ Incluye `icce_smooth` (valores EMA suavizados)
- ✅ Incluye `momentum` en la serie
- ✅ Forecast con `icce_pred`, `pred_low`, `pred_high`

## 🔧 Archivos Modificados

1. **`backend/app/services/forecast_service.py`**
   - Refactorizado `calculate_icce()` con modelo teórico exacto
   - Agregado `calculate_ema_smooth()` para suavizado exponencial
   - Refactorizado `calculate_momentum()` para usar EMA
   - Actualizado `forecast_icce()` para trabajar con valores suavizados

2. **`backend/app/routes/forecast.py`**
   - Actualizado endpoint `/api/forecast/dashboard` para devolver JSON con estructura exacta
   - Incluye valores suavizados y momentum en la respuesta

## 📈 Ejemplo de Cálculo

Siguiendo el ejemplo del documento:

**Día 1:**
- Tweets candidato: 500
- Positivos: 200 (40%), Negativos: 150 (30%)
- Total sistema: 3000 tweets

**Cálculo:**
```
ISN = 0.40 - 0.30 = 0.10
ISN' = (0.10 + 1) / 2 = 0.55
ICR = 500 / 3000 = 0.1666
ICCE = 0.5 * 0.55 + 0.5 * 0.1666 = 0.358
```

**EMA (Día 2):**
```
S_1 = 0.358 (inicial)
S_2 = 0.3 * 0.370 + 0.7 * 0.358 = 0.364
```

**Momentum (Día 2):**
```
MEC_2 = S_2 - S_1 = 0.364 - 0.358 = +0.006
```

## ✅ Validación

- ✅ Fórmulas coinciden exactamente con modelo teórico
- ✅ Estructura JSON coincide con ejemplo proporcionado
- ✅ Valores en escala correcta [0, 1]
- ✅ EMA implementado correctamente
- ✅ Momentum calculado como diferencia de EMA
- ✅ Forecast usa valores suavizados por defecto

## 🚀 Próximos Pasos (Opcional)

1. **Implementar IFT (Índice de Foco en Temas)**
   - Calcular distribución por tema PND
   - Agregar a respuestas API

2. **Mejorar obtención de V_total**
   - Optimizar búsqueda de tweets totales
   - Cachear resultados por día

3. **Validación histórica**
   - Comparar con datos reales
   - Ajustar parámetros α y λ si es necesario

## 📝 Notas Técnicas

- Los valores ICCE se almacenan internamente en escala 0-100 para compatibilidad
- Se convierten a escala 0-1 en las respuestas JSON para coincidir con ejemplo
- El parámetro `alpha` es configurable (default 0.5)
- El parámetro `lambda` para EMA es configurable (default 0.3)


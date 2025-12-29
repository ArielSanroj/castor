# Análisis: Implementación Actual vs Modelo Teórico de CASTOR Forecast

## 📊 Estado Actual de la Implementación

### ✅ Lo que SÍ está implementado:

1. **ICCE básico** - Funciona pero con fórmula diferente al modelo teórico
2. **Momentum (MEC)** - Implementado con media móvil simple
3. **Forecast** - Holt-Winters simplificado funcionando
4. **Endpoints API** - `/api/forecast/icce`, `/api/forecast/momentum`, `/api/forecast/dashboard`
5. **Integración con servicios** - TwitterService, SentimentService funcionando

### ❌ Diferencias con el Modelo Teórico:

#### 1. **Fórmula de ICCE**

**Modelo Teórico:**
```
ICCE_c(t) = α * ISN'_c(t) + (1-α) * ICR_c(t)
```
Donde:
- `ISN'_c(t)` = Sentimiento Neto normalizado [0,1]
- `ICR_c(t)` = Cuota de conversación [0,1]
- `α` = peso (ej: 0.5)

**Implementación Actual:**
```python
ICCE = (Volume_Normalized * 0.4) + (Sentiment_Score * 0.4) + (Conversation_Share * 0.2)
```

**Problemas:**
- Usa 3 componentes en lugar de 2
- `Conversation_Share` no se calcula comparando con `V_total` (total de conversación del día)
- No calcula explícitamente `ISN` ni `ICR` como índices separados

#### 2. **Índice de Sentimiento Neto (ISN)**

**Modelo Teórico:**
```
ISN_c(t) = P_c(t) - N_c(t)  # Rango [-1, 1]
ISN'_c(t) = (ISN_c(t) + 1) / 2  # Normalizado a [0, 1]
```

**Implementación Actual:**
```python
avg_sentiment = data['sentiment_sum'] / data['count']  # Ya es P - N
sentiment_score = (avg_sentiment + 1) * 50  # Convierte a 0-100
```

**Estado:** ✅ Se calcula implícitamente pero no se expone como índice separado

#### 3. **Índice de Conversación Relativa (ICR)**

**Modelo Teórico:**
```
V_total(t) = Σ V_c(t)  # Suma de todos los candidatos
ICR_c(t) = V_c(t) / V_total(t)
```

**Implementación Actual:**
```python
# Conversation share (simplified - would compare with total conversation)
conversation_share = min(data['count'] / 10.0, 1.0) * 100
```

**Problema:** ❌ No compara con el total real de conversación del día. Usa un divisor fijo (10.0) que no tiene sentido.

#### 4. **Índice de Foco en Temas (IFT)**

**Modelo Teórico:**
```
IFT_{c,k}(t) = V_{c,k}(t) / Σ_j V_{c,j}(t)
```
Distribución de probabilidad sobre temas PND.

**Implementación Actual:** ❌ No implementado

#### 5. **Momentum con EMA**

**Modelo Teórico:**
```
ICCE_smooth(t) = λ * ICCE(t) + (1-λ) * ICCE_smooth(t-1)  # EMA
MEC_c(t) = ICCE_smooth(t) - ICCE_smooth(t-1)
```

**Implementación Actual:**
```python
# Usa media móvil simple, no EMA
recent_avg = np.mean([v.value for v in icce_values[i-window:i]])
previous_avg = np.mean([v.value for v in icce_values[i-window-1:i-1]])
momentum = recent_avg - previous_avg
```

**Problema:** ❌ Usa media móvil simple en lugar de EMA exponencial

## 🔧 Recomendaciones de Mejora

### Prioridad Alta:

1. **Calcular ICR correctamente**
   - Obtener `V_total(t)` sumando tweets de todos los candidatos del día
   - Calcular `ICR_c(t) = V_c(t) / V_total(t)`

2. **Refactorizar ICCE según modelo teórico**
   - Calcular `ISN_c(t)` y `ISN'_c(t)` explícitamente
   - Calcular `ICR_c(t)` correctamente
   - Usar fórmula: `ICCE = α * ISN' + (1-α) * ICR` con `α` configurable

3. **Implementar EMA para Momentum**
   - Reemplazar media móvil simple por EMA exponencial
   - Usar `λ = 0.3` como valor por defecto

### Prioridad Media:

4. **Implementar IFT (Índice de Foco en Temas)**
   - Calcular distribución por tema PND para cada candidato
   - Exponer en API como métrica adicional

5. **Exponer índices intermedios en API**
   - Agregar `ISN`, `ICR`, `IFT` como campos en las respuestas
   - Permitir análisis más granular

### Prioridad Baja:

6. **Mejorar forecast con Prophet/ARIMA**
   - Evaluar librerías más robustas si es necesario
   - Mantener Holt-Winters como fallback

## 📝 Plan de Implementación Sugerido

### Fase 1: Corregir Cálculos Base
- [ ] Modificar `calculate_icce()` para obtener `V_total` del día
- [ ] Calcular `ICR_c(t)` correctamente
- [ ] Calcular `ISN_c(t)` y `ISN'_c(t)` explícitamente
- [ ] Refactorizar fórmula ICCE según modelo teórico

### Fase 2: Mejorar Momentum
- [ ] Implementar EMA en lugar de media móvil simple
- [ ] Actualizar `calculate_momentum()` con suavizado exponencial

### Fase 3: Agregar IFT
- [ ] Calcular distribución por tema PND
- [ ] Agregar IFT a esquemas y respuestas API

### Fase 4: Documentación
- [ ] Actualizar documentación técnica con fórmulas exactas
- [ ] Agregar ejemplos de cálculo en docs

## 🎯 Conclusión

La implementación actual **funciona** pero **no sigue exactamente el modelo teórico** descrito. Las diferencias principales son:

1. **ICCE usa fórmula diferente** (3 componentes vs 2 del modelo teórico)
2. **ICR no se calcula comparando con V_total real**
3. **Momentum usa media móvil simple en lugar de EMA**
4. **IFT no está implementado**

**Recomendación:** Refactorizar para alinear con el modelo teórico, especialmente el cálculo de ICR y la fórmula de ICCE, ya que estos son fundamentales para la precisión del modelo.













# 🎯 Forecast con Lenguaje Estratégico (No Técnico)

## ✅ Cambios Implementados

### 1. **Traducción de Términos Técnicos a Lenguaje Estratégico**

| Término Técnico | Término Estratégico | Interpretación Automática |
|----------------|---------------------|---------------------------|
| **ICCE** | **Fuerza Narrativa** | 70-100: Dominante<br>50-70: Competitiva<br>30-50: Débil<br>0-30: Crisis |
| **Momentum** | **Tendencia Semanal** | Positivo: Ganando terreno<br>Estable: Sin cambios<br>Negativo: Perdiendo narrativa |
| **Forecast** | **Pronóstico de Conversación** | Crecimiento/Estabilidad/Caída con explicación estratégica |
| **Riesgos/Oportunidades** | **Alertas Estratégicas** | Lenguaje de gerente de campaña |

### 2. **Funciones de Traducción Estratégica**

#### `translateNarrativeStrength(icce, candidateName, location)`
Convierte ICCE a "Fuerza Narrativa" con interpretación automática:
- **79 puntos** → "Narrativa dominante" → "María López tiene una narrativa fuerte y dominante..."
- **45 puntos** → "Narrativa débil" → "Juan Pérez tiene una narrativa débil..."
- **18 puntos** → "Crisis severa" → "Ricardo Gómez está en crisis narrativa severa..."

#### `translateWeeklyTrend(momentum, trend, candidateName, momentumHistory)`
Convierte Momentum a "Tendencia Semanal":
- Analiza patrones históricos (caídas recientes, recuperaciones)
- Genera explicaciones contextuales: "perdió terreno a mitad de semana pero se está recuperando"

#### `translateConversationForecast(forecastPoints, currentICCE, candidateName)`
Convierte Forecast a "Pronóstico de Conversación":
- **Crecimiento moderado** → "La conversación seguirá subiendo..."
- **Recuperación leve** → "Se proyecta una recuperación lenta pero sostenida..."
- **Caída continua** → "Se proyecta una caída continua..."

### 3. **Tres Escenarios de Ejemplo**

#### 🟢 **Escenario BUENO** - Narrativa Dominante
- **Candidato:** María López (Medellín)
- **Fuerza Narrativa:** 79 puntos (dominante)
- **Tendencia:** Subiendo (5 días consecutivos de crecimiento)
- **Pronóstico:** Crecimiento moderado
- **Oportunidades:** Tema Empleo muy favorable, Engagement alto con jóvenes
- **Riesgos:** Críticas menores (bajo)

#### 🟡 **Escenario MALO** - Narrativa Débil (Default)
- **Candidato:** Juan Pérez (Bogotá)
- **Fuerza Narrativa:** 33 puntos (débil)
- **Tendencia:** Estable con recuperación ligera
- **Pronóstico:** Recuperación leve
- **Oportunidades:** Tema Empleo positivo, Buen rebote post-debate
- **Riesgos:** Críticas en Seguridad, Caída a mitad de semana

#### 🔴 **Escenario CRISIS** - Narrativa Colapsada
- **Candidato:** Ricardo Gómez (Cali)
- **Fuerza Narrativa:** 18 puntos (crisis severa)
- **Tendencia:** Bajando fuerte (tres caídas abruptas)
- **Pronóstico:** Caída continua
- **Oportunidades:** Solo si hay respuesta clara y contundente
- **Riesgos:** Crisis activa, Narrativa dominada por corrupción (alto)

### 4. **Componentes UI Actualizados**

#### Tarjetas de Resumen
```
🔵 FUERZA NARRATIVA — 33 puntos (débil)
La conversación sobre Juan Pérez es débil y vulnerable. 
Los votantes hablan más desde la crítica que desde el apoyo.

🟠 TENDENCIA SEMANAL — estable
Juan Pérez perdió terreno a mitad de semana por críticas en Seguridad, 
pero el tono mejoró ligeramente los últimos dos días.

🟣 PRONÓSTICO A 7 DÍAS — recuperación leve
La conversación se mantendrá estable, con una leve recuperación. 
No se proyecta una crisis inmediata, pero tampoco un crecimiento fuerte.
```

#### Recomendación Estratégica
```
🎯 Recomendación Estratégica
Posicionar mensajes en Empleo y mitigar críticas en Seguridad 
con propuestas claras y datos verificables.
```

#### Oportunidades y Riesgos
- **Oportunidades:** Lista con iconos ✅ y descripciones estratégicas
- **Riesgos:** Lista con iconos ⚠️, severidad (bajo/medio/alto) y descripciones contextuales

### 5. **Estructura de Datos Estratégica**

El mockup ahora incluye en `metadata`:
```javascript
{
  metadata: {
    risks: [
      "Críticas sostenidas en Seguridad",
      "Caída fuerte a mitad de semana"
    ],
    opportunities: [
      "Tema Empleo en tono positivo",
      "Buen rebote post-debate"
    ],
    strategic_recommendation: "Posicionar mensajes en Empleo..."
  }
}
```

### 6. **Renderizado Inteligente**

- **Detecta estructura nueva** (`series`/`forecast`) vs antigua (`icce`/`momentum`)
- **Usa traducciones estratégicas** si están disponibles
- **Muestra recomendación estratégica** si está en metadata
- **Renderiza oportunidades/riesgos** desde metadata o genera automáticamente

## 📊 Ejemplo Visual Completo

### Cuando el usuario hace clic en "Prueba con un ejemplo":

1. **Formulario prellenado** con datos del escenario
2. **Tarjetas de resumen** con lenguaje estratégico (no técnico)
3. **Gráficos** con títulos descriptivos
4. **Recomendación estratégica** destacada
5. **Oportunidades y riesgos** con lenguaje de gerente de campaña

### Lenguaje Mostrado:

❌ **ANTES (Técnico):**
- "ICCE: 33.0"
- "Momentum: -0.001"
- "Forecast: 34.8"

✅ **AHORA (Estratégico):**
- "Fuerza Narrativa: 33 puntos (débil)"
- "Tendencia Semanal: estable con recuperación ligera"
- "Pronóstico: recuperación leve en los próximos 7 días"

## 🎯 Beneficios

✅ **100% comprensible** para gerentes de campaña sin conocimiento técnico
✅ **Lenguaje periodístico + estratégico** en lugar de matemático
✅ **Interpretaciones automáticas** contextualizadas
✅ **Recomendaciones accionables** en lugar de solo métricas
✅ **Mantiene rigor técnico** pero lo traduce a insights humanos

## 🚀 Uso

El ejemplo se genera automáticamente con el escenario "malo" (Juan Pérez) por defecto. Para cambiar de escenario, se puede modificar la llamada:

```javascript
testForecastWithMockup("good")   // María López - Narrativa dominante
testForecastWithMockup("bad")    // Juan Pérez - Narrativa débil (default)
testForecastWithMockup("crisis") // Ricardo Gómez - Crisis severa
```













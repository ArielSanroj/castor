# 📊 Cómo Debería Verse el Ejemplo de Forecast

## 🎯 Cuando el Usuario Hace Clic en "Prueba con un Ejemplo"

### 1. **Formulario Prellenado**
El formulario se llena automáticamente con:
- **Ubicación:** "Bogotá"
- **Candidato:** "Juan Pérez"
- **Días hacia atrás:** 30 (pero muestra 7 días de datos)
- **Días a proyectar:** 14 (pero muestra 7 días de proyección)

### 2. **Tarjetas de Resumen (Top)**

#### 🔵 **ESTADO ACTUAL**
```
ICCE actual: 33.0. La conversación sobre Juan Pérez en Bogotá muestra 
un índice compuesto de 33.0 puntos.
```

#### 🟠 **MOMENTUM**
```
Momentum: -0.001. Juan Pérez está estable en la conversación.
```
*(Puede mostrar "ganando momentum" o "perdiendo momentum" según el valor)*

#### 🟣 **PROYECCIÓN**
```
Proyección a 7 días: tendencia creciente. ICCE proyectado: 34.8.
```

### 3. **Tarjeta de Posición Narrativa**

```
⭐ Posición Narrativa del Candidato

65%                    [Número grande en color]
Competitivo con sesgo positivo

🟡 Riesgo medio-bajo
```

### 4. **Pestaña: Resumen (Overview)**

#### 📊 **Dominio Narrativo**
```
Juan Pérez tiene una cuota de conversación del 42% en el tema analizado.
Esto indica una presencia significativa en la conversación pública.
```

#### 💬 **Tono de la Conversación**
```
El sentimiento neto ajustado es +0.15, indicando una conversación 
ligeramente positiva alrededor de Juan Pérez.
```

#### 📈 **Gráfico Principal: Forecast**
- **Línea naranja sólida:** ICCE histórico suavizado (EMA)
- **Línea verde punteada:** Proyección futura
- **Área sombreada:** Intervalos de confianza (pred_low a pred_high)

**Interpretación visual:**
- Días 1-2: Subida ligera
- Días 3-4: Caída fuerte (crisis/polémica)
- Días 5-7: Recuperación suave
- Días 8-14: Proyección con tendencia creciente

### 5. **Pestaña: Tendencias**

#### 📈 **Evolución Histórica (Gráfico ICCE)**
- **Línea naranja punteada:** ICCE Raw (valores originales)
- **Línea verde sólida:** ICCE Suavizado (EMA)

**Valores del ejemplo:**
- D1: 0.358 (35.8)
- D2: 0.370 (37.0) ⬆️
- D3: 0.310 (31.0) ⬇️ *Caída*
- D4: 0.298 (29.8) ⬇️ *Mínimo*
- D5: 0.315 (31.5) ⬆️ *Recuperación*
- D6: 0.360 (36.0) ⬆️ *Rebote*
- D7: 0.330 (33.0) ⬇️ *Estable*

#### 📊 **Momentum (Gráfico de Barras)**
- **Barras verdes:** Momentum positivo (ganando)
- **Barras rojas:** Momentum negativo (perdiendo)

**Valores del ejemplo:**
- D2: +0.006 (verde claro)
- D3: -0.024 (rojo largo) ⚠️
- D4: -0.016 (rojo) ⚠️
- D5: -0.002 (rojo corto)
- D6: +0.013 (verde) ✅
- D7: -0.001 (rojo muy corto)

### 6. **Pestaña: Oportunidades**

Tarjetas con oportunidades identificadas:
```
✅ [Icono] Oportunidad: Rebote en D6
   El momentum positivo en el día 6 indica una recuperación 
   narrativa después de la caída de los días 3-4.

✅ [Icono] Oportunidad: Tendencia proyectada positiva
   La proyección muestra una tendencia creciente en los próximos días.
```

### 7. **Pestaña: Riesgos**

Tarjetas con riesgos identificados:
```
⚠️ [Icono] Riesgo: Caída significativa D3-D4 [medio]
   La conversación cayó bruscamente en los días 3-4, 
   indicando una posible crisis comunicacional o polémica.

⚠️ [Icono] Riesgo: Momentum negativo reciente [bajo]
   El momentum negativo en el día 7 requiere monitoreo.
```

## 📐 Estructura Visual Esperada

### Layout General:
```
┌─────────────────────────────────────────────────┐
│  [Tarjetas de Resumen: Estado, Momentum, Proyección] │
├─────────────────────────────────────────────────┤
│  [Tarjeta Posición Narrativa - Grande]         │
├─────────────────────────────────────────────────┤
│  [Tabs: Resumen | Tendencias | Oportunidades | Riesgos] │
├─────────────────────────────────────────────────┤
│                                                 │
│  [Contenido según Tab Activo]                  │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Colores y Estilos:
- **ICCE Raw:** Naranja (`rgb(255, 106, 61)`) - línea punteada
- **ICCE Suavizado:** Verde (`rgb(66, 214, 151)`) - línea sólida
- **Proyección:** Verde punteado
- **Intervalos:** Gris semitransparente
- **Momentum positivo:** Verde
- **Momentum negativo:** Rojo

## 🎨 Elementos Visuales Clave

1. **Gráficos interactivos** (Chart.js)
   - Zoom y hover para ver valores exactos
   - Leyendas clicables para mostrar/ocultar series

2. **Tarjetas informativas**
   - Bordes de colores según tipo
   - Iconos descriptivos
   - Texto claro y conciso

3. **Indicadores de tendencia**
   - Flechas ⬆️⬇️ para mostrar dirección
   - Colores semafóricos (verde/amarillo/rojo)

4. **Números destacados**
   - ICCE en escala 0-100
   - Momentum con signo (+/-)
   - Porcentajes para métricas narrativas

## ✅ Checklist de Visualización

- [x] Formulario prellenado con valores de ejemplo
- [x] Tarjetas de resumen con texto descriptivo
- [x] Gráfico principal con histórico + proyección
- [x] Gráfico de ICCE con línea raw y suavizada
- [x] Gráfico de Momentum con barras de colores
- [x] Tarjetas de oportunidades y riesgos
- [x] Posición narrativa con IVN destacado
- [x] Tabs funcionales para navegar entre vistas

## 🚀 Datos del Ejemplo Teórico

Los datos mostrados siguen **exactamente** el ejemplo teórico:

**Serie Histórica (7 días):**
- ICCE Raw: [0.358, 0.370, 0.310, 0.298, 0.315, 0.360, 0.330]
- ICCE Suavizado: [0.358, 0.364, 0.340, 0.324, 0.322, 0.335, 0.334]
- Momentum: [0.0, +0.006, -0.024, -0.016, -0.002, +0.013, -0.001]

**Proyección (7 días):**
- ICCE Predicho: [0.336, 0.338, 0.340, 0.343, 0.345, 0.347, 0.348]
- Intervalos: Low [0.320...], High [0.350...]

Esto permite al usuario ver **exactamente** cómo funciona el modelo teórico con datos realistas.


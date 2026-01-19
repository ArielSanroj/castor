# Modelo Castor Elecciones

## Visión General

El modelo trata la campaña política como un **"juego narrativo" dinámico** entre varios jugadores (una campaña v. rivales), donde el objetivo es maximizar la ventaja narrativa (medida por ICCE, Momentum, SOV, SNA e IVN) con información incompleta (solo señales públicas como tendencias en X o medios).

El enfoque usa datos de CASTOR para estimar "movidas" óptimas diarias o semanales. Tiene 3 pasos clave (estado, acciones, recompensa), con un payoff basado en métricas intermedias como ΔICCE (+10 puntos = ganancia alta). Esto permite a candidatos políticos tomar decisiones rápidas, como "pivotar un tema" si el rival domina el SOV. El resultado: un **"copiloto de juegos"** integrable al dashboard, que recomienda 3 acciones con riesgo bajo y alto payoff, potencialmente aumentando la intención de voto en **5-15%** según benchmarks históricos.

---

## Análisis de Datos

### Métricas Clave

- **ICCE** (fuerza narrativa, 0-100): Índice Compuesto de Conversación Electoral
- **Momentum**: Tendencia de conversación
- **SOV** (Share of Voice): Cuota de voz en la conversación
- **SNA** (Sentimiento Neto): Sentimiento Neto de la conversación
- **IVN** (Índice de Ventaja Narrativa): Ventaja narrativa por tema
- **Engagement**: Interacción en redes
- **Alcance**: Reach de las publicaciones
- **Firmas/día**: Firma de peticiones o apoyo

Estos datos representan **"señales"** del ecosistema electoral, con confianza media en la mayoría (depende de ejecución).

### Datos Clave Extraídos

- **ICCE y Momentum** detectan cambios rápidos (24-48h), ideales para juegos dinámicos.
- **SOV y SNA** miden competencia directa (e.g., si rival sube SOV en "seguridad", tu SNA cae).
- **Trending Topics y Hashtags** ofrecen señales en tiempo real (hoy), con uplift en engagement (10-25% semanal).
- **Proyecciones (7-14 días)** anticipan riesgos, como caída de ICCE >10 pts.

### Supuestos del Modelo

- **Plaza media**: 100k-500k electores
- **Base digital inicial**: 5k-50k seguidores
- **Ejecución mínima**: 4-6 piezas/semana

### Estado del Juego (S)

Estos datos forman el **"estado del juego" (S)**, que es incompleto porque no ves las intenciones reales de rivales, solo inferencias (e.g., si rival empuja "seguridad" vía trending, asumes ataque).

Usando elasticidad histórica (de la tabla: métricas intermedias → voto), estimo que un **ΔICCE +10 pts** correlaciona con **+5-10%** en intención de voto. El modelo es bayesiano: actualizas creencias con datos diarios de CASTOR (e.g., si SNA negativo en un tema, probabilidad de pérdida narrativa = 60%).

### Limitaciones

- **Confianza baja en orgánico** (variabilidad alta), así que priorizo acciones con payout medible (e.g., engagement > min_faves:10 en X).

---

## Plan Estratégico

El modelo se integra al dashboard como sección **"Juego Narrativo"**, con implementación sencilla. Aquí va el desarrollo paso a paso, simplificado para candidatos: **piensa en ajedrez electoral, donde CASTOR te da "visión parcial" del tablero**.

### 1. Definir Jugadores y Objetivos

**Jugadores:**
- **"Cliente" (C)**: Tu campaña
- **"Rival Principal" (R1)**: Opositor fuerte
- **"Rival Secundario" (R2)**: Independiente u otro

**Objetivo:** Maximizar IVN (ventaja narrativa) al final de la campaña, minimizando costos (gasto, riesgo reputacional). 

**Ganar = ICCE >70 y Momentum positivo.**

### 2. Estado del Juego (S)

**S = Combinación simple de métricas:**
- ICCE (fuerza general)
- Momentum (velocidad)
- SOV (dominio)
- SNA (tono)
- IVN (ventaja por tema)

**Ejemplo:** Si ICCE=50, Momentum=-5% semanal, SOV=30%, SNA=-10 en "seguridad", estado = **"Defensivo"** (riesgo medio).

### 3. Acciones Posibles (Estrategias)

Simplificadas a **3-5 opciones por "turno"** (día/semana):

- **A1: Proponer** (e.g., nuevo tema con 3 posts en redes)
- **A2: Contrastar** (e.g., responder rival con datos, vía medios)
- **A3: Atacar** (e.g., cuestionar rival en trending topic)
- **A4: Evitar/Pivotar** (e.g., cambiar a tema con SNA positivo)

**Intensidad:**
- **Baja**: Orgánico, costo bajo
- **Media**: Pauta ligera
- **Alta**: Campaña full, riesgo alto

**Ligado a CASTOR:** Usa "Trending Topics" para elegir tema, "Hashtags" para canal.

### 4. Payoff (Recompensa)

**Fórmula simple:**
```
Payoff = (ΔICCE * 2) + (ΔSNA * 1.5) + (ΔSOV * 1) + (Momentum * 0.5) - Costo (1-3 pts) - Riesgo (0-5 pts)
```

**Ejemplo:**
- +10 ICCE = +20 pts
- Riesgo alto (e.g., ataque falla) = -5 pts

**Pesos basados en tabla:** Priorizo ICCE (métrica clave) y SNA (sentimiento 99% preciso).

- **Payoff >15** = Buena movida
- **Payoff <0** = Evitar

### 5. Información Incompleta y Señales

No ves planes rivales, solo señales de CASTOR (e.g., "Rival A domina SOV en seguridad" vía Radar Ciudadano).

**Actualiza diariamente:** Si alerta "SNA cayó 12%", asume rival atacó (probabilidad 70%).

### 6. Equilibrio (Mejor Respuesta)

Usa **"Mejor Respuesta Simple"**: Simula 3 acciones vs. señal rival, elige la con payoff más alto.

**Ejemplo:**
- **Estado:** ICCE cae, SNA negativo en seguridad. Rival: Empuja seguridad.
- **A1 (Evitar):** Payoff = +5 (mejora tono, pero -SOV)
- **A2 (Contrastar):** Payoff = +12 (ΔSNA +10, mantiene SOV)
- **A3 (Atacar):** Payoff = +8 (ΔSOV +15, pero riesgo -7)

**Mejor: A2**, con playbook: "Emitir comunicado + video corto".

### 7. Implementación en Dashboard

**Nueva sección: "Juego Narrativo"**

- **Tarjeta 1:** Estado Actual (gráfico simple de métricas)
- **Tarjeta 2:** Señal Rival (e.g., "Trending: Seguridad, Intensidad Alta")
- **Tarjeta 3:** 3 Acciones Recomendadas (con payoff, riesgo, checklist: quién/cuándo/medir)

**Rutina:**
- **Diario (8am):** Integra con "Resumen Ejecutivo"
- **Quincenal:** Ajusta pesos con datos nuevos

**MVP:** Empieza con 2 jugadores, expande a 3. Usa alertas CASTOR para triggers (e.g., si Momentum cae 2 semanas, activa simulación).

Este plan aumenta eficiencia: Reasigna 60-80% recursos a movidas ganadoras (de tabla), con uplift en intención vía métricas intermedias.

---

## Discurso

> "Señores y señoras, en esta campaña no jugamos a ciegas. Usando herramientas como CASTOR, vemos el tablero claro: mientras rivales empujan temas divisivos como la seguridad con narrativas negativas, nosotros contrastamos con propuestas reales que resuenan en el sentimiento ciudadano. Nuestro ICCE sube porque escuchamos: prioricemos economía y paz, donde nuestra ventaja narrativa es clara. ¡No dejemos votos sobre la mesa – actuemos con datos, no con intuición! Juntos, ganamos el juego electoral con estrategia inteligente."

---

## Gráfico Sugerido

Dado que tenemos datos numéricos de métricas (e.g., ICCE 0-100, Δ en SNA/SOV), sugiero un **gráfico de radar** para visualizar el "Estado del Juego" vs. rivales, comparando fortalezas. Esto ayuda a candidatos a ver desequilibrios de un vistazo.

### Características del Gráfico

- **Eje 1:** ICCE (0-100)
- **Eje 2:** Momentum (-100% a +100%)
- **Eje 3:** SOV (0-100%)
- **Eje 4:** SNA (-100 a +100)
- **Eje 5:** IVN (0-100)
- **Eje 6:** Engagement (normalizado)

Cada jugador (Cliente, Rival 1, Rival 2) tiene su polígono, permitiendo comparación visual rápida de ventajas y desventajas narrativas.

---

## Resumen Ejecutivo

El Modelo Castor Elecciones transforma la campaña política en un **juego estratégico basado en datos**, donde:

1. **Estado del juego** se actualiza diariamente con métricas de CASTOR
2. **Acciones** se optimizan usando payoff calculado (ΔICCE, ΔSNA, ΔSOV)
3. **Señales rivales** se detectan vía trending topics y cambios en SOV/SNA
4. **Recomendaciones** se generan automáticamente con 3 opciones por turno
5. **Resultado esperado:** +5-15% en intención de voto mediante movidas optimizadas

**Impacto potencial:** Reasignación eficiente de recursos (60-80% a movidas ganadoras), reducción de errores tácticos, y maximización de ventaja narrativa en tiempo real.


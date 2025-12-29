# RESUMEN_FUNCIONALIDADES.md

## Vista rapida

### MEDIOS (Media Analysis)
- **Proposito**: analisis neutral para prensa.
- **Flujo**: Tweets → Sentimiento (BETO) → Temas → Resumen (GPT-4o).
- **Output**: resumen narrativo, sentimiento, temas, graficos.

### CAMPANA (Campaign Agent)
- **Proposito**: estrategias para ganar votos.
- **Flujo**: Trending + Historial → Estrategias (GPT-4o) → Discurso.
- **Output**: estrategias, resumen ejecutivo, plan, discurso, temas.

### FORECAST (Pronostico Electoral)
- **Proposito**: metricas y proyecciones.
- **Metricas**:
  - **ICCE** = 50% Sentimiento + 50% Volumen Relativo (0-100)
  - **Momentum** = cambio suavizado del ICCE
  - **Forecast** = proyeccion Holt-Winters
- **Output**: ICCE historico, Momentum, Forecast con intervalos.

---

## Flujos simplificados

- **Medios**: Input → Tweets → Sentimiento → Temas → Resumen.
- **Campana**: Input → Tweets → Sentimiento/Temas → GPT Estrategico.
- **Forecast**: Input → ICCE → Momentum → Forecast.

---

## Comparacion rapida

| Producto | Enfoque | GPT | Principal salida |
| --- | --- | --- | --- |
| Medios | Descriptivo | Si | Resumen narrativo |
| Campana | Estrategico | Si | Plan + Discurso |
| Forecast | Cuantitativo | No | ICCE/Momentum |

---

## Ejemplos de uso

### Medios
```json
POST /api/media/analyze
{
  "location": "Bogota",
  "topic": "Seguridad"
}
```

### Campana
```json
POST /api/campaign/analyze
{
  "location": "Bogota",
  "theme": "Seguridad",
  "candidate_name": "Juan Perez"
}
```

### Forecast
```json
POST /api/forecast/dashboard
{
  "location": "Bogota",
  "candidate_name": "Juan Perez",
  "days_back": 30,
  "forecast_days": 14
}
```

---

## Dashboard unificado
- **Ruta**: `/dashboard`
- **Documento completo**: `FUNCIONALIDADES_EXPLICADAS.md`


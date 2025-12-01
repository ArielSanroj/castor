# Scripts de Prueba para Endpoints

Este directorio contiene scripts para probar y visualizar cómo se ven los datos de los endpoints de medios y campañas.

## Scripts Disponibles

### 1. `test_data_preview.py` - Previsualización con Datos de Ejemplo

Muestra cómo se ven los datos sin hacer llamadas reales al backend. Útil para entender la estructura de las respuestas.

```bash
python3 test_data_preview.py
```

**Salida:**
- Estructura completa JSON de las respuestas
- Resumen ejecutivo formateado
- Temas analizados
- Plan estratégico (para campañas)
- Discurso (para campañas)
- Metadata

### 2. `test_endpoints_simple.py` - Pruebas Rápidas

Hace llamadas reales a los endpoints y muestra solo la información clave de forma visual.

```bash
# Usar servidor por defecto (localhost:5001)
python3 test_endpoints_simple.py

# Especificar URL del servidor
python3 test_endpoints_simple.py http://localhost:5001
```

**Características:**
- Prueba ambos endpoints (medios y campañas)
- Muestra resumen ejecutivo
- Muestra temas analizados
- Muestra plan estratégico y discurso (campañas)
- Formato visual con emojis

### 3. `test_endpoints.py` - Pruebas Completas

Script completo con opciones avanzadas para pruebas detalladas.

```bash
# Probar ambos endpoints
python3 test_endpoints.py

# Solo probar endpoint de medios
python3 test_endpoints.py --media-only

# Solo probar endpoint de campañas
python3 test_endpoints.py --campaign-only

# Especificar URL del servidor
python3 test_endpoints.py --base-url http://localhost:5001
```

**Características:**
- Salida detallada con colores
- Opciones para probar endpoints individuales
- Guarda resultados completos en JSON
- Manejo de errores mejorado

## Endpoints Probados

### `/api/media/analyze` - Endpoint de Medios

**Payload de ejemplo:**
```json
{
  "location": "Bogotá",
  "topic": "Seguridad",
  "candidate_name": null,
  "politician": null,
  "max_tweets": 10,
  "time_window_days": 7,
  "language": "es"
}
```

**Respuesta incluye:**
- `summary`: Resumen ejecutivo con overview, key_stats, key_findings
- `sentiment_overview`: Distribución de sentimientos
- `topics`: Lista de temas analizados con sentimiento
- `chart_data`: Configuración para gráficos Chart.js
- `metadata`: Metadatos de la consulta

### `/api/campaign/analyze` - Endpoint de Campañas

**Payload de ejemplo:**
```json
{
  "location": "Bogotá",
  "theme": "Seguridad",
  "candidate_name": "Juan Pérez",
  "politician": null,
  "max_tweets": 50,
  "language": "es"
}
```

**Respuesta incluye:**
- `executive_summary`: Resumen ejecutivo con overview, key_findings, recommendations
- `topic_analyses`: Análisis detallado de temas con tweets de ejemplo
- `strategic_plan`: Plan estratégico con objetivos y acciones
- `speech`: Discurso completo con título, puntos clave y contenido
- `chart_data`: Configuración para gráficos Chart.js
- `metadata`: Metadatos de la consulta

## Requisitos

- Python 3.7+
- `requests` library: `pip install requests`

## Notas

- Los endpoints pueden tardar varios minutos en responder (análisis de tweets, llamadas a OpenAI, etc.)
- El timeout por defecto es de 120 segundos
- Asegúrate de que el servidor esté corriendo antes de ejecutar las pruebas
- Los scripts de prueba no requieren autenticación (los endpoints usan `@jwt_required(optional=True)`)

## Ejemplos de Uso

### Ver estructura de datos sin hacer llamadas reales:
```bash
python3 test_data_preview.py
```

### Probar con servidor local:
```bash
# Asegúrate de que el servidor esté corriendo
cd backend
python3 main.py

# En otra terminal
python3 test_endpoints_simple.py
```

### Probar solo el endpoint de medios:
```bash
python3 test_endpoints.py --media-only
```

### Guardar resultados en archivo:
```bash
python3 test_endpoints.py > resultados_prueba.json 2>&1
```

## Troubleshooting

### Error: Connection refused
- Verifica que el servidor esté corriendo
- Verifica que el puerto sea correcto (por defecto 5001)

### Error: Read timeout
- Los análisis pueden tardar mucho tiempo
- Considera reducir `max_tweets` en el payload
- Verifica que las APIs de Twitter y OpenAI estén funcionando

### Error: Missing required environment variables
- Asegúrate de tener configuradas las variables de entorno necesarias
- Verifica el archivo `.env` en la raíz del proyecto


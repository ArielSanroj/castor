# Smoke Test - Verificación de Integración con X/Twitter

Este documento explica cómo ejecutar un smoke test para verificar que el backend realmente responde con datos de X/Twitter y OpenAI.

## Requisitos Previos

1. **Archivo `.env`** en la raíz del proyecto con:
   ```bash
   TWITTER_BEARER_TOKEN=tu_token_de_twitter
   OPENAI_API_KEY=tu_key_de_openai
   ```

2. **Python y dependencias instaladas**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

## Opción 1: Script Automatizado (Recomendado)

El script `smoke_test.sh` hace todo automáticamente:

```bash
./smoke_test.sh
```

Este script:
- ✅ Verifica que exista `.env` con las variables necesarias
- ✅ Levanta el backend en background
- ✅ Espera a que esté listo (máximo 30 segundos)
- ✅ Ejecuta los tests contra el endpoint de medios
- ✅ Muestra los resultados
- ✅ Limpia el proceso del backend al finalizar

## Opción 2: Manual (Paso a Paso)

### Paso 1: Levantar el Backend

**Opción A: Usando el script helper:**
```bash
./start_backend.sh
```

**Opción B: Manualmente:**
```bash
cd backend
python main.py
```

El backend debería iniciar en `http://localhost:5001`

### Paso 2: Verificar que el Backend está Listo

En otra terminal, verifica el health endpoint:
```bash
curl http://localhost:5001/api/health
```

Deberías recibir una respuesta JSON con `"status": "ok"`.

### Paso 3: Ejecutar los Tests

**Desde la raíz del proyecto:**
```bash
python test_endpoints.py --base-url http://localhost:5001 --media-only
```

**O desde el directorio backend:**
```bash
cd backend
python test_endpoints.py --base-url http://localhost:5001 --media-only
```

### Paso 4: Ver Resultados

El script mostrará:
- ✅ Estructura de la respuesta
- ✅ Resumen ejecutivo
- ✅ Temas analizados
- ✅ Metadata (incluyendo tweets analizados)

## Qué Verificar

El smoke test hace una llamada real a:
1. **X/Twitter API** - Para obtener tweets sobre "Seguridad" en "Bogotá"
2. **OpenAI API** - Para generar el análisis y resumen

**Señales de éxito:**
- ✅ Status code 200
- ✅ Respuesta contiene `"success": true`
- ✅ `metadata.tweets_analyzed` > 0 (indica que se obtuvieron tweets reales)
- ✅ `summary` contiene texto generado por OpenAI
- ✅ `topics` contiene análisis de sentimiento

**Señales de error:**
- ❌ Status code != 200
- ❌ Error de autenticación (verifica tokens en `.env`)
- ❌ Rate limit de Twitter (espera unos minutos)
- ❌ Timeout (el backend puede estar tardando en responder)

## Troubleshooting

### El backend no inicia
- Verifica que el puerto 5001 esté libre: `lsof -i :5001`
- Revisa los logs en `backend.log` (si usaste el script automatizado)
- Verifica que las dependencias estén instaladas

### Error de autenticación
- Verifica que `TWITTER_BEARER_TOKEN` esté correcto en `.env`
- Verifica que `OPENAI_API_KEY` esté correcto en `.env`
- Asegúrate de que el `.env` esté en la raíz del proyecto (no en `backend/`)

### Rate Limit de Twitter
- El free tier de Twitter tiene límites estrictos (100 posts/mes)
- Si ves errores de rate limit, espera unos minutos o verifica tu cuota

### No se obtienen tweets
- Verifica que el token de Twitter sea válido
- Prueba con una ubicación diferente (ej: "Medellín" en lugar de "Bogotá")
- Verifica que haya tweets recientes sobre el tema en esa ubicación

## Endpoints Probados

El smoke test actualmente prueba:
- `POST /api/media/analyze` - Análisis de medios con datos de Twitter

Para probar otros endpoints:
```bash
# Solo endpoint de medios
python test_endpoints.py --base-url http://localhost:5001 --media-only

# Solo endpoint de campañas
python test_endpoints.py --base-url http://localhost:5001 --campaign-only

# Ambos endpoints
python test_endpoints.py --base-url http://localhost:5001
```

## Notas Importantes

⚠️ **Este test hace llamadas REALES a APIs externas:**
- Consume tu cuota de Twitter API
- Consume tu cuota de OpenAI API
- Puede generar costos si excedes los límites gratuitos

💡 **Para desarrollo local sin costos:**
- Usa mocks o datos de prueba
- Limita el número de tweets solicitados (`max_tweets: 5`)
- Usa el cache del backend (si está configurado)

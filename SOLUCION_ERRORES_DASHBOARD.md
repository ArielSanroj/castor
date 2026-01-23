# 🔧 Solución de Errores del Dashboard

## Problema Identificado

El dashboard estaba devolviendo errores 503/500 porque:
1. **OpenAI API Key inválida** - Causaba que el servicio no se inicializara
2. **Endpoints muy estrictos** - Fallaban completamente si algún servicio faltaba
3. **Sin manejo de errores resiliente** - No funcionaba parcialmente

## ✅ Cambios Aplicados

### 1. Media API (`/api/media/analyze`)
**Antes:** Requería tanto `pipeline` como `openai_svc`, si alguno faltaba → 503

**Ahora:** 
- Funciona sin OpenAI (usa resumen básico)
- Solo requiere `pipeline` para funcionar
- Si OpenAI falla, genera resumen fallback automático

### 2. Forecast API (`/api/forecast/dashboard`)
**Antes:** Lanzaba RuntimeError si servicios faltaban → 500

**Ahora:**
- Manejo de errores mejorado
- Mensajes de error más claros
- Retorna 503 con mensaje descriptivo si servicios no están disponibles

### 3. Trending API (`/api/campaign/trending`)
**Antes:** Si fallaba → 500 Internal Server Error

**Ahora:**
- Retorna lista vacía si falla (en lugar de error)
- Dashboard puede renderizar aunque no haya trending topics
- Logs de advertencia en lugar de errores fatales

## 🧪 Cómo Probar

### 1. Verificar que el servidor está corriendo
```bash
curl http://localhost:5001/api/health
```

### 2. Probar el dashboard
1. Abre `http://localhost:5001/dashboard`
2. Llena el formulario o usa "Prueba con un ejemplo"
3. Haz clic en "Generar dashboard"

### 3. Qué deberías ver ahora

**Si los servicios están disponibles:**
- ✅ KPIs completos
- ✅ Resumen narrativo (con OpenAI si está configurado)
- ✅ Gráfico forecast
- ✅ Streams con datos
- ✅ Panel geográfico

**Si OpenAI no está configurado:**
- ✅ KPIs básicos (ICCE, Momentum si hay datos)
- ✅ Resumen básico (sin OpenAI)
- ⚠️ Streams pueden estar vacíos o con datos básicos
- ✅ Dashboard funciona parcialmente

**Si Twitter/Sentiment no están disponibles:**
- ⚠️ KPIs pueden mostrar "-"
- ⚠️ Gráficos vacíos
- ⚠️ Streams vacíos
- ✅ Dashboard carga sin errores fatales

## 🔍 Verificar Configuración

### Variables de Entorno Necesarias

Para funcionalidad completa, configura en `.env`:

```bash
# Requerido para análisis de tweets
TWITTER_BEARER_TOKEN=tu_token_aqui

# Requerido para resúmenes con IA (opcional, tiene fallback)
OPENAI_API_KEY=tu_api_key_aqui

# Opcional para persistencia
DATABASE_URL=postgresql://user:pass@localhost:5432/castor
```

### Verificar Estado de Servicios

```bash
# Health check
curl http://localhost:5001/api/health

# Ver logs del servidor
tail -f backend.log
```

## 📊 Comportamiento Esperado

### Con Todos los Servicios
```
✅ Media API: 200 OK (con resumen OpenAI)
✅ Forecast API: 200 OK (con ICCE y forecast)
✅ Trending API: 200 OK (con temas trending)
✅ Dashboard: Renderiza completamente
```

### Sin OpenAI (pero con Twitter/Sentiment)
```
✅ Media API: 200 OK (resumen básico)
✅ Forecast API: 200 OK (con ICCE y forecast)
✅ Trending API: 200 OK (con temas trending)
✅ Dashboard: Renderiza con datos básicos
```

### Sin Twitter/Sentiment
```
⚠️ Media API: 503 (servicios no disponibles)
⚠️ Forecast API: 503 (servicios no disponibles)
✅ Trending API: 200 OK (lista vacía)
⚠️ Dashboard: Carga pero muestra mensajes de "sin datos"
```

## 🐛 Troubleshooting

### Si sigues viendo errores 503:

1. **Verifica que los servicios se inicializaron:**
   ```bash
   tail -50 backend.log | grep "initialized"
   ```

2. **Verifica variables de entorno:**
   ```bash
   cd backend
   python3 -c "from config import Config; print('TWITTER:', bool(Config.TWITTER_BEARER_TOKEN)); print('OPENAI:', bool(Config.OPENAI_API_KEY))"
   ```

3. **Prueba endpoints individuales:**
   ```bash
   # Health
   curl http://localhost:5001/api/health
   
   # Trending (más simple)
   curl "http://localhost:5001/api/campaign/trending?location=Colombia&limit=3"
   ```

### Si el dashboard carga pero no muestra datos:

- Esto es **normal** si no hay tweets disponibles o servicios no están configurados
- El dashboard debería mostrar mensajes como "Sin datos disponibles" en lugar de errores
- Verifica los logs para ver qué está pasando

## ✅ Checklist de Funcionamiento

- [ ] Servidor corriendo en puerto 5001
- [ ] Health check responde 200
- [ ] Dashboard carga sin errores en consola
- [ ] Formulario funciona
- [ ] Botón "Generar dashboard" funciona
- [ ] Si hay datos: KPIs, gráficos y streams se muestran
- [ ] Si no hay datos: Mensajes informativos en lugar de errores

---

**Última actualización:** 2025-12-28
**Estado:** Endpoints mejorados para ser más resilientes





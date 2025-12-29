# 🧪 Guía de Pruebas - Unified Dashboard

## ✅ Estado Actual

**Servidor:** ✅ Corriendo en `http://localhost:5001`
**Dashboard:** ✅ Accesible y funcional
**APIs:** ⚠️ Requieren configuración completa

---

## 🌐 Dónde Probar el Dashboard

### 1. **Dashboard Web (Recomendado)**
```
URL: http://localhost:5001/dashboard
```

**Pasos:**
1. Abre tu navegador (Chrome, Firefox, Safari, etc.)
2. Ve a la URL arriba
3. Haz clic en el botón **"Prueba con un ejemplo"** para llenar el formulario automáticamente
4. Haz clic en **"Generar dashboard"**
5. El dashboard mostrará:
   - KPIs (ICCE, Momentum, Sentiment, Volume)
   - Resumen narrativo
   - Gráfico de forecast
   - Streams de medios, campaña y forecast
   - Panel geográfico

### 2. **APIs Individuales**

#### Health Check
```bash
curl http://localhost:5001/api/health
```

#### Media Analyze
```bash
curl -X POST http://localhost:5001/api/media/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Colombia",
    "topic": "Seguridad",
    "max_tweets": 15,
    "time_window_days": 30,
    "language": "es"
  }'
```

#### Forecast Dashboard
```bash
curl -X POST http://localhost:5001/api/forecast/dashboard \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Colombia",
    "days_back": 30,
    "forecast_days": 14
  }'
```

#### Campaign Trending
```bash
curl "http://localhost:5001/api/campaign/trending?location=Colombia&limit=6"
```

---

## 🧪 Scripts de Prueba Automatizados

### Prueba Completa
```bash
python3 test_unified_dashboard.py
```

### Prueba Simple (Solo conectividad)
```bash
python3 test_dashboard_simple.py
```

---

## 🔧 Reiniciar el Servidor

### Opción 1: Script Automático
```bash
./start_backend.sh
```

### Opción 2: Manual
```bash
# Detener servidor actual
kill $(lsof -ti:5001) 2>/dev/null || true

# Iniciar servidor
cd backend
python3 main.py
```

### Opción 3: En Background
```bash
cd backend
python3 main.py &
```

---

## ⚙️ Configuración Requerida

Para que las APIs funcionen completamente, necesitas configurar en `.env`:

```bash
# Requerido para análisis de medios
OPENAI_API_KEY=tu_api_key_aqui

# Requerido para obtener tweets
TWITTER_BEARER_TOKEN=tu_token_aqui

# Requerido para persistencia (opcional para pruebas básicas)
DATABASE_URL=postgresql://user:pass@localhost:5432/castor
```

**Nota:** El dashboard web funciona sin estas configuraciones, pero las APIs pueden devolver errores.

---

## 📊 Endpoints del Dashboard

El dashboard unificado hace 3 llamadas paralelas:

1. **`POST /api/media/analyze`** - Análisis de medios
2. **`POST /api/forecast/dashboard`** - Pronóstico y métricas
3. **`GET /api/campaign/trending`** - Temas trending

Todas se ejecutan en paralelo usando `Promise.allSettled`, así que si una falla, las otras continúan.

---

## 🐛 Troubleshooting

### El servidor no inicia
```bash
# Verificar si el puerto está ocupado
lsof -i :5001

# Matar proceso en el puerto
kill $(lsof -ti:5001)
```

### Las APIs devuelven 503/500
- Verifica que las variables de entorno estén configuradas
- Revisa los logs del servidor: `tail -f backend.log`
- El dashboard seguirá funcionando con datos limitados

### El dashboard no carga
- Verifica que el servidor esté corriendo: `curl http://localhost:5001/api/health`
- Abre la consola del navegador (F12) para ver errores JavaScript
- Verifica que los archivos estáticos se sirvan correctamente

---

## 📝 Notas Importantes

1. **El dashboard funciona parcialmente** sin todas las APIs funcionando
2. **El panel geográfico** usa datos reales si están disponibles, o genera un fallback determinístico
3. **Los gráficos** se renderizan con Chart.js y funcionan si hay datos de forecast
4. **El botón "Prueba con un ejemplo"** llena el formulario con datos de prueba

---

## ✅ Checklist de Pruebas

- [ ] Servidor corriendo en puerto 5001
- [ ] Dashboard accesible en `/dashboard`
- [ ] Health check responde 200
- [ ] Formulario del dashboard funciona
- [ ] Botón "Prueba con un ejemplo" funciona
- [ ] APIs responden (pueden devolver errores si falta config)
- [ ] Gráficos se renderizan (si hay datos)
- [ ] Panel geográfico muestra datos

---

## 🎯 Próximos Pasos

1. Configurar variables de entorno para APIs completas
2. Probar con datos reales de Twitter
3. Verificar que el forecast genere proyecciones
4. Validar que el panel geográfico muestre distribución real

---

**Última actualización:** $(date)
**Servidor:** http://localhost:5001
**Dashboard:** http://localhost:5001/dashboard


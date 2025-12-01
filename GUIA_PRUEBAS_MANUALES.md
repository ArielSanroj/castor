# 🧪 Guía de Pruebas Manuales - CASTOR API

Guía rápida para probar los endpoints de la API de CASTOR usando `curl`.

---

## 🔧 Prerequisitos

1. Servidor corriendo en `http://localhost:5001`
2. `curl` instalado
3. `jq` instalado (opcional, para formatear JSON)

---

## ✅ Health Check

### Verificar estado del servidor
```bash
curl http://localhost:5001/api/health | jq
```

### Ver estadísticas de uso de Twitter
```bash
curl http://localhost:5001/api/twitter-usage | jq
```

---

## 🌐 Web Routes

### Landing Page
```bash
curl http://localhost:5001/webpage
```

### CASTOR Medios
```bash
curl http://localhost:5001/media
```

### CASTOR Campañas
```bash
curl http://localhost:5001/campaign
```

---

## 📊 Análisis de Medios

### Análisis básico
```bash
curl -X POST http://localhost:5001/api/media/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Bogotá",
    "theme": "Seguridad",
    "max_tweets": 15
  }' | jq
```

### Análisis con tema específico
```bash
curl -X POST http://localhost:5001/api/media/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Medellín",
    "theme": "Educación",
    "max_tweets": 20
  }' | jq
```

---

## 🎯 Análisis de Campaña

### Análisis completo
```bash
curl -X POST http://localhost:5001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Bogotá",
    "theme": "Seguridad",
    "candidate_name": "Juan Pérez",
    "politician": "@juanperez",
    "max_tweets": 15
  }' | jq
```

**Nota:** Requiere `max_tweets >= 10` y configuración de Twitter API.

---

## 💬 Chat con IA

### Pregunta simple
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "¿Qué es CASTOR?",
    "context": {}
  }' | jq
```

### Pregunta con contexto
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "¿Cómo puedo mejorar mi campaña?",
    "context": {
      "location": "Bogotá",
      "theme": "Seguridad"
    }
  }' | jq
```

---

## 🎯 Análisis de Campaña (Campaign Agent)

### Análisis de votos
```bash
curl -X POST http://localhost:5001/api/campaign/analyze-votes \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Bogotá",
    "theme": "Seguridad",
    "candidate_name": "Test Candidate",
    "max_tweets": 15
  }' | jq
```

### Análisis completo de campaña
```bash
curl -X POST http://localhost:5001/api/campaign/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Bogotá",
    "theme": "Seguridad",
    "candidate_name": "Test Candidate",
    "max_tweets": 15
  }' | jq
```

---

## 🔍 Validación de Errores

### Endpoint inválido (debe retornar 404)
```bash
curl http://localhost:5001/api/invalid-endpoint
```

### Request inválido (max_tweets < 10)
```bash
curl -X POST http://localhost:5001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Bogotá",
    "theme": "Seguridad",
    "max_tweets": 5
  }' | jq
```

---

## 📋 Temas del PND Disponibles

Los siguientes temas están disponibles para análisis:

1. Seguridad
2. Infraestructura
3. Gobernanza y Transparencia
4. Educación
5. Salud
6. Igualdad y Equidad
7. Paz y Reinserción
8. Economía y Empleo
9. Medio Ambiente y Cambio Climático
10. Alimentación

---

## 🔐 Autenticación (Opcional)

Algunos endpoints pueden requerir autenticación JWT. Para usar autenticación:

```bash
# Primero obtener token (si hay endpoint de login)
TOKEN="tu_token_jwt_aqui"

# Usar token en requests
curl -X POST http://localhost:5001/api/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{...}'
```

---

## 📊 Ejemplos de Respuestas Exitosas

### Health Check
```json
{
  "service": "CASTOR ELECCIONES API",
  "status": "ok",
  "timestamp": "2025-11-30T13:06:47.939528",
  "version": "1.0.0"
}
```

### Media Analysis
```json
{
  "success": true,
  "summary": {
    "overview": "...",
    "key_findings": [...],
    "key_stats": [...]
  },
  "sentiment_overview": {
    "positive": 0.45,
    "neutral": 0.30,
    "negative": 0.25
  },
  "topics": [...],
  "chart_data": {...}
}
```

---

## 🐛 Troubleshooting

### El servidor no responde
```bash
# Verificar que el servidor esté corriendo
curl http://localhost:5001/api/health

# Si no responde, iniciar servidor
cd backend
python3 main.py
```

### Error de conexión
```bash
# Verificar puerto
lsof -ti:5001

# Si está ocupado, usar otro puerto
export PORT=5002
python3 backend/main.py
```

### Error de validación
- Verificar que `max_tweets >= 10`
- Verificar que `location` sea una cadena válida
- Verificar que `theme` sea uno de los temas del PND

---

## 📝 Notas

- Todos los endpoints POST requieren `Content-Type: application/json`
- `max_tweets` debe ser >= 10 para la mayoría de endpoints
- Algunos endpoints requieren configuración de servicios externos (Twitter API, OpenAI)
- El sistema tiene rate limiting activo (5-10 requests por minuto dependiendo del endpoint)

---

**Última actualización:** 30 de Noviembre, 2025


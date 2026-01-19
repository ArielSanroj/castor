# 🚀 Guía de Deployment - CASTOR ELECCIONES

## Opciones de Deployment

### 1. Render.com (Recomendado para MVP)

#### Backend

1. **Crear cuenta en Render**
   - Ir a https://render.com
   - Conectar repositorio GitHub

2. **Crear Web Service**
   - New → Web Service
   - Seleccionar repositorio
   - Configuración:
     - **Build Command**: `cd backend && pip install -r requirements.txt`
     - **Start Command**: `cd backend && python main.py`
     - **Environment**: Python 3

3. **Variables de Entorno**
   - Agregar todas las variables de `.env.example`
   - Configurar `FLASK_ENV=production`
   - `DEBUG=False`

4. **Health Check**
   - Path: `/api/health`

#### Frontend (cuando esté listo)

1. **Crear Static Site**
   - New → Static Site
   - Build Command: `npm install && npm run build`
   - Publish Directory: `out` o `dist`

### 2. Heroku

#### Backend

```bash
# Instalar Heroku CLI
heroku login

# Crear app
heroku create castor-elecciones-api

# Configurar variables
heroku config:set SECRET_KEY=your-secret-key
heroku config:set TWITTER_BEARER_TOKEN=your-token
# ... (todas las variables)

# Deploy
git push heroku main
```

### 3. Docker (Recomendado para Producción)

#### Dockerfile Backend

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 5001

CMD ["python", "main.py"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "5001:5001"
    environment:
      - FLASK_ENV=production
    env_file:
      - .env
    volumes:
      - ./backend:/app
```

### 4. AWS (Para Escala)

#### Opciones:
- **ECS/Fargate**: Contenedores
- **Elastic Beanstalk**: PaaS
- **EC2**: Instancias virtuales

#### Configuración Recomendada:
- **Load Balancer**: ALB
- **Auto Scaling**: Basado en CPU/Memoria
- **RDS**: Para base de datos (si se migra de Supabase)
- **ElastiCache**: Redis para caché

## Checklist Pre-Deployment

- [ ] Variables de entorno configuradas
- [ ] `DEBUG=False` en producción
- [ ] `SECRET_KEY` fuerte y único
- [ ] CORS configurado correctamente
- [ ] Rate limiting implementado
- [ ] Tests pasando
- [ ] Logging configurado
- [ ] Health check funcionando
- [ ] Base de datos migrada (Supabase)
- [ ] SSL/HTTPS configurado
- [ ] Monitoring configurado

## Variables de Entorno Críticas

```bash
# Producción
FLASK_ENV=production
DEBUG=False
SECRET_KEY=<generar-con-secrets-token>
JWT_SECRET_KEY=<generar-con-secrets-token>

# APIs
TWITTER_BEARER_TOKEN=<token>
OPENAI_API_KEY=<key>
SUPABASE_URL=<url>
SUPABASE_KEY=<key>
TWILIO_ACCOUNT_SID=<sid>
TWILIO_AUTH_TOKEN=<token>
```

## Monitoreo Post-Deployment

1. **Health Checks**
   - Verificar `/api/health` periódicamente
   - Configurar alertas

2. **Logs**
   - Revisar logs de errores
   - Monitorear rate limits

3. **Métricas**
   - Tiempo de respuesta
   - Tasa de errores
   - Uso de recursos

## Rollback Plan

1. Mantener versión anterior en branch
2. Revertir deployment si hay problemas críticos
3. Tener backup de base de datos

## Escalabilidad

### Horizontal Scaling
- Múltiples instancias Flask
- Load balancer
- Session storage compartido (Redis)

### Vertical Scaling
- Aumentar recursos de servidor
- Optimizar queries de base de datos
- Caché de modelos ML


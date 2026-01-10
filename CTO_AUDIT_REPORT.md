# CASTOR ELECCIONES - Reporte de Auditoría CTO

**Fecha**: 2026-01-10
**Proyecto**: CASTOR ELECCIONES - Plataforma de Análisis Electoral
**Stack**: Python/Flask + PostgreSQL + BETO/OpenAI + HTML/JS
**Auditor**: CTO Review

---

## RESUMEN EJECUTIVO

CASTOR ELECCIONES es una plataforma de inteligencia artificial para análisis de campañas electorales en Colombia. El proyecto tiene una arquitectura sólida pero presenta **42 issues identificados** que requieren atención, clasificados por severidad.

| Severidad | Cantidad | Descripción |
|-----------|----------|-------------|
| **CRÍTICA** | 6 | Seguridad y estabilidad inmediata |
| **ALTA** | 12 | Funcionalidad y rendimiento |
| **MEDIA** | 15 | Mejores prácticas y mantenibilidad |
| **BAJA** | 9 | Optimizaciones y documentación |

---

## 1. ISSUES CRÍTICOS (Severidad: CRÍTICA)

### 1.1 SECRET_KEY por defecto en producción
**Archivo**: `backend/config.py:19`
```python
SECRET_KEY: str = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
```
**Problema**: Si SECRET_KEY no está configurada, usa un valor predecible que compromete JWT y sesiones.
**Fix requerido**:
```python
SECRET_KEY: str = os.getenv('SECRET_KEY') or ''
# Y en validate():
if not cls.SECRET_KEY or len(cls.SECRET_KEY) < 32:
    raise ValueError("SECRET_KEY must be set to a secure value (min 32 chars)")
```

### 1.2 Archivo `.env` con credenciales en el repositorio
**Archivos detectados**:
- `.env` (contiene credenciales reales)
- `backend/app/.env` (duplicado)

**Problema**: Credenciales de APIs (OpenAI, Twitter, Twilio) expuestas.
**Fix requerido**:
1. Agregar a `.gitignore`: `.env`, `*.env`
2. Rotar TODAS las credenciales expuestas
3. Usar secrets management (ej: AWS Secrets Manager, Vault)

### 1.3 SQL Injection potencial en filtros
**Archivo**: `backend/services/database_service.py:218`
```python
query = query.filter(TrendingTopic.location == location)
```
**Problema**: Aunque SQLAlchemy parametriza, hay queries con `text()` sin sanitizar.
**Fix requerido**: Auditar todas las queries con `text()` y usar parámetros bound.

### 1.4 Session management sin context manager
**Archivo**: `backend/services/database_service.py:64-97`
```python
session = self.get_session()
try:
    # ... operaciones
finally:
    session.close()
```
**Problema**: Si ocurre excepción antes del finally, la sesión queda abierta (connection leak).
**Fix requerido**:
```python
from contextlib import contextmanager

@contextmanager
def get_session(self):
    session = self.SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

# Uso:
with self.get_session() as session:
    # operaciones
```

### 1.5 Métodos NotImplementedError en producción
**Archivo**: `backend/services/openai_service.py:421-440`
```python
def generate_executive_summary_new(...):
    raise NotImplementedError("Implementa generate_executive_summary_new según tu lógica")
```
**Problema**: 3 métodos que lanzan excepciones en producción.
**Fix requerido**: Implementar o eliminar estos métodos muertos.

### 1.6 Circuit Breaker sin persistencia
**Archivo**: `backend/utils/circuit_breaker.py:191-201`
**Problema**: Los circuit breakers son globales en memoria. En multi-proceso (gunicorn workers), cada worker tiene estado independiente.
**Fix requerido**: Usar Redis para compartir estado del circuit breaker entre workers.

---

## 2. ISSUES DE SEVERIDAD ALTA

### 2.1 Archivos deprecados sin eliminar
**Archivos detectados**:
- `main.py.deprecated.bak`
- `backend/services/supabase_service.py.deprecated.bak`
- `backend/services/supabase_service.py` (marcado como eliminado en git)

**Impacto**: Confusión en el codebase, posibles imports erróneos.
**Fix**: Eliminar archivos deprecated completamente.

### 2.2 Rate Limiting insuficiente para Twitter Free Tier
**Archivo**: `backend/services/twitter_service.py:103-140`
**Problema**: El límite de 100 posts/mes de Twitter Free tier puede agotarse rápidamente con los límites actuales de 3/día.
**Fix requerido**: Implementar contador persistente en Redis:
```python
def can_make_request(self) -> bool:
    monthly_count = redis.get('twitter:monthly_count') or 0
    return monthly_count < 100
```

### 2.3 Imports no usados en múltiples archivos
**Ejemplos**:
- `backend/app/routes/analysis.py:9`: `from pydantic import ValidationError` (ya capturado)
- `backend/app/routes/forecast.py:7`: `from pydantic import ValidationError` (no usado directamente)

**Fix**: Ejecutar `autoflake --remove-all-unused-imports -i **/*.py`

### 2.4 Servicios inicializados globalmente (anti-pattern)
**Archivo**: `backend/app/routes/analysis.py:27-32`
```python
twitter_service = None
sentiment_service = None
# ... globals
```
**Problema**: Variables globales mutables causan race conditions.
**Fix**: Usar Flask `g` object o dependency injection.

### 2.5 Caché sin invalidación
**Archivo**: `backend/utils/cache.py`
**Problema**: No hay mecanismo para invalidar caché cuando los datos cambian.
**Fix requerido**: Agregar:
```python
def invalidate(key_pattern: str) -> int:
    if redis_client:
        keys = redis_client.keys(key_pattern)
        return redis_client.delete(*keys) if keys else 0
    return 0
```

### 2.6 Logging de errores con información sensible
**Archivo**: `backend/app/routes/auth.py:117-122`
```python
return jsonify({
    'error': 'Internal server error',
    'message': str(e)  # Expone stack trace
}), 500
```
**Fix**: En producción, no exponer `str(e)`:
```python
if Config.DEBUG:
    return jsonify({'error': str(e)}), 500
return jsonify({'error': 'Internal server error'}), 500
```

### 2.7 Timeout insuficiente para operaciones ML
**Archivo**: `backend/config.py:45`
```python
OPENAI_TIMEOUT_SECONDS: int = int(os.getenv('OPENAI_TIMEOUT_SECONDS', '15'))
```
**Problema**: 15 segundos puede ser insuficiente para generación de contenido largo.
**Fix**: Aumentar a 30-60 segundos.

### 2.8 Falta validación de tipos en endpoints
**Archivo**: `backend/app/routes/forecast.py:113-124`
```python
days_back = payload.get("days_back", 30)  # Podría ser string
```
**Fix**: Usar Pydantic para validación:
```python
from pydantic import BaseModel, Field

class ForecastRequest(BaseModel):
    location: str
    days_back: int = Field(default=30, ge=7, le=90)
```

### 2.9 Endpoints duplicados funcionalmente
**Archivos**:
- `/api/forecast/dashboard` (POST)
- `/api/forecast/icce` + `/api/forecast/momentum` + `/api/forecast/forecast`

**Problema**: El dashboard hace 3 llamadas que podrían consolidarse.
**Fix**: Usar endpoint único con parámetros opcionales.

### 2.10 Frontend sin minificación
**Archivo**: `static/js/unified_dashboard.js` (26K+ tokens)
**Problema**: JavaScript sin minificar impacta tiempo de carga.
**Fix**: Implementar build pipeline con Vite/Webpack.

### 2.11 CORS configurado incorrectamente
**Archivo**: `backend/app/__init__.py:71-77`
```python
cors.init_app(app, resources={
    r"/api/*": {
        "origins": Config.CORS_ORIGINS,  # Por defecto: 'http://localhost:3000'
```
**Problema**: En producción, puede bloquear requests legítimos.
**Fix**: Agregar dominio de producción a CORS_ORIGINS.

### 2.12 Modelo BETO cargado en cada request (potencial)
**Archivo**: `backend/services/model_singleton.py`
**Problema**: Si el singleton no funciona correctamente en multi-proceso, el modelo se recarga.
**Fix**: Verificar comportamiento con `gunicorn --preload`.

---

## 3. ISSUES DE SEVERIDAD MEDIA

### 3.1 Código duplicado en clasificación de topics
**Archivos**:
- `backend/app/routes/analysis.py:346-435` (`_classify_tweets_by_topic`)
- `backend/services/twitter_service.py:292-307` (`_get_topic_keywords`)

**Fix**: Consolidar en un servicio único `TopicService`.

### 3.2 Falta de type hints consistentes
**Ejemplos**:
```python
def _parse_analysis_request(req_data):  # Sin hints
def get_services():  # Retorna tuple sin tipado
```
**Fix**: Agregar type hints:
```python
def _parse_analysis_request(req_data: dict) -> tuple[AnalysisRequest | None, tuple | None]:
```

### 3.3 Tests con mocks incompletos
**Archivo**: `backend/tests/test_services.py:54-78`
**Problema**: Tests de SentimentService mockean incorrectamente AutoTokenizer.
**Fix**: Usar `@patch.object` en lugar de `@patch` directo.

### 3.4 Configuración de logging inconsistente
**Archivo**: `backend/app/__init__.py:89-96`
```python
logging.basicConfig(
    handlers=[
        logging.FileHandler(Config.LOG_FILE) if Config.LOG_FILE else logging.StreamHandler()
    ]
)
```
**Problema**: Solo un handler activo a la vez.
**Fix**: Permitir múltiples handlers:
```python
handlers = [logging.StreamHandler()]
if Config.LOG_FILE:
    handlers.append(logging.FileHandler(Config.LOG_FILE))
```

### 3.5 Uso de `datetime.utcnow()` deprecado
**Múltiples archivos** (Python 3.12+):
```python
from datetime import datetime, timezone
datetime.now(timezone.utc)  # En lugar de datetime.utcnow()
```

### 3.6 Falta de índices en queries frecuentes
**Archivo**: `backend/models/database.py`
**Tablas sin índices óptimos**:
- `analyses.created_at` - falta índice para ordenamiento
- `campaign_actions.user_id + roi` - falta índice compuesto

### 3.7 JSON responses inconsistentes
**Problema**: Algunos endpoints retornan `{"success": true, ...}`, otros solo datos.
**Fix**: Estandarizar formato de respuesta.

### 3.8 Error handling genérico
**Archivo**: `backend/services/twitter_service.py:193-201`
```python
except Exception as e:
    logger.error(f"Error searching tweets: {e}")
    break
```
**Fix**: Manejar excepciones específicas.

### 3.9 Hardcoded values
**Archivo**: `backend/services/twitter_service.py:109`
```python
TWITTER_MIN_RESULTS = 10
```
**Fix**: Mover a Config.

### 3.10 Frontend sin lazy loading
**Archivo**: `static/js/unified_dashboard.js`
**Problema**: Todo el JS carga de una vez.
**Fix**: Implementar code splitting.

### 3.11 Falta de health check profundo
**Archivo**: `backend/app/routes/health.py`
**Problema**: Health check no verifica conectividad a servicios externos.
**Fix**: Agregar checks para DB, Redis, APIs externas.

### 3.12 Manejo de timezone inconsistente
**Problema**: Algunas fechas usan UTC, otras no especifican timezone.
**Fix**: Usar timezone-aware datetimes consistentemente.

### 3.13 Falta de compression en responses
**Fix**: Agregar Flask-Compress:
```python
from flask_compress import Compress
compress = Compress()
compress.init_app(app)
```

### 3.14 Pool de conexiones no optimizado
**Archivo**: `backend/services/database_service.py:28-33`
```python
self.engine = create_engine(
    Config.DATABASE_URL,
    pool_size=10,  # Hardcoded
```
**Fix**: Hacer configurable vía env vars.

### 3.15 Imports circulares potenciales
**Archivos**: `backend/app/routes/analysis.py` importa servicios que importan Config.
**Fix**: Usar imports locales o reestructurar.

---

## 4. ISSUES DE SEVERIDAD BAJA

### 4.1 Comentarios en español/inglés mezclados
**Fix**: Estandarizar a inglés para código, español para user-facing.

### 4.2 Archivos `__init__.py` vacíos o mínimos
**Fix**: Agregar `__all__` exports explícitos.

### 4.3 Requirements.txt sin versiones pinned
**Archivo**: `requirements.txt`
**Fix**: Pinear versiones exactas: `flask==3.0.0`

### 4.4 Falta de pre-commit hooks
**Fix**: Agregar `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
```

### 4.5 Docstrings incompletos
**Ejemplo**: `backend/app/services/analysis_core.py` tiene docstrings parciales.

### 4.6 Magic numbers en frontend
**Archivo**: `static/js/unified_dashboard.js:184-194`
```javascript
if (daysBack < 7 || daysBack > 90) {
```
**Fix**: Usar constantes nombradas.

### 4.7 Console.log en producción
**Archivo**: `static/js/unified_dashboard.js:274`
```javascript
console.error(err);
```
**Fix**: Usar logging condicional.

### 4.8 CSS inline en JavaScript
**Archivo**: `static/js/unified_dashboard.js:61`
```javascript
userMsg.style.cssText = "background: rgba(255,106,61,0.15)...";
```
**Fix**: Usar clases CSS.

### 4.9 Falta de PWA capabilities
**Fix**: Agregar manifest.json y service worker para offline support.

---

## 5. ANÁLISIS DE ARQUITECTURA

### Fortalezas
1. **Separación de capas clara**: Routes → Services → Models
2. **Uso de Factory Pattern**: `create_app()` bien implementado
3. **Circuit breaker y retry logic**: Resiliencia implementada
4. **Caché multinivel**: Redis + in-memory fallback
5. **Validación con Pydantic**: Schemas bien definidos

### Debilidades
1. **No hay message queue**: RQ configurado pero no usado activamente
2. **Falta de API versioning**: `/api/` sin versión
3. **No hay rate limiting por usuario**: Solo por IP
4. **Monolito sin boundaries claros**: Difícil de escalar horizontalmente

### Recomendaciones de Escalabilidad

```
┌─────────────────────────────────────────────────────────────┐
│                     ARQUITECTURA PROPUESTA                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Nginx     │───>│   Flask     │───>│   Redis     │     │
│  │   (LB)      │    │   Workers   │    │   Cache     │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                  │                  │              │
│         │           ┌──────┴──────┐          │              │
│         │           │             │          │              │
│         │    ┌──────▼──────┐ ┌────▼────┐     │              │
│         │    │  PostgreSQL │ │  RQ     │     │              │
│         │    │  (Primary)  │ │ Workers │     │              │
│         │    └─────────────┘ └─────────┘     │              │
│         │                                    │              │
│  ┌──────▼──────────────────────────────────┐│              │
│  │              CDN (Static Assets)         ││              │
│  └──────────────────────────────────────────┘│              │
│                                              │              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. COBERTURA DE TESTS

### Estado Actual
- **Tests unitarios**: 4 archivos, ~15 tests
- **Coverage estimado**: <30%
- **Tests de integración**: Incompletos
- **Tests E2E**: No existen

### Plan para 80% Coverage

| Área | Tests Requeridos | Prioridad |
|------|------------------|-----------|
| Services | 50+ tests | ALTA |
| Routes | 30+ tests | ALTA |
| Utils | 15+ tests | MEDIA |
| Models | 10+ tests | MEDIA |
| Integration | 20+ tests | ALTA |

### Configuración pytest recomendada
```ini
# pytest.ini
[pytest]
testpaths = backend/tests
python_files = test_*.py
python_functions = test_*
addopts = --cov=backend --cov-report=html --cov-fail-under=80
```

---

## 7. ENDPOINTS Y CONECTIVIDAD

### Endpoints Verificados

| Endpoint | Método | Estado | Notas |
|----------|--------|--------|-------|
| `/` | GET | ✅ OK | Landing page |
| `/api/health` | GET | ✅ OK | Health check |
| `/api/analyze` | POST | ⚠️ | Depende de Twitter API |
| `/api/forecast/dashboard` | POST | ⚠️ | Depende de servicios externos |
| `/api/auth/register` | POST | ✅ OK | Funcional |
| `/api/auth/login` | POST | ✅ OK | Funcional |
| `/api/media/analyze` | POST | ⚠️ | Depende de Twitter API |
| `/api/campaign/analyze` | POST | ⚠️ | Depende de OpenAI API |
| `/api/leads/demo-request` | POST | ✅ OK | Funcional |

### Endpoints Muertos o No Implementados
- `generate_executive_summary_new` - NotImplementedError
- `generate_strategic_plan_new` - NotImplementedError
- `generate_speech_new` - NotImplementedError

---

## 8. ROADMAP DE MEJORAS

### Fase 1: Crítico (1-2 semanas)
1. [ ] Rotar todas las credenciales expuestas
2. [ ] Implementar SECRET_KEY seguro
3. [ ] Corregir session management con context managers
4. [ ] Eliminar archivos deprecated
5. [ ] Agregar .env a .gitignore

### Fase 2: Alta Prioridad (2-4 semanas)
1. [ ] Implementar rate limiting persistente para Twitter
2. [ ] Agregar dependency injection para servicios
3. [ ] Implementar invalidación de caché
4. [ ] Corregir logging para producción
5. [ ] Aumentar timeouts para ML

### Fase 3: Optimización (4-8 semanas)
1. [ ] Consolidar código duplicado
2. [ ] Agregar type hints completos
3. [ ] Implementar test coverage 80%
4. [ ] Agregar health checks profundos
5. [ ] Implementar API versioning

### Fase 4: Escalabilidad (8-12 semanas)
1. [ ] Migrar a arquitectura con RQ workers
2. [ ] Implementar CDN para assets
3. [ ] Agregar métricas y APM
4. [ ] Implementar blue-green deployment
5. [ ] Agregar rate limiting por usuario

---

## 9. HERRAMIENTAS RECOMENDADAS

### Linting y Formateo
```bash
# Instalar
pip install black flake8 mypy isort

# Ejecutar
black backend/
flake8 backend/
mypy backend/
isort backend/
```

### CI/CD Pipeline (GitHub Actions)
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov=backend --cov-fail-under=80
      - run: black --check backend/
      - run: flake8 backend/
```

---

## 10. CONCLUSIÓN

CASTOR ELECCIONES tiene una base sólida pero requiere atención inmediata en:

1. **Seguridad**: Credenciales expuestas y SECRET_KEY débil
2. **Estabilidad**: Session management y error handling
3. **Escalabilidad**: Rate limiting y caché persistente

El proyecto está en un estado viable para MVP pero **no está listo para producción** sin abordar los issues críticos.

**Recomendación**: Priorizar Fase 1 antes de cualquier despliegue público.

---

*Generado por CTO Audit - 2026-01-10*

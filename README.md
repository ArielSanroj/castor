# CASTOR ELECCIONES

**Campaña Electoral Inteligente** - Herramienta avanzada de inteligencia artificial para análisis político en tiempo real.

## 🎯 Descripción

CASTOR ELECCIONES es una plataforma web full-stack que permite a candidatos, gerentes de campaña y estrategas analizar en tiempo real el sentimiento ciudadano en X (Twitter) sobre los 10 ejes clave del Plan Nacional de Desarrollo (PND 2022-2026). Con una precisión del 99% en análisis de sentimiento, genera automáticamente:

- 📊 Resumen ejecutivo del clima político
- 📈 Análisis detallado de datos con sentimiento por tema
- 🎯 Plan estratégico con propuestas concretas
- 🎤 Discurso listo para usar
- 📉 Gráfico de distribución de sentimientos
- 📱 Envío automático del informe por WhatsApp (opcional)

## 🏗️ Arquitectura

### Backend (Flask + Python)
- **Framework**: Flask 3.0.0
- **API**: RESTful con validación Pydantic
- **Autenticación**: JWT + Supabase Auth
- **ML/AI**: 
  - BETO (Transformers) para análisis de sentimiento
  - OpenAI GPT-4o para generación de contenido
- **Integraciones**:
  - Twitter API (Tweepy) para búsqueda de tweets
  - Supabase para base de datos y autenticación
  - Twilio para envío de WhatsApp

### Frontend (React + Next.js)
- **Framework**: React con Next.js 14 (App Router)
- **UI**: Tailwind CSS + shadcn/ui
- **Estado**: Context API / Redux
- **Visualización**: Chart.js para gráficos

## 📁 Estructura del Proyecto

```
castor-elecciones/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask app factory
│   │   └── routes/               # API endpoints
│   │       ├── analysis.py       # Endpoint principal de análisis
│   │       ├── chat.py           # Chat con IA
│   │       ├── auth.py           # Autenticación
│   │       └── health.py         # Health check
│   ├── services/                 # Servicios modulares
│   │   ├── twitter_service.py    # Integración Twitter
│   │   ├── sentiment_service.py  # Análisis BETO
│   │   ├── openai_service.py    # Generación GPT-4o
│   │   ├── twilio_service.py    # WhatsApp
│   │   └── supabase_service.py  # Base de datos
│   ├── models/                   # Modelos Pydantic
│   │   └── schemas.py           # Validación de datos
│   ├── utils/                    # Utilidades
│   │   ├── chart_generator.py   # Generación de gráficos
│   │   ├── validators.py        # Validación de inputs
│   │   └── formatters.py        # Formateo de datos
│   ├── tests/                    # Tests unitarios
│   ├── config.py                # Configuración
│   ├── main.py                  # Punto de entrada
│   └── requirements.txt         # Dependencias
├── frontend/                     # Frontend React (pendiente)
├── docs/                         # Documentación
└── .env.example                 # Variables de entorno ejemplo
```

## 🚀 Instalación y Configuración

### Prerrequisitos

- Python 3.9+
- Node.js 18+ (para frontend)
- Cuentas de:
  - Twitter Developer (API v2)
  - OpenAI (API key)
  - Supabase (proyecto)
  - Twilio (opcional, para WhatsApp)

### Backend

1. **Clonar y navegar al proyecto**:
```bash
cd castor-elecciones/backend
```

2. **Crear entorno virtual**:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**:
```bash
cp ../.env.example .env
# Editar .env con tus credenciales
```

5. **Ejecutar aplicación**:
```bash
python main.py
```

La API estará disponible en `http://localhost:5001`

### Frontend

(Pendiente de implementación)

## 📡 Endpoints API

### Análisis Principal

**POST** `/api/analyze`

Genera análisis completo de sentimiento político.

**Request Body**:
```json
{
  "location": "Bogotá",
  "theme": "Seguridad",
  "candidate_name": "Juan Pérez",
  "politician": "@juanperez",
  "max_tweets": 100
}
```

**Response**:
```json
{
  "success": true,
  "executive_summary": {...},
  "topic_analyses": [...],
  "strategic_plan": {...},
  "speech": {...},
  "chart_data": {...}
}
```

### Chat con IA

**POST** `/api/chat`

Asistente de campaña en tiempo real.

**Request Body**:
```json
{
  "message": "¿Cómo puedo mejorar mi campaña?",
  "context": {...}
}
```

### Autenticación

- **POST** `/api/auth/register` - Registro de usuario
- **POST** `/api/auth/login` - Inicio de sesión
- **GET** `/api/auth/me` - Obtener usuario actual (requiere JWT)

### Health Check

**GET** `/api/health`

Verifica estado del servidor.

## 🔒 Seguridad

- ✅ Validación de inputs con Pydantic
- ✅ Autenticación JWT
- ✅ Rate limiting activo con Flask-Limiter + caché anti-picos
- ✅ CORS configurado
- ✅ Variables de entorno para secretos
- ✅ Manejo seguro de errores

## 🧪 Testing

```bash
# Ejecutar tests
pytest backend/tests/

# Con cobertura
pytest --cov=backend backend/tests/
```

## 📊 Temas del PND Soportados

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

## 🛠️ Mejores Prácticas Implementadas

- ✅ **SOLID**: Separación de responsabilidades en servicios
- ✅ **DRY**: Código reutilizable y modular
- ✅ **Type Hints**: Tipado estático con Python
- ✅ **Error Handling**: Manejo robusto de excepciones
- ✅ **Logging**: Sistema de logs estructurado
- ✅ **Validation**: Validación de datos con Pydantic
- ✅ **Documentation**: Docstrings en todas las funciones
- ✅ **Caching inteligente**: TTL cache con refresco diferido para trending, BETO y GPT

## 🐛 Issues Conocidos y Mejoras Pendientes

### Críticas
- [ ] Frontend React pendiente de implementación
- [ ] Tests unitarios incompletos
- [x] Rate limiting implementado con Flask-Limiter y cachés en servicios críticos

### Altas
- [ ] Caché de análisis para evitar duplicados
- [ ] WebSockets para actualizaciones en tiempo real
- [ ] Optimización de carga de modelo BETO (lazy loading)

### Medias
- [ ] Documentación Swagger/OpenAPI
- [ ] Métricas y monitoring (Prometheus)
- [ ] CI/CD pipeline

### Bajas
- [ ] Internacionalización (i18n)
- [ ] Temas personalizables
- [ ] Exportación a PDF

## 📝 Licencia

Proyecto privado - Todos los derechos reservados

## 👥 Contribuidores

- Carlos Ariel Sánchez Torres

## 📞 Soporte

Para soporte técnico, contactar al equipo de desarrollo.

---

**CASTOR ELECCIONES** - *Campaña Electoral Inteligente*

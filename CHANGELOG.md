# 📝 Changelog - CASTOR ELECCIONES

## [2.0.0] - Noviembre 2024

### 🎯 Cambios Principales

#### 1. Base de Datos
- ✅ **Reemplazado Supabase con PostgreSQL/SQLite**
  - Migrado a SQLAlchemy ORM
  - Modelos de base de datos completos
  - Sistema de autenticación propio
  - Migraciones con Flask-Migrate

#### 2. Detección de Trending Topics en Tiempo Real
- ✅ **Nuevo servicio `TrendingService`**
  - Detecta qué está trending AHORA
  - Analiza engagement y sentimiento
  - Extrae keywords y hashtags
  - Agrupa tweets por tema
  - Guarda trending topics en BD

#### 3. Agente de Campaña Inteligente
- ✅ **Nuevo `CampaignAgent`**
  - Analiza qué estrategias ganan votos
  - Aprende de acciones pasadas exitosas
  - Genera estrategias con predicción de votos
  - Calcula ROI y nivel de riesgo
  - Proporciona recomendaciones accionables

#### 4. Sistema de Recolección de Firmas
- ✅ **Endpoints para firmas digitales**
  - Recolectar firmas (`POST /api/campaign/signatures/collect`)
  - Contar firmas (`GET /api/campaign/signatures/{campaign_id}/count`)
  - Estrategia de recolección (`POST /api/campaign/signatures/strategy`)
  - Validación de duplicados
  - Tracking de progreso

#### 5. Discursos Alineados con Trending
- ✅ **Discursos ahora incluyen trending topics**
  - Se posicionan sobre temas trending
  - Conectan con lo que la gente está diciendo AHORA
  - Usan lenguaje que resuena en tiempo real
  - Mencionan temas trending del momento

### 🆕 Nuevos Endpoints

#### Campaña
- `POST /api/campaign/analyze-votes` - Analiza qué gana votos
- `GET /api/campaign/trending` - Obtiene trending topics
- `POST /api/campaign/signatures/collect` - Recolecta firma
- `GET /api/campaign/signatures/{campaign_id}/count` - Cuenta firmas
- `POST /api/campaign/signatures/strategy` - Estrategia de recolección

### 📊 Nuevas Tablas de Base de Datos

- `trending_topics` - Temas trending detectados
- `speeches` - Discursos generados
- `signatures` - Firmas recolectadas
- `campaign_actions` - Acciones de campaña y efectividad
- `vote_strategies` - Estrategias para ganar votos

### 🔧 Cambios Técnicos

- Reemplazado `SupabaseService` con `DatabaseService`
- Agregado `TrendingService` para detección de trending
- Agregado `CampaignAgent` para análisis de votos
- Actualizado `OpenAIService` para incluir trending topics en discursos
- Actualizado `Analysis` endpoint para detectar trending antes de generar discurso

### 📚 Documentación

- Agregado `docs/CAMPAIGN_AGENT.md` - Documentación del agente
- Actualizado `.env.example` con `DATABASE_URL`
- Agregado `init_db.py` para inicializar base de datos

### 🐛 Correcciones

- Corregidos imports de servicios
- Actualizada autenticación para usar base de datos propia
- Corregida referencia a Supabase en endpoints

### ⚠️ Breaking Changes

- **Supabase removido** - Ahora usa PostgreSQL/SQLite
- Variables de entorno cambiadas:
  - Removido: `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
  - Agregado: `DATABASE_URL`

### 🚀 Migración

Para migrar de Supabase a PostgreSQL:

1. Instalar PostgreSQL o usar SQLite para desarrollo
2. Configurar `DATABASE_URL` en `.env`
3. Ejecutar `python backend/init_db.py` para crear tablas
4. Actualizar código que use Supabase (ya hecho)

---

## [1.0.0] - Versión Inicial

### Características Iniciales
- Backend Flask con endpoints de análisis
- Integración con Twitter API
- Análisis de sentimiento con BETO
- Generación de contenido con GPT-4o
- Integración con Supabase
- Sistema de autenticación JWT
- Envío de WhatsApp con Twilio


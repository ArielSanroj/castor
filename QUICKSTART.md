# 🚀 Inicio Rápido - CASTOR ELECCIONES

## Configuración en 5 Minutos

### 1. Instalar Dependencias

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

```bash
cp ../.env.example .env
# Editar .env con tus credenciales
```

**Variables mínimas requeridas**:
- `TWITTER_BEARER_TOKEN`
- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`

### 3. Configurar Base de Datos Supabase

1. Ir a tu proyecto Supabase
2. Abrir SQL Editor
3. Ejecutar: `docs/supabase_schema.sql`

### 4. Ejecutar Servidor

```bash
python main.py
```

La API estará en: `http://localhost:5001`

### 5. Probar Endpoints

#### Health Check
```bash
curl http://localhost:5001/api/health
```

#### Análisis (requiere autenticación opcional)
```bash
curl -X POST http://localhost:5001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Bogotá",
    "theme": "Seguridad",
    "candidate_name": "Juan Pérez",
    "max_tweets": 50
  }'
```

## Estructura de Archivos Importantes

- `backend/main.py` - Iniciar servidor
- `backend/config.py` - Configuración
- `backend/app/routes/analysis.py` - Endpoint principal
- `.env` - Variables de entorno (crear desde .env.example)

## Comandos Útiles

```bash
# Ejecutar tests
make test

# Formatear código
make format

# Linter
make lint

# Limpiar archivos temporales
make clean
```

## Troubleshooting

### Error: Module not found
- Verificar que estás en el entorno virtual
- Ejecutar `pip install -r requirements.txt`

### Error: Twitter API
- Verificar `TWITTER_BEARER_TOKEN` en `.env`
- Verificar que el token tenga permisos de lectura

### Error: Supabase
- Verificar `SUPABASE_URL` y `SUPABASE_KEY`
- Ejecutar schema SQL en Supabase

### Error: OpenAI
- Verificar `OPENAI_API_KEY`
- Verificar que tenga créditos disponibles

## Siguiente Paso

Ver `README.md` para documentación completa.


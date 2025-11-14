# Guía de Migración: Unificación de Flask

## Problema

Actualmente existen dos implementaciones de Flask:
1. **Backend modular** (`backend/app/`) - Arquitectura moderna con blueprints, servicios separados
2. **Main monolítico** (`main.py`) - Implementación legacy con todo en un archivo

## Solución

Se recomienda **deprecar `main.py`** y usar únicamente el backend modular.

## Pasos de Migración

### 1. Verificar que el backend modular tenga todas las funcionalidades

El backend modular (`backend/app/`) ya incluye:
- ✅ Endpoint `/api/analyze` (equivalente a `/analyze` en main.py)
- ✅ Análisis de sentimiento con BETO
- ✅ Integración con OpenAI
- ✅ Generación de gráficas
- ✅ Rate limiting
- ✅ Cacheo
- ✅ Background jobs

### 2. Migrar templates (si es necesario)

Si `main.py` tiene templates HTML que necesitas mantener:

```bash
# Mover templates a backend si es necesario
mkdir -p backend/templates
# Copiar templates de main.py si existen
```

### 3. Actualizar scripts de inicio

**Antes (main.py):**
```bash
python main.py
```

**Después (backend modular):**
```bash
cd backend
python -m app  # O usar el entry point configurado
```

O crear un nuevo `run.py`:

```python
# backend/run.py
from app import create_app
from config import Config

app = create_app('development')

if __name__ == '__main__':
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
```

### 4. Actualizar documentación

Actualizar README.md y cualquier documentación que haga referencia a `main.py`.

### 5. Deprecar main.py

Agregar un aviso de deprecación al inicio de `main.py`:

```python
"""
⚠️ DEPRECATED: Este archivo está deprecado.

Por favor usa el backend modular en backend/app/ en su lugar.

Para ejecutar:
    cd backend
    python run.py

O usa el entry point configurado.
"""
```

## Endpoints Equivalentes

| main.py (Legacy) | backend/app/ (Modular) |
|------------------|----------------------|
| `POST /analyze` | `POST /api/analyze` |
| `GET /` | `GET /api/health` (o crear endpoint raíz) |
| `GET /webpage` | Crear blueprint para UI si es necesario |

## Ventajas del Backend Modular

1. **Arquitectura limpia**: Separación de responsabilidades
2. **Rate limiting**: Protección contra abuso
3. **Cacheo**: Mejor rendimiento
4. **Background jobs**: Procesamiento asíncrono
5. **Tests**: Suite de pruebas más completa
6. **Escalabilidad**: Fácil de extender y mantener

## Notas

- El backend modular es más completo y moderno
- `main.py` puede mantenerse temporalmente para compatibilidad
- Se recomienda migrar completamente al backend modular antes de producción


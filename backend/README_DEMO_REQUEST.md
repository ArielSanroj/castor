# Demo Request - Guardado en PostgreSQL

## Descripción

El sistema ahora guarda las solicitudes de demo del formulario modal en PostgreSQL.

## Campos del Formulario

El formulario incluye los siguientes campos:
- **Nombre** (first_name) - Requerido
- **Apellido** (last_name) - Requerido
- **Email** (email) - Requerido, único
- **Teléfono** (phone) - Requerido
- **¿Qué te interesa?** (interest) - Requerido: `forecast`, `campañas`, o `medios`
- **Ubicación** (location) - Requerido: ciudad

## Endpoint

**POST** `/api/demo-request`

### Request Body
```json
{
  "first_name": "Juan",
  "last_name": "Pérez",
  "email": "juan@example.com",
  "phone": "+573001234567",
  "interest": "forecast",
  "location": "Bogotá"
}
```

### Response (Success - 201)
```json
{
  "success": true,
  "lead_id": "uuid-del-lead",
  "message": "Solicitud de demo recibida exitosamente"
}
```

### Response (Error - 400)
```json
{
  "success": false,
  "error": "Invalid request data",
  "details": [...]
}
```

## Migración de Base de Datos

Si ya tienes una tabla `leads` existente, ejecuta la migración:

```bash
cd backend
python3 migrate_leads_table.py
```

Esto agregará las columnas:
- `interest` (VARCHAR(50), NOT NULL)
- `location` (VARCHAR(120), NOT NULL)
- Hace `candidacy_type` opcional (nullable)

Si es una instalación nueva, las tablas se crearán automáticamente con `init_db.py`.

## Pruebas

Para probar el endpoint:

```bash
cd backend
python3 test_demo_request.py
```

O manualmente con curl:

```bash
curl -X POST http://localhost:5001/api/demo-request \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Juan",
    "last_name": "Pérez",
    "email": "juan@example.com",
    "phone": "+573001234567",
    "interest": "forecast",
    "location": "Bogotá"
  }'
```

## Cambios Realizados

1. **Modelo Lead** (`backend/models/database.py`):
   - Agregado campo `interest` (forecast, campañas, medios)
   - Agregado campo `location` (ciudad)
   - `candidacy_type` ahora es opcional

2. **Endpoint** (`backend/app/routes/leads.py`):
   - Actualizado para aceptar `interest` y `location`
   - Validación con Pydantic

3. **JavaScript** (`static/js/performance.js`):
   - Actualizado `submitForm()` para enviar datos al endpoint `/api/demo-request`
   - Manejo de errores y mensajes de éxito

4. **Frontend** (`templates/webpage.html`):
   - Formulario actualizado con campos `interest` y `location`
   - Botón "Probar ahora" en el header
   - Modal se activa desde múltiples lugares

## Verificación

Para verificar que los datos se están guardando:

1. Envía una solicitud de demo desde el frontend
2. Verifica en la base de datos:
   ```sql
   SELECT * FROM leads ORDER BY created_at DESC LIMIT 10;
   ```

3. O usa el endpoint de conteo:
   ```bash
   curl http://localhost:5001/api/leads/count
   ```

## Notas

- El email debe ser único. Si se intenta crear un lead con un email existente, retornará error.
- El campo `interest` solo acepta: `forecast`, `campañas`, o `medios`
- Todos los campos son requeridos excepto `candidacy_type`


# ADR-001: Framework Backend - Flask vs FastAPI

**Estado:** Aceptado
**Fecha:** 2026-01-14
**Decisores:** Equipo CASTOR
**Categoria:** Arquitectura Backend

## Contexto

CASTOR Elecciones necesita un framework backend Python para servir:
- APIs REST para analisis electoral
- Integracion con modelos ML (BETO sentiment analysis)
- Conexion a servicios externos (Twitter API, OpenAI)
- Renderizado de templates HTML (Jinja2)

### Opciones Evaluadas

| Criterio | Flask | FastAPI |
|----------|-------|---------|
| Madurez | 2010, muy maduro | 2018, maduro |
| Async nativo | No (requiere extensiones) | Si (ASGI) |
| Validacion | Manual o Flask-Pydantic | Pydantic integrado |
| OpenAPI/Swagger | Flask-RESTX (extension) | Automatico |
| Curva aprendizaje | Baja | Media |
| Ecosistema templates | Jinja2 nativo | Jinja2 (requiere config) |
| Performance I/O bound | Medio | Alto |
| Performance CPU bound | Similar | Similar |

## Decision

**Elegimos Flask** para la primera version de CASTOR.

## Justificacion

### 1. Simplicidad de Prototipado Rapido
- Flask permite iterar rapidamente sin boilerplate
- Templates Jinja2 integrados nativamente
- Ideal para MVP y validacion de mercado

### 2. Carga de Trabajo Actual
- Volumen esperado: <1000 usuarios/dia inicialmente
- Operaciones CPU-bound (BETO model) dominan sobre I/O
- Async no es critico para el caso de uso actual

### 3. Equipo y Mantenimiento
- Mayor pool de desarrolladores Flask disponibles
- Documentacion y recursos abundantes
- Menor riesgo tecnico para equipo pequeno

### 4. Costo de Migracion
- Migracion a FastAPI es incremental si se requiere
- Pydantic ya implementado para validacion
- Rutas pueden migrarse gradualmente

## Consecuencias

### Positivas
- Desarrollo rapido del MVP
- Facil onboarding de nuevos desarrolladores
- Menor complejidad operacional

### Negativas
- Limitaciones de concurrencia sin Gunicorn workers
- Sin async nativo para llamadas a APIs externas
- Documentacion OpenAPI requiere extension adicional

### Mitigaciones
- Usar Gunicorn con multiples workers para concurrencia
- Implementar cache agresivo para reducir llamadas API
- Agregar Flask-RESTX para documentacion OpenAPI

## Plan de Reevaluacion

Migrar a FastAPI cuando:
- Usuarios concurrentes superen 10,000
- Latencia de APIs externas sea cuello de botella critico
- Se requiera WebSocket nativo para features real-time

## Metricas de Exito

| Metrica | Objetivo | Actual |
|---------|----------|--------|
| Latencia p95 | <3s | ~2.5s |
| Throughput | >100 req/min | ~80 req/min |
| Disponibilidad | 99.5% | 99.2% |

## Referencias

- [Flask Documentation](https://flask.palletsprojects.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Python Web Framework Benchmarks](https://www.techempower.com/benchmarks/)

---
*Revision programada: Q2 2026*

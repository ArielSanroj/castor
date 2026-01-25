# CASTOR Microservicios - Pendientes

## Comparación de Arquitecturas

### Opción A: Por Dominio de Negocio (Implementado)
```
services/
├── core-service/      # Auth, Users
├── e14-service/       # Todo E-14
└── dashboard-ia/      # Todo Dashboard IA
```
**Pros**: Menos servicios, deploy más simple, menos latencia inter-servicio
**Contras**: Servicios más grandes, menos flexibilidad de escala

### Opción B: Por Servicio Técnico (Propuesta CASTOR-2-CE)
```
services/
├── sentiment-service/
├── twitter-service/
├── openai-service/
├── rag-service/
├── forecast-service/
├── trending-service/
└── auth-service/
```
**Pros**: Escala granular, equipos independientes, fácil reemplazo
**Contras**: Más servicios (7+), más complejidad, más latencia

---

## Lo que FALTA para Producción

### 1. Contratos API Versionados
```python
# Falta: schemas estandarizados para comunicación inter-servicio
# Ejemplo propuesto:
POST /v1/sentiment/analyze
{
    "texts": ["texto1", "texto2"],
    "lang": "es"
}
Response:
{
    "ok": true,
    "data": {
        "results": [
            {"text": "...", "positive": 0.8, "negative": 0.1, "neutral": 0.1}
        ]
    }
}
```

### 2. Clientes HTTP Inter-Servicio
```python
# Falta: client con retry, circuit breaker, timeout
class CoreServiceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)

    @circuit_breaker(failure_threshold=5, reset_timeout=60)
    async def validate_token(self, token: str) -> dict:
        response = await self.client.post(
            f"{self.base_url}/internal/validate-token",
            json={"token": token}
        )
        return response.json()
```

### 3. Autenticación Inter-Servicios
- [ ] JWT interno para service-to-service
- [ ] mTLS alternativo para producción
- [ ] API keys para servicios internos

### 4. Observabilidad
- [ ] OpenTelemetry traces
- [ ] Métricas Prometheus en todos los servicios
- [ ] Logging estructurado (JSON)
- [ ] Correlation IDs entre servicios

### 5. Health Checks Robustos
```python
# Falta: separar liveness de readiness
GET /health/live   # Solo "estoy vivo"
GET /health/ready  # "Puedo procesar requests" (DB, Redis, etc.)
```

### 6. Kubernetes Manifests
```yaml
# Falta: deployment, service, ingress, HPA por servicio
apiVersion: apps/v1
kind: Deployment
metadata:
  name: e14-service
spec:
  replicas: 2
  ...
```

### 7. CI/CD Pipeline
- [ ] Build independiente por servicio
- [ ] Tests de contrato (Pact o similar)
- [ ] Canary deployments
- [ ] Rollback automático

---

## Plan de Migración Recomendado

### Fase 1: Estabilizar lo actual (1-2 semanas)
1. Ajustar imports en archivos copiados
2. Probar cada servicio localmente
3. Migrar datos SQLite → PostgreSQL
4. Verificar comunicación básica

### Fase 2: Agregar robustez (2-3 semanas)
1. Implementar clientes HTTP con retry/circuit breaker
2. Agregar API versioning (/v1/)
3. Mejorar health checks
4. Agregar logging estructurado

### Fase 3: Observabilidad (1-2 semanas)
1. OpenTelemetry integration
2. Prometheus metrics
3. Grafana dashboards
4. Alertas básicas

### Fase 4: Producción (2-3 semanas)
1. Kubernetes manifests
2. CI/CD pipelines
3. Canary deployment
4. Documentación operacional

---

## Decisión Arquitectónica Pendiente

**¿Mantener 3 servicios por dominio o separar más granularmente?**

### Recomendación: Híbrido
```
services/
├── core-service/          # Auth, Users, Leads (como está)
├── e14-service/           # E-14 completo (como está)
└── dashboard-ia/          # Mantener monolito interno, pero...
    └── internal/
        ├── sentiment/     # Módulo interno, NO servicio separado
        ├── twitter/       # Módulo interno
        ├── rag/           # Módulo interno
        └── forecast/      # Módulo interno
```

**Razón**: Separar Sentiment, Twitter, RAG como servicios independientes solo tiene sentido si:
- Equipos diferentes los mantienen
- Necesitan escalar de forma muy diferente
- Quieres reemplazarlos independientemente

Para un equipo pequeño, 3 servicios es suficiente. Puedes extraer más después si lo necesitas.

---

## Respuesta a las opciones propuestas

### Opción A (scaffold completo CASTOR-2-CE)
- Demasiado trabajo si ya tienes la estructura de 3 servicios
- Solo si quieres empezar de cero con FastAPI

### Opción B (scaffold + clientes + PRs graduales)
- **Recomendada** si quieres migrar gradualmente
- Mantiene compatibilidad con el monolito

### Opción C (solo schemas/contratos)
- Útil si quieres documentar primero
- No resuelve la implementación

### Mi recomendación: B modificada
1. Usar la estructura de 3 servicios que ya creamos (Flask)
2. Agregar los elementos faltantes (clientes HTTP, observabilidad)
3. Migrar gradualmente el frontend/monolito a usar los nuevos endpoints
4. Si después necesitas más granularidad, extraer de dashboard-ia

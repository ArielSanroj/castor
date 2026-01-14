# ADR-002: Arquitectura Monolitica vs Microservicios

**Estado:** Aceptado (temporal)
**Fecha:** 2026-01-14
**Decisores:** Equipo CASTOR
**Categoria:** Arquitectura de Sistema

## Contexto

CASTOR tiene multiples dominios funcionales:
- Analisis de Twitter (TwitterService)
- Analisis de Sentimiento (SentimentService/BETO)
- Generacion de Contenido (OpenAIService)
- Forecast Electoral (ForecastService)
- Chat RAG (RAGService)

### Pregunta Clave
¿Debemos separar estos dominios en microservicios independientes?

## Decision

**Mantener arquitectura monolitica modular** para la fase actual (MVP → Product-Market Fit).

## Justificacion Economica (Analisis Costo-Beneficio)

### Costo de Microservicios Ahora

| Componente | Costo Mensual Estimado |
|------------|------------------------|
| Kubernetes cluster | $150-300/mes |
| Service mesh (Istio) | +$50/mes overhead |
| Monitoring distribuido | +$100/mes |
| DevOps adicional | +40h/mes desarrollo |
| **Total** | **~$500/mes + 40h** |

### Costo de Monolito Actual

| Componente | Costo Mensual |
|------------|---------------|
| Single Heroku/Railway dyno | $25-50/mes |
| Redis addon | $15/mes |
| PostgreSQL | $15/mes |
| **Total** | **~$80/mes** |

### ROI de Microservicios
- Beneficio real solo con >10K usuarios concurrentes
- Usuarios actuales: <500/dia
- **ROI negativo hasta alcanzar escala**

## Arquitectura Actual (Monolito Modular)

```
┌─────────────────────────────────────────────────────────────┐
│                    CASTOR Monolith                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Routes    │  │   Routes    │  │   Routes    │         │
│  │   /media    │  │  /campaign  │  │  /forecast  │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│  ┌──────┴────────────────┴────────────────┴──────┐         │
│  │              Service Layer                     │         │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐         │         │
│  │  │Twitter  │ │Sentiment│ │ OpenAI  │         │         │
│  │  │Service  │ │Service  │ │ Service │         │         │
│  │  └─────────┘ └─────────┘ └─────────┘         │         │
│  └───────────────────────────────────────────────┘         │
│                          │                                  │
│  ┌───────────────────────┴───────────────────────┐         │
│  │              Data Layer                        │         │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐         │         │
│  │  │PostgreSQL│ │  Redis  │ │  RAG    │         │         │
│  │  │         │ │ (Cache) │ │ Index   │         │         │
│  │  └─────────┘ └─────────┘ └─────────┘         │         │
│  └───────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## Plan de Migracion a Microservicios

### Fase 1: Modularizacion Interna (Actual)
- Servicios como modulos Python separados
- Interfaces claras entre servicios
- Cache compartido via Redis

### Fase 2: Extraction de Servicios (Cuando escalar)
Orden de extraccion por complejidad/beneficio:

1. **SentimentService** (CPU-bound, escalado independiente)
2. **OpenAIService** (rate limiting independiente)
3. **TwitterService** (rate limiting independiente)
4. **ForecastService** (puede pre-calcular)

### Triggers para Migrar

| Metrica | Threshold | Accion |
|---------|-----------|--------|
| Usuarios concurrentes | >5,000 | Evaluar extraccion |
| Latencia p99 | >5s | Extraer servicio lento |
| Costo OpenAI | >$500/mes | Optimizar/extraer |
| Downtime mensual | >4h | HA con replicas |

## Consecuencias

### Positivas
- Desarrollo rapido sin overhead de infraestructura
- Facil debugging (single process)
- Deployment simple
- Costo operacional minimo

### Negativas
- Escalado solo vertical (mas recursos al dyno)
- Single point of failure
- Deploy completo por cualquier cambio

### Mitigaciones
- Health checks robustos
- Circuit breakers para APIs externas
- Cache agresivo para reducir carga
- Graceful degradation cuando APIs fallan

## Defensa ante Inversionistas

> "¿Por que NO microservicios?"

**Respuesta:**
1. **Unit Economics:** $80/mes vs $500/mes sin usuarios que lo justifiquen
2. **Time to Market:** 3x mas rapido iterar en monolito
3. **Complejidad Operacional:** Equipo de 1-2 personas no puede mantener K8s
4. **Escalabilidad Planificada:** Arquitectura modular permite extraer servicios cuando ROI sea positivo
5. **Precedente:** Shopify, Basecamp y Hey.com escalan con monolitos optimizados

## Referencias

- [Monolith First - Martin Fowler](https://martinfowler.com/bliki/MonolithFirst.html)
- [Majestic Monolith - DHH](https://m.signalvnoise.com/the-majestic-monolith/)
- [Microservices Premium - Martin Fowler](https://martinfowler.com/bliki/MicroservicesPremium.html)

---
*Reevaluacion: Cuando MRR > $5,000 o usuarios > 5,000*

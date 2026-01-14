# CASTOR Elecciones - Service Level Agreement (SLA)

**Version:** 1.0
**Fecha:** 2026-01-14
**Propietario:** Equipo CASTOR

---

## 1. Resumen Ejecutivo

Este documento define los objetivos de nivel de servicio (SLOs) y acuerdos de nivel de servicio (SLAs) para la plataforma CASTOR Elecciones.

### Metricas Clave

| Metrica | Objetivo | Medicion |
|---------|----------|----------|
| **Disponibilidad** | 99.5% | Uptime mensual |
| **Latencia p95** | < 3,000 ms | Tiempo de respuesta |
| **Tasa de Error** | < 1% | Requests fallidos |
| **MTTR** | < 4 horas | Tiempo de recuperacion |

---

## 2. Definiciones

### 2.1 Disponibilidad
- **Definicion:** Porcentaje de tiempo que el servicio responde exitosamente a requests
- **Formula:** `(Total minutos - Minutos downtime) / Total minutos × 100`
- **Exclusiones:** Mantenimiento programado, fuerza mayor, dependencias externas (Twitter API, OpenAI)

### 2.2 Latencia
- **p50 (mediana):** Tiempo que tarda el 50% de los requests
- **p95:** Tiempo que tarda el 95% de los requests
- **p99:** Tiempo que tarda el 99% de los requests

### 2.3 Tasa de Error
- **Definicion:** Porcentaje de requests que retornan codigo HTTP 5xx
- **Formula:** `(Requests 5xx / Total requests) × 100`

---

## 3. Objetivos de Nivel de Servicio (SLOs)

### 3.1 API Principal (`/api/*`)

| Endpoint | Disponibilidad | Latencia p95 | Tasa Error |
|----------|----------------|--------------|------------|
| `/api/health` | 99.9% | 100 ms | 0.1% |
| `/api/media/analyze` | 99.5% | 3,000 ms | 1% |
| `/api/campaign/analyze` | 99.5% | 5,000 ms | 2% |
| `/api/forecast/dashboard` | 99.5% | 3,000 ms | 1% |
| `/api/chat/rag` | 99.5% | 2,000 ms | 1% |

### 3.2 Dependencias Externas

| Servicio | SLA del Proveedor | Impacto en CASTOR |
|----------|-------------------|-------------------|
| Twitter API | 99.5% | Degradado (cache fallback) |
| OpenAI API | 99.9% | Degradado (sin generacion IA) |
| Supabase | 99.9% | Critico (sin persistencia) |
| Redis (Upstash) | 99.9% | Degradado (in-memory fallback) |

### 3.3 Ventanas de Mantenimiento

| Tipo | Frecuencia | Duracion | Notificacion |
|------|------------|----------|--------------|
| Parches criticos | Ad-hoc | < 15 min | 1 hora |
| Actualizaciones | Semanal | < 30 min | 24 horas |
| Mantenimiento mayor | Mensual | < 2 horas | 1 semana |

---

## 4. Indicadores de Rendimiento (KPIs)

### 4.1 Metricas de Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    DASHBOARD SLA                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Disponibilidad (30 dias)     Latencia p95                 │
│  ┌────────────────────┐       ┌────────────────────┐       │
│  │  ████████████████  │       │  ██████████░░░░░░  │       │
│  │       99.7%        │       │     2,450 ms       │       │
│  │   Meta: 99.5%  ✓   │       │   Meta: 3,000 ms ✓ │       │
│  └────────────────────┘       └────────────────────┘       │
│                                                             │
│  Tasa de Error                MTTR (ultimo incidente)      │
│  ┌────────────────────┐       ┌────────────────────┐       │
│  │  █░░░░░░░░░░░░░░░  │       │  ████████░░░░░░░░  │       │
│  │       0.3%         │       │     2.5 horas      │       │
│  │   Meta: < 1%   ✓   │       │   Meta: < 4h   ✓   │       │
│  └────────────────────┘       └────────────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Metricas por Endpoint

| Endpoint | Requests/dia | Latencia p50 | Latencia p95 | Errores |
|----------|--------------|--------------|--------------|---------|
| `/api/media/analyze` | ~200 | 1,200 ms | 2,400 ms | 0.2% |
| `/api/forecast/icce` | ~150 | 800 ms | 1,600 ms | 0.1% |
| `/api/chat/rag` | ~300 | 600 ms | 1,200 ms | 0.3% |

---

## 5. Procedimientos de Escalacion

### 5.1 Niveles de Severidad

| Nivel | Descripcion | Tiempo Respuesta | Tiempo Resolucion |
|-------|-------------|------------------|-------------------|
| **P1 - Critico** | Servicio caido completamente | 15 min | 4 horas |
| **P2 - Alto** | Funcionalidad principal degradada | 30 min | 8 horas |
| **P3 - Medio** | Funcionalidad secundaria afectada | 2 horas | 24 horas |
| **P4 - Bajo** | Inconveniente menor | 24 horas | 1 semana |

### 5.2 Matriz de Escalacion

```
Tiempo desde deteccion:
0 ──────────────────────────────────────────────────────► 4h

P1: [On-call] → [Team Lead] → [CTO] → [CEO]
     0 min       15 min        1h       2h

P2: [On-call] → [Team Lead] → [CTO]
     0 min       30 min        2h

P3: [Ticket] → [Developer] → [Team Lead]
     0 min       2h            24h
```

---

## 6. Monitoreo y Alertas

### 6.1 Endpoints de Health Check

| Endpoint | Uso | Frecuencia |
|----------|-----|------------|
| `/api/health` | Basico (load balancer) | 10 seg |
| `/api/health/ready` | K8s readiness | 5 seg |
| `/api/health/live` | K8s liveness | 10 seg |
| `/api/health/full` | Monitoreo completo | 1 min |
| `/api/health/sla` | Metricas SLA | 5 min |

### 6.2 Umbrales de Alerta

| Metrica | Warning | Critical | Accion |
|---------|---------|----------|--------|
| CPU | > 70% | > 90% | Scale up |
| Memory | > 75% | > 90% | Investigate |
| Disk | > 80% | > 95% | Clean up |
| Latencia p95 | > 2.5s | > 4s | Investigate |
| Error rate | > 0.5% | > 2% | Incident |
| Circuit breaker | Half-open | Open | Check API |

### 6.3 Integraciones

| Herramienta | Proposito | Estado |
|-------------|-----------|--------|
| Uptime Robot | Monitoreo externo | Configurado |
| Sentry | Error tracking | Pendiente |
| Prometheus | Metricas | Roadmap |
| Grafana | Dashboards | Roadmap |
| PagerDuty | Alertas on-call | Roadmap |

---

## 7. Creditos y Compensacion

### 7.1 Creditos por Incumplimiento

| Disponibilidad Mensual | Credito |
|------------------------|---------|
| 99.0% - 99.5% | 10% proximo mes |
| 95.0% - 99.0% | 25% proximo mes |
| < 95.0% | 50% proximo mes |

### 7.2 Exclusiones

No aplican creditos por:
- Mantenimiento programado con aviso previo
- Fallas de dependencias externas (Twitter, OpenAI)
- Mal uso o abuso del servicio
- Fuerza mayor
- Periodo beta/trial

---

## 8. Revision y Mejora Continua

### 8.1 Reuniones de Revision

| Tipo | Frecuencia | Participantes |
|------|------------|---------------|
| Daily standup | Diario | Equipo tecnico |
| SLA review | Semanal | Tech + Producto |
| Post-mortem | Post-incidente P1/P2 | Todo el equipo |
| Quarterly review | Trimestral | Stakeholders |

### 8.2 Mejora de SLOs

Los SLOs se revisaran trimestralmente considerando:
- Tendencias de metricas
- Feedback de usuarios
- Capacidad de infraestructura
- Costo vs beneficio

---

## 9. Contacto

| Rol | Contacto | Disponibilidad |
|-----|----------|----------------|
| Soporte L1 | soporte@castor.com | 9am-6pm COT |
| On-call | oncall@castor.com | 24/7 |
| Emergencias | +57 XXX XXX XXXX | 24/7 |

---

## Historial de Cambios

| Version | Fecha | Cambios | Autor |
|---------|-------|---------|-------|
| 1.0 | 2026-01-14 | Documento inicial | Equipo CASTOR |

---

*Este documento es vinculante para clientes con contratos de servicio activos.*

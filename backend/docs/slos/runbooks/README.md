# Runbooks - CASTOR Electoral

Procedimientos operativos para responder a incidentes según QAS definidos.

## Índice de Runbooks

### Críticos (P0)

| Runbook | QAS | Trigger | Tiempo Respuesta |
|---------|-----|---------|------------------|
| [ingestion_degraded.md](./ingestion_degraded.md) | L1, A1 | `ingestion_latency_p95 > 4s` | < 5 min |
| [security_breach.md](./security_breach.md) | Sec1, Sec2 | `unauthorized_access > 0` | < 2 min |
| [validation_inconsistency.md](./validation_inconsistency.md) | I2, I3 | `consistency < 100%` | < 5 min |

### Alta Prioridad (P1)

| Runbook | QAS | Trigger | Tiempo Respuesta |
|---------|-----|---------|------------------|
| [ocr_backlog_critical.md](./ocr_backlog_critical.md) | L2, S1 | `ocr_queue_depth > 1000` | < 5 min |
| [db_replication_lag.md](./db_replication_lag.md) | A3, S2 | `replication_lag > 5s` | < 10 min |

### Por Crear

| Runbook | QAS | Estado |
|---------|-----|--------|
| `api_down.md` | A1 | Pendiente |
| `anthropic_failure.md` | L2 | Pendiente |
| `storage_failure.md` | I1 | Pendiente |
| `olap_degraded.md` | A2, L3 | Pendiente |
| `pii_incident.md` | Sec2 | Pendiente |

## Uso de Runbooks

### Durante Incidente

1. **Identificar** el runbook correcto según la alerta
2. **Seguir** el diagnóstico rápido (< 2 min)
3. **Ejecutar** mitigación según árbol de decisión
4. **Verificar** resolución con criterios de cierre
5. **Documentar** en post-mortem

### Formato de Runbook

```markdown
# Runbook: [Nombre]

**Severidad:** CRITICAL | HIGH | MEDIUM
**QAS:** [Referencias]
**SLO Afectado:** [métrica]

## Síntomas
## Impacto
## Diagnóstico Rápido
## Árbol de Decisión
## Acciones de Mitigación
## Verificación de Resolución
## Criterios de Cierre
## Contactos
## Referencias
```

## Escalación

| Nivel | Tiempo | Rol |
|-------|--------|-----|
| L1 | 0-15 min | SRE on-call |
| L2 | 15-30 min | Tech Lead |
| L3 | 30+ min | CTO / Directivos |

## Contactos de Emergencia

| Rol | Slack | Teléfono |
|-----|-------|----------|
| SRE On-Call | @sre-oncall | +57-XXX |
| Security | @security | +57-XXX |
| CTO | @cto | +57-XXX |
| Registraduría (enlace) | N/A | +57-XXX |

## Simulacros

- **Semanal:** Revisar runbooks
- **Mensual:** Simulacro de incidente P1
- **Trimestral:** Simulacro de incidente P0

## Actualizaciones

Última revisión: 2026-01-23
Próxima revisión: 2026-02-23 (antes de elección)

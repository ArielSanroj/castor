# Service Level Objectives (SLOs) - CASTOR Electoral

Basado en Quality Attribute Scenarios (QAS) para la Gran Consulta Nacional 8 Marzo 2026.

## Prioridades de Implementación

| Prioridad | QAS | Descripción | SLO Target |
|-----------|-----|-------------|------------|
| P0 | L1 + A1 + I1 | Ingesta + Evidencia siempre | 99.9% disponibilidad |
| P1 | L2 + S1 | OCR fast-path + Escala | p95 ≤ 45s |
| P2 | Reconciliación | War room chosen_form | 100% consistencia |
| P3 | OLAP + Cache | Dashboards rápidos | p95 ≤ 500ms |
| P4 | HITL + Auditoría | Correcciones defendibles | 100% auditado |
| P5 | Versioning | Templates/Rulesets | Deploy ≤ 1 día |
| P6 | Security + Ops | RBAC + PII + Alertas | 0 brechas |

## Archivos

- `slo_definitions.yaml` - Definiciones formales de SLOs
- `metrics_dashboard.yaml` - Configuración de métricas
- `runbooks/` - Procedimientos operativos

## Error Budget

- **99.9% = 8.76 horas/año de downtime permitido**
- **99.5% = 43.8 horas/año** (servicios no críticos)
- Para día electoral (12h): **0 minutos** tolerancia en ingesta

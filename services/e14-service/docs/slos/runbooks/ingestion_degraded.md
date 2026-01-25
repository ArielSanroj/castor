# Runbook: Ingestion Degraded

**Severidad:** CRITICAL
**QAS:** L1, A1
**SLO Afectado:** ingestion_latency_p95 > 4s

---

## Síntomas

- Alerta: `ingestion_latency_p95 > 4000ms`
- Testigos reportan lentitud al subir E-14
- Dashboard muestra cola de ingesta creciendo

## Impacto

- **CRÍTICO en día electoral:** Pérdida de evidencia, retraso en escrutinio
- Testigos pueden abandonar antes de confirmar upload
- Posible pérdida de documentos

## Diagnóstico Rápido (< 2 min)

```bash
# 1. Verificar estado de API
curl -w "%{http_code}" https://api.castor.electoral/api/electoral/health

# 2. Verificar latencia actual
curl -s https://metrics.castor/api/v1/query?query=histogram_quantile(0.95,castor_ingestion_duration_seconds_bucket[5m])

# 3. Verificar conexiones BD
curl -s https://metrics.castor/api/v1/query?query=castor_db_connections_active

# 4. Verificar storage
aws s3api head-bucket --bucket castor-evidence-bucket
```

## Árbol de Decisión

```
┌─────────────────────────────────────────┐
│ ¿API responde 200?                      │
└─────────────────────────────────────────┘
        │
   ┌────┴────┐
   │ NO      │ SÍ
   ▼         ▼
┌──────────┐ ┌─────────────────────────────┐
│ RUNBOOK: │ │ ¿Conexiones BD > 80%?       │
│ api_down │ └─────────────────────────────┘
└──────────┘         │
               ┌─────┴─────┐
               │ SÍ        │ NO
               ▼           ▼
         ┌──────────┐ ┌─────────────────────┐
         │ Escalar  │ │ ¿Storage responde?  │
         │ BD pool  │ └─────────────────────┘
         └──────────┘         │
                        ┌─────┴─────┐
                        │ NO        │ SÍ
                        ▼           ▼
                  ┌──────────┐ ┌──────────────┐
                  │ RUNBOOK: │ │ Escalar API  │
                  │ storage_ │ │ instances    │
                  │ failure  │ └──────────────┘
                  └──────────┘
```

## Acciones de Mitigación

### Nivel 1: Escalar (< 5 min)

```bash
# Escalar API instances
kubectl scale deployment castor-api --replicas=10

# Verificar autoscaling
kubectl get hpa castor-api

# Aumentar pool de conexiones BD (si necesario)
kubectl set env deployment/castor-api DB_POOL_SIZE=50
```

### Nivel 2: Degradación Controlada (5-15 min)

```bash
# Activar modo de ingesta mínima (solo guardar, sin validación inline)
kubectl set env deployment/castor-api INGESTION_MODE=minimal

# Desactivar features no críticas
kubectl set env deployment/castor-api FEATURE_INLINE_VALIDATION=false
```

### Nivel 3: Failover (si persiste > 15 min)

```bash
# Activar endpoint de respaldo
kubectl apply -f k8s/ingestion-backup-endpoint.yaml

# Notificar a operadores de campo
./scripts/notify_field_operators.sh --message "Usar endpoint de respaldo"
```

## Verificación de Resolución

```bash
# Verificar latencia volvió a normal
watch -n 5 "curl -s https://metrics.castor/api/v1/query?query=histogram_quantile(0.95,castor_ingestion_duration_seconds_bucket[5m])"

# Verificar cola drenando
watch -n 10 "curl -s https://metrics.castor/api/v1/query?query=castor_forms_pending_total"

# Verificar error rate
curl -s https://metrics.castor/api/v1/query?query=rate(castor_ingestion_errors_total[5m])
```

## Criterios de Cierre

- [ ] `ingestion_latency_p95 < 2s` por 10 minutos
- [ ] `ingestion_error_rate < 0.5%`
- [ ] Cola de pending forms estable o decreciendo
- [ ] Ningún form perdido (verificar contadores)

## Post-Mortem

1. Documentar hora de inicio/fin
2. Registrar causa raíz
3. Verificar ningún E-14 perdido
4. Crear ticket de mejora si aplica

## Contactos de Escalación

| Nivel | Rol | Contacto |
|-------|-----|----------|
| L1 | SRE on-call | @sre-oncall |
| L2 | Tech Lead | @tech-lead |
| L3 | CTO | @cto |

## Referencias

- [SLO Definition](../slo_definitions.yaml#ingestion_api)
- [Architecture Diagram](../../architecture/ingestion.md)
- [QAS L1](../../qas/latency.md#L1)

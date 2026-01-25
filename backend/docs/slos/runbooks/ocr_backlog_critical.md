# Runbook: OCR Backlog Critical

**Severidad:** CRITICAL
**QAS:** L2, S1, A1
**SLO Afectado:** ocr_queue_depth > 1000

---

## Síntomas

- Alerta: `ocr_queue_depth > 1000`
- Dashboard muestra "OCR pendiente" creciendo
- Forms en estado `RECEIVED` pero no `OCR_COMPLETED`

## Impacto

- Retraso en visualización de resultados
- War Room muestra datos incompletos
- Posible timeout de jobs si backlog es muy grande

## Diagnóstico Rápido (< 2 min)

```bash
# 1. Verificar profundidad de cola
curl -s https://metrics.castor/api/v1/query?query=castor_ocr_queue_depth

# 2. Verificar workers activos
curl -s https://metrics.castor/api/v1/query?query=castor_ocr_workers_active

# 3. Verificar rate de procesamiento
curl -s https://metrics.castor/api/v1/query?query=rate(castor_forms_processed_total[5m])

# 4. Verificar API Anthropic
curl -s https://metrics.castor/api/v1/query?query=rate(castor_anthropic_requests_total{status="error"}[5m])

# 5. Verificar costo acumulado (límite de rate?)
curl -s https://metrics.castor/api/v1/query?query=increase(castor_anthropic_cost_usd[1h])
```

## Árbol de Decisión

```
┌─────────────────────────────────────────┐
│ ¿API Anthropic tiene errores?           │
└─────────────────────────────────────────┘
        │
   ┌────┴────┐
   │ SÍ      │ NO
   ▼         ▼
┌──────────┐ ┌─────────────────────────────┐
│ RUNBOOK: │ │ ¿Workers < configurados?    │
│ anthropic│ └─────────────────────────────┘
│ _failure │         │
└──────────┘   ┌─────┴─────┐
               │ SÍ        │ NO
               ▼           ▼
         ┌──────────┐ ┌─────────────────────┐
         │ Verificar│ │ ¿Rate de ingesta    │
         │ worker   │ │ > rate procesamiento│
         │ health   │ └─────────────────────┘
         └──────────┘         │
                        ┌─────┴─────┐
                        │ SÍ        │ NO
                        ▼           ▼
                  ┌──────────┐ ┌──────────────┐
                  │ Escalar  │ │ Investigar   │
                  │ workers  │ │ jobs lentos  │
                  └──────────┘ └──────────────┘
```

## Acciones de Mitigación

### Nivel 1: Escalar Workers (< 5 min)

```bash
# Escalar workers OCR
kubectl scale deployment castor-ocr-worker --replicas=20

# Verificar HPA
kubectl get hpa castor-ocr-worker

# Forzar autoscale si HPA no responde
kubectl patch hpa castor-ocr-worker -p '{"spec":{"minReplicas":15}}'
```

### Nivel 2: Optimizar Throughput (5-15 min)

```bash
# Reducir timeout por job (procesar más rápido, menos retries)
kubectl set env deployment/castor-ocr-worker OCR_TIMEOUT=180

# Aumentar concurrencia por worker
kubectl set env deployment/castor-ocr-worker CONCURRENT_JOBS=3

# Priorizar formularios críticos (departamentos clave)
kubectl set env deployment/castor-ocr-worker PRIORITY_DEPARTMENTS="11,05,76"
```

### Nivel 3: Degradación Controlada (si persiste > 20 min)

```bash
# Activar modo fast-path (solo header + totales, sin candidatos)
kubectl set env deployment/castor-ocr-worker OCR_MODE=fast_path

# Marcar forms no procesados para retry posterior
./scripts/mark_for_retry.sh --status PENDING_FULL_OCR
```

### Nivel 4: API Anthropic Rate Limit

Si el problema es rate limiting de Anthropic:

```bash
# Verificar límites
./scripts/check_anthropic_limits.sh

# Distribuir carga entre API keys
kubectl set env deployment/castor-ocr-worker ANTHROPIC_KEY_ROTATION=true

# Contactar Anthropic para aumento de límites (si día electoral)
# Teléfono emergencia: XXX-XXX-XXXX
```

## Verificación de Resolución

```bash
# Verificar cola disminuyendo
watch -n 30 "curl -s https://metrics.castor/api/v1/query?query=castor_ocr_queue_depth"

# Verificar throughput estable
watch -n 30 "curl -s https://metrics.castor/api/v1/query?query=rate(castor_forms_processed_total[5m])*60"

# Calcular tiempo estimado para drenar
./scripts/estimate_drain_time.sh
```

## Fórmulas Útiles

```
Tiempo para drenar = queue_depth / (processing_rate - ingestion_rate)

Ejemplo:
- queue_depth: 1500 forms
- processing_rate: 2 forms/s (120/min)
- ingestion_rate: 1 form/s (60/min)
- Tiempo: 1500 / (2-1) = 1500 segundos = 25 minutos
```

## Criterios de Cierre

- [ ] `ocr_queue_depth < 500` por 10 minutos
- [ ] `ocr_latency_p95 < 45s`
- [ ] Backlog en tendencia decreciente
- [ ] Ningún job en estado FAILED

## SLA de Recuperación (QAS S1)

| Backlog | Tiempo Máximo Recuperación |
|---------|---------------------------|
| 10x normal (30 min) | ≤ 20 minutos |
| 20x normal | ≤ 40 minutos |
| 50x normal | ≤ 90 minutos |

## Contactos

| Nivel | Rol | Contacto |
|-------|-----|----------|
| L1 | SRE on-call | @sre-oncall |
| L2 | ML/OCR Lead | @ml-lead |
| L3 | Anthropic Support | support@anthropic.com |

## Referencias

- [SLO Definition](../slo_definitions.yaml#ocr_pipeline)
- [Anthropic API Docs](https://docs.anthropic.com)
- [QAS S1](../../qas/scalability.md#S1)

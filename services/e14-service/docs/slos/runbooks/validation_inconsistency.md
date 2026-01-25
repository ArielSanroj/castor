# Runbook: Validation Inconsistency

**Severidad:** CRITICAL
**QAS:** I2, I3
**SLO Afectado:** validation_consistency < 100%

---

## Síntomas

- Alerta: `castor_reconciliation_discrepancies_total > 0`
- Resultados no reproducibles desde `chosen_form_id`
- Diferencias entre agregados y suma de tallies
- Auditoría reporta inconsistencias

## Impacto

- **CRÍTICO:** Integridad electoral comprometida
- Resultados no defendibles
- Pérdida de trazabilidad
- Implicaciones legales

## Diagnóstico Rápido (< 5 min)

```bash
# 1. Identificar scope de inconsistencia
psql -h db.castor -U admin -c "
SELECT
    r.scope_type, r.scope_id,
    r.sum_from_forms, r.official_count,
    r.delta, r.status
FROM reconciliation r
WHERE r.delta != 0
ORDER BY abs(r.delta) DESC
LIMIT 20;
"

# 2. Verificar forms involucrados
psql -h db.castor -U admin -c "
SELECT
    fi.id, fi.mesa_id, fi.status, fi.chosen_at,
    (SELECT sum(votes) FROM vote_tally vt WHERE vt.form_instance_id = fi.id) as tally_sum
FROM form_instance fi
WHERE fi.status = 'RECONCILED'
AND fi.id IN (
    SELECT DISTINCT form_instance_id
    FROM vote_tally
    WHERE contest_id = 'CONTEST_ID'
)
LIMIT 50;
"

# 3. Verificar audit trail
psql -h db.castor -U admin -c "
SELECT *
FROM audit_log
WHERE entity_type IN ('vote_tally', 'reconciliation')
AND created_at > now() - interval '24 hours'
ORDER BY created_at DESC
LIMIT 100;
"
```

## Clasificación de Inconsistencia

| Tipo | Descripción | Severidad | Acción |
|------|-------------|-----------|--------|
| Sum Mismatch | Σ tallies ≠ total reportado | Alta | Verificar cálculo |
| Missing Tally | Form sin tally registrado | Alta | Re-procesar |
| Duplicate Tally | Tally duplicado | Crítica | Eliminar duplicado |
| Edit without Audit | Cambio sin registro | Crítica | Forense completa |
| Chosen Form Changed | chosen_form_id modificado | Crítica | Investigar |

## Árbol de Decisión

```
┌─────────────────────────────────────────┐
│ ¿Hay audit trail completo?              │
└─────────────────────────────────────────┘
        │
   ┌────┴────┐
   │ NO      │ SÍ
   ▼         ▼
┌──────────┐ ┌─────────────────────────────┐
│ CRÍTICO  │ │ ¿Diferencia es de cálculo?  │
│ Forense  │ └─────────────────────────────┘
│ Completa │         │
└──────────┘   ┌─────┴─────┐
               │ SÍ        │ NO
               ▼           ▼
         ┌──────────┐ ┌─────────────────────┐
         │ Bug de   │ │ ¿Hay forms faltantes│
         │ código   │ │ o duplicados?       │
         │ Fix +    │ └─────────────────────┘
         │ recálculo│         │
         └──────────┘   ┌─────┴─────┐
                        │ SÍ        │ NO
                        ▼           ▼
                  ┌──────────┐ ┌──────────────┐
                  │ Verificar│ │ Investigar   │
                  │ ingesta  │ │ modificación │
                  │ y dedup  │ │ maliciosa    │
                  └──────────┘ └──────────────┘
```

## Acciones de Mitigación

### Paso 1: Congelar Área Afectada (< 2 min)

```bash
# Marcar scope como "en revisión"
psql -h db.castor -U admin -c "
UPDATE reconciliation
SET status = 'UNDER_REVIEW', reviewed_at = now()
WHERE scope_type = 'SCOPE_TYPE' AND scope_id = 'SCOPE_ID';
"

# Notificar a War Room
./scripts/notify_war_room.sh --message "Inconsistencia detectada en SCOPE_ID - En revisión"
```

### Paso 2: Diagnóstico Detallado (5-15 min)

```bash
# Script de diagnóstico completo
./scripts/diagnose_inconsistency.sh \
    --scope-type municipality \
    --scope-id "11-001" \
    --contest-id "consulta_2026_03_08" \
    --output /tmp/diagnosis_report.json
```

#### Si es Bug de Cálculo:

```bash
# Identificar el bug
./scripts/compare_calculations.sh \
    --expected "from_tallies" \
    --actual "from_reconciliation" \
    --scope-id "SCOPE_ID"

# Aplicar fix y recalcular
./scripts/recalculate_reconciliation.sh \
    --scope-id "SCOPE_ID" \
    --dry-run  # Primero dry-run

# Si dry-run es correcto, aplicar
./scripts/recalculate_reconciliation.sh \
    --scope-id "SCOPE_ID" \
    --apply \
    --audit-reason "Bug fix: [descripción]"
```

#### Si es Form Faltante:

```bash
# Verificar si el form existe
psql -h db.castor -U admin -c "
SELECT fi.*,
       (SELECT count(*) FROM vote_tally WHERE form_instance_id = fi.id) as tally_count
FROM form_instance fi
WHERE fi.mesa_id = 'MESA_ID'
AND fi.contest_id = 'CONTEST_ID';
"

# Si existe pero sin tally, re-procesar
./scripts/reprocess_form.sh --form-id FORM_ID --reason "missing_tally"

# Si no existe, verificar ingesta
./scripts/trace_form_ingestion.sh --mesa-id MESA_ID --date "2026-03-08"
```

#### Si es Modificación Sin Audit:

```bash
# CRÍTICO: Esto es potencial fraude

# 1. Preservar evidencia
pg_dump -h db.castor -U admin -t vote_tally -t audit_log --where "..." > /secure/evidence_$(date +%s).sql

# 2. Comparar con backups
./scripts/compare_with_backup.sh \
    --table vote_tally \
    --backup-time "2h ago" \
    --scope-id "SCOPE_ID"

# 3. Escalar inmediatamente
./scripts/escalate_incident.sh \
    --type "data_integrity" \
    --severity "critical" \
    --details "Modification without audit trail detected"
```

### Paso 3: Corrección Auditada

```bash
# TODA corrección debe ser auditada

# Corrección manual (si es necesaria)
psql -h db.castor -U admin -c "
BEGIN;

-- Registrar audit ANTES del cambio
INSERT INTO audit_log (
    actor_user_id, action, entity_type, entity_id,
    before_state, after_state, reason, ip_address
) VALUES (
    'system:reconciliation_fix',
    'CORRECT',
    'vote_tally',
    'TALLY_ID',
    '{\"votes\": OLD_VALUE}',
    '{\"votes\": NEW_VALUE}',
    'Corrección por inconsistencia detectada - Ticket INC-XXX',
    'internal'
);

-- Aplicar corrección
UPDATE vote_tally
SET votes = NEW_VALUE, updated_at = now()
WHERE id = 'TALLY_ID';

COMMIT;
"
```

### Paso 4: Reconstruir y Verificar

```bash
# Reconstruir agregados desde tallies
./scripts/rebuild_aggregates.sh \
    --scope-type municipality \
    --scope-id "11-001" \
    --contest-id "consulta_2026_03_08" \
    --verify-only  # Primero solo verificar

# Si verificación pasa, aplicar
./scripts/rebuild_aggregates.sh \
    --scope-type municipality \
    --scope-id "11-001" \
    --contest-id "consulta_2026_03_08" \
    --apply
```

## Verificación de Resolución

```bash
# Verificar consistencia restaurada
./scripts/verify_consistency.sh \
    --scope-id "SCOPE_ID" \
    --detailed

# Verificar audit trail completo
psql -h db.castor -U admin -c "
SELECT count(*) as changes,
       count(*) FILTER (WHERE before_state IS NOT NULL AND after_state IS NOT NULL) as fully_audited
FROM audit_log
WHERE entity_id IN (SELECT id FROM vote_tally WHERE ...)
AND created_at > now() - interval '24 hours';
"

# Verificar reproducibilidad
./scripts/reproduce_result.sh \
    --scope-id "SCOPE_ID" \
    --from "tallies" \
    --expected "official"
```

## Criterios de Cierre

- [ ] Causa raíz identificada
- [ ] Corrección aplicada con audit trail
- [ ] Consistencia verificada al 100%
- [ ] Resultado reproducible desde chosen_forms
- [ ] Documentación actualizada
- [ ] Ticket de mejora creado (si aplica)

## Reporte de Integridad

```markdown
## Reporte de Inconsistencia INC-XXXX

**Scope:** [Municipio/Departamento/Nacional]
**Contest:** [consulta_2026_03_08]
**Detectado:** [timestamp]
**Resuelto:** [timestamp]

### Causa Raíz
[Descripción]

### Impacto
- Forms afectados: X
- Diferencia máxima: Y votos
- Duración de inconsistencia: Z minutos

### Acciones Tomadas
1. [Acción 1]
2. [Acción 2]

### Verificación
- Consistencia: 100%
- Reproducibilidad: Verificada
- Audit trail: Completo

### Recomendaciones
- [Mejora 1]
- [Mejora 2]
```

## Contactos

| Rol | Contacto |
|-----|----------|
| Data Integrity Lead | @data-lead |
| Electoral Coordinator | @electoral |
| Legal | @legal |

## Referencias

- [SLO Definition](../slo_definitions.yaml#validation_engine)
- [Data Integrity Architecture](../../architecture/data_integrity.md)
- [QAS I3](../../qas/integrity.md#I3)

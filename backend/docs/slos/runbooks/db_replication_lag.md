# Runbook: Database Replication Lag

**Severidad:** CRITICAL
**QAS:** A3, S2
**SLO Afectado:** replication_lag > 5s, db_rpo

---

## Síntomas

- Alerta: `castor_db_replication_lag_seconds > 5`
- War Room muestra datos desactualizados
- Reads de réplica retornan datos viejos

## Impacto

- **RPO en riesgo:** Posible pérdida de datos si falla primary
- Dashboard desactualizado
- Inconsistencias entre vistas

## Diagnóstico Rápido (< 2 min)

```bash
# 1. Verificar lag actual
psql -h replica.db.castor -U monitor -c "SELECT pg_last_wal_receive_lsn() - pg_last_wal_replay_lsn() AS lag_bytes, now() - pg_last_xact_replay_timestamp() AS lag_time;"

# 2. Verificar carga en primary
psql -h primary.db.castor -U monitor -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"

# 3. Verificar write rate
curl -s https://metrics.castor/api/v1/query?query=rate(castor_db_writes_total[5m])

# 4. Verificar disk I/O
kubectl top pods -l app=postgres

# 5. Verificar red
ping -c 5 replica.db.castor
```

## Árbol de Decisión

```
┌─────────────────────────────────────────┐
│ ¿Réplica está conectada a primary?      │
└─────────────────────────────────────────┘
        │
   ┌────┴────┐
   │ NO      │ SÍ
   ▼         ▼
┌──────────┐ ┌─────────────────────────────┐
│ Reconectar│ │ ¿Write rate > normal?      │
│ réplica   │ └─────────────────────────────┘
└──────────┘         │
               ┌─────┴─────┐
               │ SÍ        │ NO
               ▼           ▼
         ┌──────────┐ ┌─────────────────────┐
         │ Escalar  │ │ ¿Disk I/O saturado? │
         │ writes   │ └─────────────────────┘
         │ (batch)  │         │
         └──────────┘   ┌─────┴─────┐
                        │ SÍ        │ NO
                        ▼           ▼
                  ┌──────────┐ ┌──────────────┐
                  │ Escalar  │ │ Verificar    │
                  │ storage  │ │ queries      │
                  │ IOPS     │ │ bloqueantes  │
                  └──────────┘ └──────────────┘
```

## Acciones de Mitigación

### Nivel 1: Optimizar Writes (< 5 min)

```bash
# Aumentar batch size para reducir commits
kubectl set env deployment/castor-api DB_BATCH_SIZE=1000

# Reducir fsync frequency (solo en emergencia, con cuidado)
psql -h primary.db.castor -U admin -c "ALTER SYSTEM SET synchronous_commit = 'off';"
psql -h primary.db.castor -U admin -c "SELECT pg_reload_conf();"
```

### Nivel 2: Aliviar Carga en Réplica (5-10 min)

```bash
# Redirigir reads pesados a primary (temporalmente)
kubectl set env deployment/castor-api DB_READ_FROM_PRIMARY=true

# Cancelar queries lentas en réplica
psql -h replica.db.castor -U admin -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND query_start < now() - interval '5 minutes';"
```

### Nivel 3: Escalar Storage (10-20 min)

```bash
# Aumentar IOPS de storage (AWS)
aws rds modify-db-instance --db-instance-identifier castor-replica --iops 10000

# O escalar a instancia más grande
aws rds modify-db-instance --db-instance-identifier castor-replica --db-instance-class db.r6g.2xlarge --apply-immediately
```

### Nivel 4: Failover Manual (si lag > 30s por > 10 min)

```bash
# PRECAUCIÓN: Solo si primary está en riesgo

# 1. Pausar ingesta temporalmente
kubectl scale deployment castor-api --replicas=0

# 2. Esperar que réplica alcance
watch -n 5 "psql -h replica.db.castor -U monitor -c 'SELECT now() - pg_last_xact_replay_timestamp() AS lag;'"

# 3. Promover réplica (si necesario)
aws rds promote-read-replica --db-instance-identifier castor-replica

# 4. Actualizar DNS/connection strings
kubectl set env deployment/castor-api DATABASE_URL=postgresql://new-primary...

# 5. Restaurar ingesta
kubectl scale deployment castor-api --replicas=5
```

## Verificación de Resolución

```bash
# Verificar lag volvió a normal
watch -n 10 "psql -h replica.db.castor -U monitor -c \"SELECT now() - pg_last_xact_replay_timestamp() AS lag;\""

# Verificar que réplica está sincronizada
psql -h primary.db.castor -U monitor -c "SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn FROM pg_stat_replication;"

# Verificar integridad de datos
./scripts/verify_data_integrity.sh --sample-size 100
```

## Criterios de Cierre

- [ ] `replication_lag < 1s` por 10 minutos
- [ ] Réplica en estado "streaming"
- [ ] Sin queries bloqueadas
- [ ] Verificación de integridad pasada

## Impacto en RPO

| Lag | RPO | Acción |
|-----|-----|--------|
| < 1s | OK | Normal |
| 1-5s | Warning | Monitorear |
| 5-30s | Degraded | Mitigar |
| > 30s | Critical | Considerar failover |

## Contactos

| Nivel | Rol | Contacto |
|-------|-----|----------|
| L1 | DBA on-call | @dba-oncall |
| L2 | Platform Lead | @platform-lead |
| L3 | AWS Support | Enterprise Support |

## Referencias

- [SLO Definition](../slo_definitions.yaml#database)
- [PostgreSQL HA Setup](../../architecture/database_ha.md)
- [QAS A3](../../qas/availability.md#A3)

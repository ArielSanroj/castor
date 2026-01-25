# Runbook: Security Breach / Unauthorized Access

**Severidad:** CRITICAL
**QAS:** Sec1, Sec2
**SLO Afectado:** unauthorized_access > 0

---

## Síntomas

- Alerta: `castor_authz_denied_total` con patrón sospechoso
- Alerta: Acceso a recursos fuera de alcance detectado
- Logs muestran intentos de acceso anómalos
- Usuario reporta actividad no reconocida

## Impacto

- **CRÍTICO:** Posible compromiso de integridad electoral
- Exposición de evidencia
- Pérdida de confianza pública
- Implicaciones legales

## Respuesta Inmediata (< 5 min)

### 1. Contención

```bash
# PRIORIDAD: Aislar la amenaza

# Bloquear IP sospechosa
kubectl exec -it nginx-ingress-XXX -- /bin/sh -c "echo 'deny IP.ADDRESS;' >> /etc/nginx/conf.d/blocklist.conf && nginx -s reload"

# Revocar tokens del usuario comprometido
./scripts/revoke_user_tokens.sh --user-id USER_ID --reason "security_incident"

# Si es ataque masivo, activar modo de emergencia
kubectl set env deployment/castor-api SECURITY_MODE=lockdown
```

### 2. Preservar Evidencia

```bash
# NO modificar nada antes de preservar

# Snapshot de logs
kubectl logs -l app=castor-api --since=1h > /secure/incident_$(date +%s)_api_logs.txt

# Snapshot de audit log
psql -h db.castor -U admin -c "COPY (SELECT * FROM audit_log WHERE created_at > now() - interval '2 hours') TO '/tmp/audit_snapshot.csv' WITH CSV HEADER;"

# Capturar estado de sesiones
redis-cli -h redis.castor KEYS "session:*" > /secure/incident_sessions.txt
```

## Diagnóstico

### Identificar Alcance

```bash
# 1. Identificar usuario/IP origen
grep -E "authz.*denied|403" /var/log/castor/api.log | tail -100

# 2. Ver qué recursos intentó acceder
psql -h db.castor -U admin -c "
SELECT actor_user_id, action, entity_type, entity_id, ip_address, created_at
FROM audit_log
WHERE created_at > now() - interval '2 hours'
AND (action LIKE '%denied%' OR http_status = 403)
ORDER BY created_at DESC
LIMIT 50;
"

# 3. Verificar si hubo accesos exitosos previos
psql -h db.castor -U admin -c "
SELECT action, entity_type, count(*)
FROM audit_log
WHERE actor_user_id = 'SUSPECT_USER_ID'
AND created_at > now() - interval '24 hours'
GROUP BY action, entity_type;
"

# 4. Verificar integridad de datos accedidos
./scripts/verify_data_integrity.sh --user-id SUSPECT_USER_ID --time-range "24h"
```

### Clasificar Incidente

| Tipo | Descripción | Acción |
|------|-------------|--------|
| Brute Force | Múltiples intentos de auth fallidos | Bloquear IP, monitorear |
| Privilege Escalation | Usuario accede fuera de rol | Revocar, investigar |
| Data Exfiltration | Acceso masivo a datos | Contener, forense |
| Insider Threat | Usuario legítimo abusa acceso | Suspender, investigar |

## Árbol de Decisión

```
┌─────────────────────────────────────────┐
│ ¿Es un usuario autenticado?             │
└─────────────────────────────────────────┘
        │
   ┌────┴────┐
   │ NO      │ SÍ
   ▼         ▼
┌──────────┐ ┌─────────────────────────────┐
│ Ataque   │ │ ¿Credenciales comprometidas?│
│ externo  │ └─────────────────────────────┘
│ Bloquear │         │
│ IP       │   ┌─────┴─────┐
└──────────┘   │ SÍ        │ NO
               ▼           ▼
         ┌──────────┐ ┌─────────────────────┐
         │ Revocar  │ │ ¿Abuso de privilegio│
         │ todas las│ │ legítimo?           │
         │ sesiones │ └─────────────────────┘
         └──────────┘         │
                        ┌─────┴─────┐
                        │ SÍ        │ NO
                        ▼           ▼
                  ┌──────────┐ ┌──────────────┐
                  │ Suspender│ │ Bug/Misconfig│
                  │ usuario  │ │ Fix urgente  │
                  │ Escalar  │ └──────────────┘
                  │ a Legal  │
                  └──────────┘
```

## Acciones por Tipo de Incidente

### Brute Force / Ataque Externo

```bash
# Bloquear rango de IPs si es DDoS
./scripts/block_ip_range.sh --cidr "IP.RANGE/24" --duration "24h"

# Activar CAPTCHA para login
kubectl set env deployment/castor-api REQUIRE_CAPTCHA=true

# Aumentar rate limiting
kubectl set env deployment/castor-api RATE_LIMIT_LOGIN="5 per minute"
```

### Credenciales Comprometidas

```bash
# Revocar TODOS los tokens del usuario
./scripts/revoke_user_tokens.sh --user-id USER_ID --all

# Forzar reset de password
./scripts/force_password_reset.sh --user-id USER_ID

# Notificar al usuario (canal seguro)
./scripts/notify_user_security.sh --user-id USER_ID --incident-id INC_XXX

# Revisar accesos recientes
./scripts/audit_user_access.sh --user-id USER_ID --days 7
```

### Insider Threat / Abuso de Privilegios

```bash
# Suspender cuenta inmediatamente
./scripts/suspend_user.sh --user-id USER_ID --reason "security_investigation"

# Preservar toda la actividad
./scripts/export_user_activity.sh --user-id USER_ID --output /secure/incident/

# Escalar a Legal y RRHH
./scripts/escalate_incident.sh --type "insider_threat" --user-id USER_ID
```

## Comunicación

### Interna (< 15 min)

```
Para: Security Team, CTO, Legal
Asunto: [CRITICAL] Security Incident INC-XXXX

Resumen:
- Tipo: [Brute Force / Credential Compromise / Insider]
- Usuario afectado: [USER_ID]
- Alcance: [Descripción]
- Datos potencialmente comprometidos: [Lista]
- Estado de contención: [Contenido / En progreso]

Próximos pasos:
1. [Acción 1]
2. [Acción 2]
```

### Externa (si aplica, después de Legal)

- NO comunicar hasta autorización de Legal
- Preparar statement para Registraduría si es necesario
- Documentar timeline completo

## Verificación de Resolución

```bash
# Verificar que amenaza está contenida
./scripts/verify_threat_contained.sh --incident-id INC_XXX

# Verificar integridad de datos
./scripts/verify_data_integrity.sh --full-scan

# Verificar que no hay accesos residuales
grep "USER_ID" /var/log/castor/api.log | tail -10
```

## Criterios de Cierre

- [ ] Amenaza contenida
- [ ] Evidencia preservada
- [ ] Alcance determinado
- [ ] Datos verificados íntegros
- [ ] Usuario notificado (si aplica)
- [ ] Post-mortem programado
- [ ] Legal notificado

## Obligaciones de Reporte

| Tipo de Dato | Tiempo de Reporte | A Quién |
|--------------|-------------------|---------|
| Datos electorales | 24 horas | Registraduría |
| PII | 72 horas | Superintendencia |
| Incidente mayor | Inmediato | Directivos |

## Contactos de Emergencia

| Rol | Contacto | Teléfono |
|-----|----------|----------|
| Security Lead | @security-lead | +57-XXX |
| Legal | @legal | +57-XXX |
| CTO | @cto | +57-XXX |
| Registraduría (enlace) | @registraduria | +57-XXX |

## Post-Incidente

1. **Root Cause Analysis** (24-48h)
2. **Lessons Learned** (1 semana)
3. **Mejoras de seguridad** (según findings)
4. **Simulacro futuro** (1 mes)

## Referencias

- [Incident Response Plan](../../security/incident_response.md)
- [Data Classification](../../security/data_classification.md)
- [Legal Requirements](../../compliance/data_protection.md)

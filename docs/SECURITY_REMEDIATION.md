# CASTOR ELECCIONES - Guía de Remediación de Seguridad

**URGENTE**: Este documento contiene pasos críticos de seguridad que deben ejecutarse ANTES de cualquier despliegue a producción.

---

## 1. ROTAR CREDENCIALES EXPUESTAS

Las siguientes credenciales fueron expuestas en el repositorio y DEBEN ser rotadas:

### OpenAI API Key
1. Ir a https://platform.openai.com/api-keys
2. Revocar la key existente
3. Crear una nueva key
4. Actualizar en el entorno de producción (NO en .env del repo)

### Twitter API Keys
1. Ir a https://developer.twitter.com/en/portal/dashboard
2. Regenerar todas las keys:
   - Bearer Token
   - API Key
   - API Secret
   - Access Token
   - Access Token Secret

### Twilio Credentials
1. Ir a https://console.twilio.com
2. Rotar Auth Token
3. Actualizar en el entorno de producción

### Database URL
1. Cambiar contraseña de PostgreSQL
2. Actualizar DATABASE_URL en producción

---

## 2. CONFIGURAR VARIABLES DE ENTORNO SEGURAS

### Producción (Vercel/Railway/etc)

```bash
# Generar SECRET_KEY seguro
python -c "import secrets; print(secrets.token_hex(32))"

# Configurar en el dashboard de tu plataforma:
SECRET_KEY=<generated_key>
JWT_SECRET_KEY=<another_generated_key>
OPENAI_API_KEY=<new_rotated_key>
TWITTER_BEARER_TOKEN=<new_rotated_token>
DATABASE_URL=<connection_string>
```

### Desarrollo Local

1. Copiar `.env.example` a `.env`:
```bash
cp .env.example .env
```

2. Generar keys locales:
```bash
python -c "import secrets; print(f'SECRET_KEY={secrets.token_hex(32)}')" >> .env
```

---

## 3. VERIFICAR .GITIGNORE

Confirmar que estos archivos NO están tracked:

```bash
# Verificar estado
git status

# Si .env está tracked, removerlo:
git rm --cached .env
git rm --cached backend/app/.env
git rm --cached .env.bak

# Commit los cambios
git add .gitignore
git commit -m "security: remove sensitive files from tracking"
```

---

## 4. ELIMINAR ARCHIVOS SENSIBLES DEL HISTORIAL

Si las credenciales fueron commiteadas, eliminarlas del historial:

```bash
# ADVERTENCIA: Esto reescribe el historial de git
# Hacer backup primero

# Opción 1: BFG Repo-Cleaner (recomendado)
bfg --delete-files .env

# Opción 2: git filter-branch
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' \
  --prune-empty --tag-name-filter cat -- --all

# Forzar push (coordinar con el equipo)
git push origin --force --all
```

---

## 5. CHECKLIST DE SEGURIDAD PRE-DEPLOY

- [ ] SECRET_KEY configurado (min 32 chars)
- [ ] JWT_SECRET_KEY configurado (min 32 chars)
- [ ] Todas las API keys rotadas
- [ ] .env NO está en el repositorio
- [ ] DEBUG=False en producción
- [ ] CORS_ORIGINS configurado correctamente
- [ ] Rate limiting habilitado
- [ ] HTTPS forzado
- [ ] Logs no exponen información sensible

---

## 6. MONITOREO POST-DEPLOY

### Verificar que no hay fugas
1. Revisar logs de acceso
2. Monitorear uso de APIs (OpenAI, Twitter)
3. Alertas de rate limiting

### Herramientas recomendadas
- GitHub Secret Scanning (habilitado por defecto)
- Snyk para dependencias
- Sentry para error tracking

---

## Contacto de Seguridad

Si descubres una vulnerabilidad, reportar a: [security@tudominio.com]

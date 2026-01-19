# 🔧 Troubleshooting - Castor Elecciones

## ❌ Problema: La página no tiene estilos (solo texto plano)

### Síntoma
Ves todo el contenido pero sin formato, colores ni diseño. Solo texto plano.

### Causas Comunes

#### 1. Puerto Incorrecto ⚠️
```
❌ INCORRECTO: http://localhost:5011/webpage
✅ CORRECTO:   http://localhost:5001/webpage
```

**Solución:** Verifica en qué puerto está corriendo el servidor

```bash
# Ver qué puertos están en uso
lsof -ti:5001
lsof -ti:5011

# El servidor por defecto corre en 5001
# Si configuraste otro puerto, úsalo
```

#### 2. CSS No Se Carga
**Solución:** Abre DevTools (F12) y verifica:

```
1. Console → Busca errores tipo:
   "Failed to load resource: static/css/styles.css"

2. Network → Filtra por "CSS"
   - styles.css debe aparecer
   - Status debe ser 200 (OK)
   - Si es 404, hay problema de ruta

3. Verifica que el archivo existe:
   ls -la static/css/styles.css
```

#### 3. Cache del Navegador
**Solución:** Forzar recarga sin cache

```
Chrome/Edge:  Ctrl + Shift + R  (Windows/Linux)
              Cmd + Shift + R   (Mac)

Firefox:      Ctrl + F5          (Windows/Linux)
              Cmd + Shift + R   (Mac)

Safari:       Cmd + Option + R  (Mac)
```

#### 4. Servidor No Corriendo
**Solución:** Reiniciar el servidor

```bash
# Matar proceso anterior
pkill -f "python.*backend"

# Arrancar de nuevo
cd /Users/arielsanroj/castor
python3 backend/main.py
```

---

## ✅ Verificación Paso a Paso

### Paso 1: Verificar Servidor
```bash
# Debe mostrar el proceso Python
ps aux | grep "python.*backend" | grep -v grep

# Debe mostrar el PID
lsof -ti:5001
```

### Paso 2: Verificar Archivos
```bash
# Todos deben existir
ls -la static/css/styles.css
ls -la static/js/main.js
ls -la static/js/performance.js
ls -la templates/webpage.html
```

### Paso 3: Probar Endpoint Directo
```bash
# Debe devolver CSS
curl -I http://localhost:5001/static/css/styles.css

# Debe devolver: HTTP/1.1 200 OK
```

### Paso 4: Verificar HTML
```bash
# Debe contener el link al CSS
curl -s http://localhost:5001/webpage | grep "styles.css"

# Output esperado:
# <link rel="stylesheet" href="/static/css/styles.css">
```

---

## 🌐 URLs Correctas

### ✅ Landing Principal
```
http://localhost:5001/webpage
```

### ✅ Productos
```
http://localhost:5001/media
http://localhost:5001/campaign
```

### ✅ Assets Estáticos
```
http://localhost:5001/static/css/styles.css
http://localhost:5001/static/js/main.js
http://localhost:5001/static/js/performance.js
```

---

## 🔍 Debugging en DevTools

### Chrome DevTools (F12)

#### 1. Console
```javascript
// Ejecuta esto en console
document.querySelector('link[href*="styles.css"]')
// Debe retornar: <link rel="stylesheet" href="/static/css/styles.css">

// Verifica variables CSS
getComputedStyle(document.documentElement).getPropertyValue('--accent')
// Debe retornar: "#FF6A3D"
```

#### 2. Network Tab
```
1. Abre Network tab
2. Recarga página (F5)
3. Busca "styles.css"
4. Verifica:
   ✓ Status: 200
   ✓ Type: stylesheet
   ✓ Size: ~38KB
```

#### 3. Elements Tab
```
1. Inspecciona <html>
2. En Styles panel, busca:
   :root {
     --bg: #0A0E1A;
     --accent: #FF6A3D;
   }
3. Si no aparece, CSS no se cargó
```

---

## 🚨 Errores Comunes y Soluciones

### Error 1: "404 Not Found" para CSS

```bash
# Verificar configuración Flask
# En backend/main.py o backend/config.py

# Debe haber:
app = Flask(__name__, 
            static_folder='../static',
            template_folder='../templates')
```

### Error 2: "MIME type text/html" warning

```bash
# Verificar extensión del archivo
ls -la static/css/styles.css
# NO debe ser: styles.css.txt

# Verificar Content-Type header
curl -I http://localhost:5001/static/css/styles.css
# Debe incluir: Content-Type: text/css
```

### Error 3: Estilos no se aplican

```bash
# Verificar que body tiene clase "landing"
curl -s http://localhost:5001/webpage | grep -o '<body.*>'
# Debe incluir: class="landing"

# Verificar selector en CSS
grep -n "body.landing" static/css/styles.css
grep -n ".landing" static/css/styles.css
```

---

## 🔄 Reset Completo

Si nada funciona, reset completo:

```bash
# 1. Matar todos los procesos
pkill -f "python.*backend"

# 2. Limpiar cache de Python
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete

# 3. Verificar archivos
ls -la static/css/styles.css      # Debe existir
ls -la templates/webpage.html     # Debe existir

# 4. Arrancar servidor limpio
cd /Users/arielsanroj/castor
python3 backend/main.py

# 5. Abrir en navegador NUEVO (incógnito)
# http://localhost:5001/webpage
```

---

## 📊 Checklist Final

Antes de reportar un bug:

- [ ] Servidor corriendo en puerto 5001
- [ ] URL correcta: `http://localhost:5001/webpage`
- [ ] CSS existe: `static/css/styles.css`
- [ ] CSS se carga: Status 200 en Network tab
- [ ] No hay errores en Console
- [ ] Cache limpio (Ctrl+Shift+R)
- [ ] Navegador moderno (Chrome 120+, Firefox 121+)
- [ ] JavaScript habilitado

---

## 🎯 Verificación Visual Esperada

Si todo está correcto, debes ver:

### ✅ Header
- Logo de Castor (arriba izquierda)
- Navegación horizontal con links
- Fondo oscuro (#0A0E1A)
- Botones naranjas (#FF6A3D)

### ✅ Hero Section
- Título grande con gradiente
- Texto gris claro (#F5F7FA)
- 2 botones con íconos
- Fondo azul petróleo

### ✅ Métricas
- 4 cards con bordes
- Números grandes en naranja
- Fondo panel (#141824)

### ✅ Animaciones
- Al hacer scroll, cards aparecen con fade-in
- Hover en botones: elevación + sombra
- Hover en cards: borde naranja

---

## 📞 Soporte Adicional

Si el problema persiste:

1. **Screenshot:** Toma captura de pantalla
2. **Console Errors:** Copia errores de DevTools
3. **Network Tab:** Screenshot del tab Network
4. **Versión:** ¿Qué navegador y versión?

**Contacto:** dev@castor-elecciones.com

---

## 🔗 Enlaces Útiles

- **Guía de Testing:** `TESTING_GUIDE.md`
- **Quick Start:** `QUICK_START.md`
- **Reporte Técnico:** `OPTIMIZATION_REPORT.md`
- **Este archivo:** `TROUBLESHOOTING.md`

---

## 🎓 Tips Pro

### Usar puerto diferente
```bash
# Si 5001 está ocupado
FLASK_APP=backend.main flask run --port 5011

# Entonces usa:
http://localhost:5011/webpage
```

### Ver logs del servidor
```bash
# Arrancar con verbose
python3 backend/main.py --debug

# Ver requests en tiempo real
tail -f backend/logs/app.log  # Si existe
```

### Verificar configuración
```python
# En Python interactive shell
python3 -c "
from backend.config import Config
print(f'HOST: {Config.HOST}')
print(f'PORT: {Config.PORT}')
"
```

---

**Última actualización:** 28 Nov 2026  
**Versión:** 1.0

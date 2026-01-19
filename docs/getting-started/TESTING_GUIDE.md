# 🧪 Guía de Testing - Castor Elecciones

**Versión:** 2.0  
**Fecha:** 28 de Noviembre, 2026

---

## 🚀 Cómo Acceder a la Nueva Landing

### Opción 1: Arrancar el Servidor

```bash
# Desde la raíz del proyecto
cd /Users/arielsanroj/castor

# Opción A: Python directo
python3 backend/main.py

# Opción B: Flask CLI
FLASK_APP=backend.main flask run
```

### Acceso en el Navegador

```
🌐 Landing Principal:  http://localhost:5001/webpage
📰 CASTOR Medios:      http://localhost:5001/media
🎯 CASTOR Campañas:    http://localhost:5001/campaign
```

**Nota:** Si el puerto es diferente (ej: 5011), ajusta la URL.

---

## ✅ Checklist de Verificación

### 1. **SEO Técnico**

Abre `http://localhost:5001/webpage` y:

- [ ] **Ver fuente de la página** (Ctrl/Cmd + U)
  - Verifica `<title>` optimizado
  - Busca `<meta property="og:` (Open Graph)
  - Busca `<script type="application/ld+json">` (Structured Data)
  
- [ ] **Chrome DevTools → Console**
  - No debe haber errores críticos
  
- [ ] **Lighthouse (DevTools → Lighthouse)**
  - SEO Score: >90
  - Verifica structured data

### 2. **Accesibilidad WCAG**

- [ ] **Navegación por teclado**
  - Presiona `Tab` repetidamente
  - Debe haber focus visible (anillo naranja)
  - Skip link debe aparecer al presionar Tab
  
- [ ] **Modal de demo**
  - Clic en "Solicitar demo"
  - Presiona `Tab`: focus debe estar atrapado en modal
  - Presiona `Escape`: modal debe cerrarse
  
- [ ] **Screen reader** (opcional)
  - macOS: Cmd + F5 (VoiceOver)
  - Windows: NVDA o JAWS
  - Verifica que lee aria-labels correctamente

- [ ] **Contraste**
  - Chrome DevTools → Lighthouse → Accessibility
  - Contrast ratio debe ser AA o AAA

### 3. **Rendimiento Técnico**

- [ ] **Google PageSpeed Insights**
  - Ve a: https://pagespeed.web.dev/
  - (Para producción, no localhost)
  - Target: >90 en móvil, >95 en desktop
  
- [ ] **Chrome DevTools → Performance**
  - Graba 5-10 segundos de carga
  - LCP debe ser <2.5s (verde)
  
- [ ] **Network tab**
  - Verifica que `performance.js` tiene `defer`
  - Verifica lazy loading de imágenes
  - Chart.js debe cargar después

- [ ] **Console logs** (solo en localhost)
  - Debe mostrar: "LCP:", "FID:", "CLS:"
  - Valores deben ser verdes

### 4. **UI/UX y Responsive**

- [ ] **Desktop (1920x1080)**
  - Todo el contenido debe verse bien espaciado
  - Animaciones deben ejecutarse al hacer scroll
  - Hover effects en cards y botones
  
- [ ] **Tablet (768x1024)**
  - Grid de métricas: 2 columnas
  - Productos: 1 columna
  - Navegación debe adaptarse
  
- [ ] **Mobile (375x667)**
  - Todo en 1 columna
  - CTAs full-width
  - Menú mobile debe mostrarse (botón hamburguesa)
  - Touch targets >44x44px

- [ ] **Animaciones**
  - Scroll hacia abajo
  - Cards deben aparecer con fade-in
  - Delay escalonado (0.1s, 0.2s, 0.3s, 0.4s)

### 5. **Conversión y Formularios**

- [ ] **Modal de demo**
  - Clic en "Solicitar demo"
  - Validación en tiempo real:
    - Email inválido → error message
    - Campo vacío → "Este campo es obligatorio"
    - Teléfono <10 dígitos → error
  
- [ ] **Submit del formulario**
  - Debe mostrar spinner "Enviando..."
  - Success message después de 1.5s
  - Modal debe cerrarse automáticamente
  
- [ ] **CTAs principales**
  - "Ver CASTOR Medios" → `/media`
  - "Explorar CASTOR Campañas" → `/campaign`
  - Hover effect: ripple + elevación

---

## 🔍 Testing con Herramientas Profesionales

### Lighthouse (Chrome DevTools)

```bash
# Instalar Lighthouse CLI (opcional)
npm install -g lighthouse

# Ejecutar audit
lighthouse http://localhost:5001/webpage --view
```

**Targets:**
- Performance: >90
- Accessibility: >95
- Best Practices: >90
- SEO: >95

### WAVE Accessibility

```bash
# En producción, usar:
# https://wave.webaim.org/
# Pegar URL de producción
```

**Verifica:**
- 0 errores de contraste
- Todos los íconos tienen aria-hidden="true"
- Formularios tienen labels

### Google PageSpeed Insights

```bash
# Solo funciona con URLs públicas
# https://pagespeed.web.dev/
```

**Core Web Vitals:**
- LCP: <2.5s (verde)
- FID: <100ms (verde)
- CLS: <0.1 (verde)

---

## 🐛 Troubleshooting

### El servidor no arranca

```bash
# Verifica el puerto
lsof -ti:5001

# Si está ocupado, mata el proceso
kill -9 $(lsof -ti:5001)

# O usa otro puerto
FLASK_APP=backend.main flask run --port 5011
```

### Errores en consola

```bash
# Verifica que performance.js existe
ls -la static/js/performance.js

# Verifica permisos
chmod 644 static/js/performance.js
```

### Animaciones no funcionan

```bash
# Abre DevTools → Console
# Debe mostrar:
# "SW registered" o "SW registration failed"

# Si hay error, verifica:
# 1. Intersection Observer soportado
# 2. JavaScript habilitado
# 3. No hay errores de sintaxis
```

### Modal no se abre

```bash
# Console debe mostrar error
# Verifica que existe:
document.getElementById('demoModal')

# Y que la función está definida:
typeof openDemoModal === 'function'
```

---

## 📱 Testing Cross-Browser

### Desktop

- [x] **Chrome 120+** (principal)
- [ ] **Firefox 121+**
- [ ] **Safari 17+** (macOS)
- [ ] **Edge 120+**

### Mobile

- [ ] **iOS Safari** (iPhone 12+)
- [ ] **Chrome Android** (Pixel 6+)
- [ ] **Samsung Internet**

### Simulación en Chrome DevTools

```
1. DevTools → Toggle device toolbar (Cmd/Ctrl + Shift + M)
2. Selecciona dispositivo:
   - iPhone 14 Pro
   - iPad Pro
   - Samsung Galaxy S21
3. Rotación: Portrait y Landscape
```

---

## 🎯 Test Cases Específicos

### Test 1: Lazy Loading de Imágenes

```javascript
// Abre Console
// Scroll hasta el footer
// Verifica que las imágenes cargan cuando entran al viewport

const images = document.querySelectorAll('img[loading="lazy"]');
console.log(`${images.length} imágenes lazy`);

// Verifica que tienen clase 'loaded' después de cargar
```

### Test 2: Focus Trap en Modal

```javascript
// 1. Tab hasta "Solicitar demo"
// 2. Enter para abrir modal
// 3. Tab varias veces
// 4. Verificar que focus no sale del modal
// 5. Shift+Tab debe navegar hacia atrás
// 6. Escape cierra modal
```

### Test 3: Validación de Formulario

```javascript
// 1. Abrir modal
// 2. Submit vacío → deben aparecer 5 errores
// 3. Email "invalid" → error específico
// 4. Teléfono "123" → error de longitud
// 5. Llenar correctamente → success message
```

### Test 4: Scroll Animations

```javascript
// Abre Console
const animatedElements = document.querySelectorAll('.animate-on-scroll');
console.log(`${animatedElements.length} elementos animados`);

// Scroll despacio
// Cada card debe aparecer con fade-in cuando es visible
```

### Test 5: Responsive Breakpoints

```
1. Desktop (1920px):
   - Métricas: 4 columnas
   - Productos: 2 columnas
   - Nav: horizontal

2. Tablet (768px):
   - Métricas: 2 columnas
   - Productos: 1 columna
   - Nav: horizontal

3. Mobile (375px):
   - Todo: 1 columna
   - Nav: botón hamburguesa
   - CTAs: full-width
```

---

## 📊 Métricas de Éxito

### Performance

```bash
# Lighthouse CLI
lighthouse http://localhost:5001/webpage --only-categories=performance --quiet

# Target: >90
```

### Accessibility

```bash
# axe-core CLI
npm install -g @axe-core/cli
axe http://localhost:5001/webpage

# Target: 0 violations
```

### SEO

```bash
# Lighthouse CLI
lighthouse http://localhost:5001/webpage --only-categories=seo --quiet

# Target: >95
```

---

## 🔧 Debugging Tips

### Ver todos los aria-labels

```javascript
// En Console
const ariaElements = document.querySelectorAll('[aria-label]');
console.table(Array.from(ariaElements).map(el => ({
  tag: el.tagName,
  label: el.getAttribute('aria-label')
})));
```

### Verificar Structured Data

```javascript
// En Console
const structuredData = document.querySelector('script[type="application/ld+json"]');
console.log(JSON.parse(structuredData.textContent));

// O usar: https://search.google.com/test/rich-results
```

### Monitor de Performance

```javascript
// En Console (solo localhost)
// Debe mostrar métricas automáticamente:
// - LCP (Largest Contentful Paint)
// - FID (First Input Delay)
// - CLS (Cumulative Layout Shift)
```

---

## ✅ Sign-off Checklist

Antes de marcar como completo:

- [ ] Landing carga en <2 segundos
- [ ] Lighthouse Performance >90
- [ ] Lighthouse Accessibility >95
- [ ] Lighthouse SEO >95
- [ ] 0 errores en Console
- [ ] Modal funciona correctamente
- [ ] Formulario valida correctamente
- [ ] Responsive en mobile/tablet/desktop
- [ ] Animaciones se ejecutan suavemente
- [ ] Focus visible en todos los elementos
- [ ] Keyboard navigation funciona
- [ ] Screen reader compatible (opcional)

---

## 📞 Soporte

Si encuentras algún problema:

1. **Revisar Console** para errores JavaScript
2. **Revisar Network** para recursos no cargados
3. **Leer OPTIMIZATION_REPORT.md** para contexto
4. **Contactar:** dev@castor-elecciones.com

---

## 🎓 Recursos Adicionales

### Documentación
- `/OPTIMIZATION_REPORT.md` - Reporte técnico completo
- `/static/js/performance.js` - Código de optimizaciones
- `/static/css/styles.css` - Estilos mejorados

### Herramientas Online
- https://pagespeed.web.dev/ - PageSpeed Insights
- https://wave.webaim.org/ - Accessibility testing
- https://search.google.com/test/rich-results - Structured data
- https://validator.w3.org/ - HTML validation

### Extensiones Chrome Recomendadas
- Lighthouse
- axe DevTools
- WAVE Evaluation Tool
- Web Vitals
- React Developer Tools (si aplica)

---

**Happy Testing! 🚀**

Si todo se ve bien, la optimización está completa y lista para producción.

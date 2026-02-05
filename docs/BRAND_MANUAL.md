# Manual de Marca CASTOR - Colores UI/UX

## 1. Principio Rector

> **El software no es un póster. Es una herramienta.**

Los colores deben:
- No cansar
- No distraer
- Guiar sin gritar
- Reflejar precisión y control

---

## 2. Paleta Base (Colores Estructurales)

El **70-80% de la UI** debe usar estos colores.

| Elemento | Color | Hex |
|----------|-------|-----|
| Fondo principal | Blanco suave | `#FFFFFF` |
| Fondo alternativo | Arena muy clara | `#F7F4EE` |
| Superficies secundarias (cards, paneles) | Arena neutra | `#E6E1D8` |
| Texto principal | Negro profundo | `#111111` |
| Texto secundario | Gris oscuro | `#444444` |
| Texto terciario / labels | Gris medio | `#777777` |

---

## 3. Color de Acción

> **CASTOR no usa colores agresivos.**
> **Nunca azul corporativo por defecto.**
> **Nunca más de un color de acción.**

| Estado | Color | Hex |
|--------|-------|-----|
| **Primario de acción** | Gris cálido profundo | `#6F6A63` |
| Hover | Gris cálido oscuro | `#5E5A54` |
| Active | Gris cálido intenso | `#4E4A45` |

**Uso:**
- Botón principal
- Estados activos
- Elementos seleccionados

---

## 4. Estados del Sistema

> **CASTOR comunica estados sin drama.**
> Usados con moderación, preferiblemente con texto o icono.
> Nunca como fondo dominante.

| Estado | Nombre | Hex |
|--------|--------|-----|
| Éxito | Arena oscura / Verdencia | `#C2A96D` |
| Error | Rojo profundo desaturado | `#8F4A4A` |
| Advertencia | Marrón cálido | `#8B7355` |
| Info | Gris frío | `#7A7F85` |

---

## 5. Modo Oscuro (si se usa)

> **Debe sentirse silencioso, no gamer.**
> Nada de negro puro + blanco puro.

| Elemento | Color | Hex |
|----------|-------|-----|
| Fondo | Negro carbón | `#141414` |
| Superficies | Gris oscuro | `#1F1F1F` |
| Texto principal | Blanco roto | `#F2F2F2` |
| Texto secundario | Gris medio | `#B0B0B0` |
| Acción | Gris cálido | `#BFB8AE` |

---

## 6. Proporción Correcta en UI

```
80% neutros (blancos, arenas, grises)
15% estructura (cards, divisores)
 5% acción y estados
```

> **Si ves muchos colores → algo está mal.**

---

## 7. Prohibiciones

El software CASTOR **NO debe tener:**

- ❌ Gradientes
- ❌ Colores saturados
- ❌ Azul default de frameworks
- ❌ Fondos oscuros con texto gris claro sin contraste
- ❌ Más de un color primario
- ❌ "Micro-colores" decorativos
- ❌ Efectos glow o brillos

> **CASTOR no decora, ordena.**

---

## 8. Variables CSS

```css
:root {
    /* Colores estructurales */
    --bg: #FFFFFF;
    --bg-alt: #F7F4EE;
    --sand: #E6E1D8;
    --panel: #FFFFFF;
    --panel-alt: #F7F4EE;
    --border: #E6E1D8;

    /* Texto */
    --text: #111111;
    --text-secondary: #444444;
    --text-tertiary: #777777;
    --muted: #777777;

    /* Acción */
    --accent: #6F6A63;
    --accent-hover: #5E5A54;
    --accent-active: #4E4A45;
    --accent-light: rgba(111, 106, 99, 0.1);

    /* Estados */
    --success: #C2A96D;
    --warning: #8B7355;
    --danger: #8F4A4A;
    --error: #8F4A4A;
    --info: #7A7F85;
}
```

---

## 9. Logo

El logo oficial de CASTOR se encuentra en:
- `/static/images/logo.png` (PNG)
- `/static/images/logo.jpg` (JPG)

Características:
- Diseño line-art minimalista de un castor
- Color de líneas: `#3E3A35` (marrón oscuro)
- Fondo: `#B8B0A6` (beige/arena)
- Tipografía integrada "CASTOR"
- Estilo: trazo continuo, elegante, profesional

---

## 10. Tipografía

| Uso | Fuente |
|-----|--------|
| Display / Títulos | Playfair Display |
| Cuerpo / UI | Source Sans 3 |

---

*Última actualización: 2026-02-04*
*Versión: 1.0*

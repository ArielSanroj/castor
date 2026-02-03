# CASTOR ELECCIONES - Índice de Diagramas de Arquitectura

## Diplomado en Arquitectura de Software - Proyecto Final

---

## Documentos Generados

### 1. Documento Principal de Arquitectura
- **Archivo:** [`arquitectura del proyecto.md`](arquitectura%20del%20proyecto.md)
- **Contenido:** Documento completo del proyecto con descripción funcional, tecnologías, módulos y características del sistema.

---

### 2. Diagrama C4 (Context, Containers, Components, Code)
- **Archivo:** [`diagrama-c4.md`](diagrama-c4.md)
- **Contenido:**
  - Nivel 1: Diagrama de Contexto del Sistema
  - Nivel 2: Diagrama de Contenedores
  - Nivel 3: Diagrama de Componentes
  - Nivel 4: Diagrama de Código

---

### 3. Diagrama de Despliegue
- **Archivo:** [`diagrama-despliegue.md`](diagrama-despliegue.md)
- **Contenido:**
  - Infraestructura Docker
  - Topología de Red
  - Configuración de Puertos
  - Docker Compose completo

---

### 4. Diagrama de Secuencia
- **Archivo:** [`diagrama-secuencia.md`](diagrama-secuencia.md)
- **Contenido:**
  - SD-01: Autenticación y Login
  - SD-02: Análisis de Campaña en Twitter
  - SD-03: Procesamiento OCR de Formulario E-14
  - SD-04: Consulta al Chat RAG
  - SD-05: Generación de Pronóstico Electoral
  - SD-06: Revisión HITL (Human-in-the-Loop)

---

### 5. Diagrama Entidad-Relación
- **Archivo:** [`diagrama-entidad-relacion.md`](diagrama-entidad-relacion.md)
- **Contenido:**
  - Base de datos core_db (Usuarios, Campañas, Análisis)
  - Base de datos e14_db (Formularios Electorales)
  - Base de datos dashboard_db (War Room, Alertas)
  - Scripts DDL completos

---

### 6. Diagrama de Casos de Uso
- **Archivo:** [`diagrama-casos-de-uso.md`](diagrama-casos-de-uso.md)
- **Contenido:**
  - 5 Actores del sistema
  - 18 Casos de uso documentados
  - Matriz Actor-Caso de Uso
  - Especificaciones detalladas

---

### 7. Diagrama de Clases
- **Archivo:** [`diagrama-clases.md`](diagrama-clases.md)
- **Contenido:**
  - ~70 clases organizadas por paquetes
  - 16 enumeraciones
  - 4 interfaces principales
  - Relaciones y cardinalidades

---

### 8. Diagrama de Estados
- **Archivo:** [`diagrama-estados.md`](diagrama-estados.md)
- **Contenido:**
  - STM-01: Estados de FormInstance
  - STM-02: Estados de Alert
  - STM-03: Estados de Reconciliation
  - STM-04: Estados de Session
  - STM-05: Estados de Lead
  - STM-06: Estados de Analysis
  - STM-07: Estados de Election
  - STM-08: Estados de CircuitBreaker

---

### 9. Diagrama de Actividades
- **Archivo:** [`diagrama-actividades.md`](diagrama-actividades.md)
- **Contenido:**
  - ACT-01: Login y Autenticación
  - ACT-02: Análisis de Campaña
  - ACT-03: Procesamiento OCR E-14
  - ACT-04: Consulta Chat RAG
  - ACT-05: Generación de Pronóstico
  - ACT-06: Revisión HITL
  - ACT-07: Generación de Reporte
  - ACT-08: Gestión de Alertas

---

### 10. Diagrama de Componentes
- **Archivo:** [`diagrama-componentes.md`](diagrama-componentes.md)
- **Contenido:**
  - ~40 componentes organizados por capas
  - Interfaces provistas y requeridas
  - Dependencias entre componentes
  - 4 microservicios documentados

---

### 11. Diagrama de Paquetes
- **Archivo:** [`diagrama-paquetes.md`](diagrama-paquetes.md)
- **Contenido:**
  - Estructura completa de directorios
  - Dependencias entre paquetes
  - Matriz de dependencias
  - Visibilidad pública/privada

---

## Resumen de Artefactos

| # | Diagrama | Archivo | Tipo UML |
|---|----------|---------|----------|
| 1 | Arquitectura General | `arquitectura del proyecto.md` | Documento |
| 2 | C4 Model | `diagrama-c4.md` | Estructural |
| 3 | Despliegue | `diagrama-despliegue.md` | Estructural |
| 4 | Secuencia | `diagrama-secuencia.md` | Comportamiento |
| 5 | Entidad-Relación | `diagrama-entidad-relacion.md` | Estructural |
| 6 | Casos de Uso | `diagrama-casos-de-uso.md` | Comportamiento |
| 7 | Clases | `diagrama-clases.md` | Estructural |
| 8 | Estados | `diagrama-estados.md` | Comportamiento |
| 9 | Actividades | `diagrama-actividades.md` | Comportamiento |
| 10 | Componentes | `diagrama-componentes.md` | Estructural |
| 11 | Paquetes | `diagrama-paquetes.md` | Estructural |

---

## Tecnologías Documentadas

```
┌─────────────────────────────────────────────────────────────────┐
│                    STACK TECNOLÓGICO                            │
├─────────────────────────────────────────────────────────────────┤
│  Frontend      │ Jinja2, Bootstrap 5, Chart.js                  │
│  Backend       │ Python 3.11, Flask 3.0, SQLAlchemy 2.0         │
│  Bases Datos   │ PostgreSQL 15, Redis 7.0, ChromaDB             │
│  IA/ML         │ OpenAI GPT-4o, Anthropic Claude 3.5, BETO      │
│  APIs          │ Twitter API v2, JWT Authentication             │
│  DevOps        │ Docker, Docker Compose, Nginx                  │
│  Patrones      │ Microservicios, Circuit Breaker, CQRS          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Estadísticas del Proyecto

- **Líneas de código:** ~71,805
- **Endpoints API:** 50+
- **Microservicios:** 4
- **Bases de datos:** 3
- **Tablas:** 30+
- **Clases documentadas:** ~70
- **Casos de uso:** 18
- **Componentes:** ~40

---

**Proyecto:** CASTOR ELECCIONES
**Versión:** 1.0.0
**Fecha:** Enero 2026
**Diplomado:** Arquitectura de Software - Proyecto Final

# Diagramas de Casos de Uso - CASTOR ELECCIONES

## 1. Identificación de Actores

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    ACTORES                                           │
└─────────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐
    │  ┌───┐  │      │  ┌───┐  │      │  ┌───┐  │      │  ┌───┐  │      │ ┌─────┐ │
    │  │ ☺ │  │      │  │ ☺ │  │      │  │ ☺ │  │      │  │ ☺ │  │      │ │ ≡≡≡ │ │
    │  └─┬─┘  │      │  └─┬─┘  │      │  └─┬─┘  │      │  └─┬─┘  │      │ │ ≡≡≡ │ │
    │   /│\   │      │   /│\   │      │   /│\   │      │   /│\   │      │ └─────┘ │
    │   / \   │      │   / \   │      │   / \   │      │   / \   │      │         │
    └────┬────┘      └────┬────┘      └────┬────┘      └────┬────┘      └────┬────┘
         │                │                │                │                │
    Analista de      Observador       Administrador      Usuario         Sistema
      Campaña        Electoral        del Sistema        Invitado        Externo
```

### Descripción de Actores

| Actor | Descripción | Permisos |
|-------|-------------|----------|
| **Analista de Campaña** | Usuario principal que analiza sentimiento, genera estrategias y pronósticos | Análisis completo, chat RAG, pronósticos, reportes |
| **Observador Electoral** | Persona en campo que sube formularios E-14 y reporta incidentes | Subir formularios, reportar incidentes, ver estado |
| **Administrador** | Gestiona usuarios, revisa formularios, resuelve alertas | Acceso total, CRUD usuarios, revisión HITL, alertas |
| **Usuario Invitado** | Acceso limitado solo lectura | Ver dashboards públicos, trending topics |
| **Sistema Externo** | APIs externas (Twitter, OpenAI, Anthropic) | Proveer datos y servicios de IA |

---

## 2. Diagrama General de Casos de Uso

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           CASTOR ELECCIONES - SISTEMA                                │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                               │  │
│  │                         MÓDULO DE AUTENTICACIÓN                               │  │
│  │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │  │
│  │   │  Registrarse    │  │ Iniciar Sesión  │  │  Cerrar Sesión  │              │  │
│  │   │     (UC-01)     │  │     (UC-02)     │  │     (UC-03)     │              │  │
│  │   └─────────────────┘  └─────────────────┘  └─────────────────┘              │  │
│  │                                                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                               │  │
│  │                      MÓDULO DE ANÁLISIS DE CAMPAÑA                            │  │
│  │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │  │
│  │   │    Analizar     │  │    Consultar    │  │     Generar     │              │  │
│  │   │   Sentimiento   │  │  Trending Topics│  │    Estrategia   │              │  │
│  │   │     (UC-04)     │  │     (UC-05)     │  │     (UC-06)     │              │  │
│  │   └─────────────────┘  └─────────────────┘  └─────────────────┘              │  │
│  │                                                                               │  │
│  │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │  │
│  │   │     Generar     │  │   Chatear con   │  │      Ver        │              │  │
│  │   │    Discurso     │  │   Asistente IA  │  │   Pronósticos   │              │  │
│  │   │     (UC-07)     │  │     (UC-08)     │  │     (UC-09)     │              │  │
│  │   └─────────────────┘  └─────────────────┘  └─────────────────┘              │  │
│  │                                                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                               │  │
│  │                       MÓDULO ELECTORAL (E-14)                                 │  │
│  │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │  │
│  │   │     Subir       │  │   Procesar OCR  │  │    Validar      │              │  │
│  │   │   Formulario    │  │  de Formulario  │  │   Formulario    │              │  │
│  │   │     (UC-10)     │  │     (UC-11)     │  │     (UC-12)     │              │  │
│  │   └─────────────────┘  └─────────────────┘  └─────────────────┘              │  │
│  │                                                                               │  │
│  │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │  │
│  │   │     Revisar     │  │    Gestionar    │  │      Ver        │              │  │
│  │   │   Manualmente   │  │     Alertas     │  │   Resultados    │              │  │
│  │   │     (UC-13)     │  │     (UC-14)     │  │     (UC-15)     │              │  │
│  │   └─────────────────┘  └─────────────────┘  └─────────────────┘              │  │
│  │                                                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                               │  │
│  │                       MÓDULO DE ADMINISTRACIÓN                                │  │
│  │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │  │
│  │   │    Gestionar    │  │      Ver        │  │    Consultar    │              │  │
│  │   │    Usuarios     │  │    Auditoría    │  │    Reportes     │              │  │
│  │   │     (UC-16)     │  │     (UC-17)     │  │     (UC-18)     │              │  │
│  │   └─────────────────┘  └─────────────────┘  └─────────────────┘              │  │
│  │                                                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Casos de Uso por Módulo

### 3.1 Módulo de Autenticación

```
                                    ┌─────────────────────────────────────┐
                                    │      MÓDULO DE AUTENTICACIÓN        │
                                    │                                     │
    ┌─────────┐                     │   ┌───────────────────────────┐    │
    │  ┌───┐  │                     │   │                           │    │
    │  │ ☺ │  │                     │   │      UC-01: Registrarse   │    │
    │  └─┬─┘  │─────────────────────┼──>│                           │    │
    │   /│\   │                     │   │  El usuario crea una      │    │
    │   / \   │                     │   │  cuenta en el sistema     │    │
    └─────────┘                     │   │                           │    │
     Cualquier                      │   └───────────────────────────┘    │
      Usuario                       │                                     │
                                    │   ┌───────────────────────────┐    │
    ┌─────────┐                     │   │                           │    │
    │  ┌───┐  │                     │   │   UC-02: Iniciar Sesión   │    │
    │  │ ☺ │  │─────────────────────┼──>│                           │    │
    │  └─┬─┘  │                     │   │  El usuario accede con    │    │
    │   /│\   │                     │   │  sus credenciales         │    │
    │   / \   │                     │   │                           │    │
    └─────────┘                     │   └─────────────┬─────────────┘    │
     Usuario                        │                 │                   │
    Registrado                      │                 │ <<include>>       │
                                    │                 ▼                   │
    ┌─────────┐                     │   ┌───────────────────────────┐    │
    │  ┌───┐  │                     │   │                           │    │
    │  │ ☺ │  │                     │   │   UC-02a: Validar JWT     │    │
    │  └─┬─┘  │─────────────────────┼──>│                           │    │
    │   /│\   │                     │   │  Sistema genera y valida  │    │
    │   / \   │                     │   │  tokens de acceso         │    │
    └─────────┘                     │   │                           │    │
     Usuario                        │   └───────────────────────────┘    │
    Autenticado                     │                                     │
         │                          │   ┌───────────────────────────┐    │
         │                          │   │                           │    │
         └──────────────────────────┼──>│   UC-03: Cerrar Sesión    │    │
                                    │   │                           │    │
                                    │   │  El usuario invalida su   │    │
                                    │   │  token y cierra sesión    │    │
                                    │   │                           │    │
                                    │   └───────────────────────────┘    │
                                    │                                     │
                                    └─────────────────────────────────────┘
```

### 3.2 Módulo de Análisis de Campaña

```
                                    ┌─────────────────────────────────────────────────┐
                                    │        MÓDULO DE ANÁLISIS DE CAMPAÑA            │
                                    │                                                 │
    ┌─────────┐                     │   ┌───────────────────────────┐                │
    │  ┌───┐  │                     │   │                           │                │
    │  │ ☺ │  │                     │   │  UC-04: Analizar          │                │
    │  └─┬─┘  │─────────────────────┼──>│         Sentimiento       │                │
    │   /│\   │                     │   │                           │                │
    │   / \   │                     │   │  Analiza tweets sobre     │                │
    └─────────┘                     │   │  un tema/candidato        │                │
    Analista de                     │   │                           │                │
     Campaña                        │   └─────────────┬─────────────┘                │
         │                          │                 │                               │
         │                          │                 │ <<include>>                   │
         │                          │                 ▼                               │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │  UC-04a: Buscar Tweets    │                │
         │                          │   │         (Twitter API)     │                │
         │                          │   └─────────────┬─────────────┘                │
         │                          │                 │                               │
         │                          │                 │ <<include>>                   │
         │                          │                 ▼                               │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │  UC-04b: Clasificar       │◄───┐           │
         │                          │   │  Sentimiento (BETO)       │    │           │
         │                          │   └───────────────────────────┘    │           │
         │                          │                                     │           │
         │                          │   ┌───────────────────────────┐    │           │
         │                          │   │                           │    │           │
         ├──────────────────────────┼──>│  UC-05: Consultar         │────┘           │
         │                          │   │  Trending Topics          │                │
         │                          │   │                           │                │
         │                          │   │  Ver temas tendencia      │                │
         │                          │   │  en Twitter Colombia      │                │
         │                          │   └───────────────────────────┘                │
         │                          │                                                 │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │                           │                │
         ├──────────────────────────┼──>│  UC-06: Generar           │                │
         │                          │   │         Estrategia        │                │
         │                          │   │                           │                │
         │                          │   │  Genera plan estratégico  │                │
         │                          │   │  basado en análisis       │                │
         │                          │   └─────────────┬─────────────┘                │
         │                          │                 │                               │
         │                          │                 │ <<include>>                   │
         │                          │                 ▼                               │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │  UC-06a: Generar con      │                │
         │                          │   │  GPT-4o (OpenAI)          │                │
         │                          │   └───────────────────────────┘                │
         │                          │                 ▲                               │
         │                          │                 │ <<include>>                   │
         │                          │                 │                               │
         │                          │   ┌─────────────┴─────────────┐                │
         │                          │   │                           │                │
         ├──────────────────────────┼──>│  UC-07: Generar Discurso  │                │
         │                          │   │                           │                │
         │                          │   │  Genera discurso          │                │
         │                          │   │  personalizado            │                │
         │                          │   └───────────────────────────┘                │
         │                          │                                                 │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │                           │                │
         ├──────────────────────────┼──>│  UC-08: Chatear con       │                │
         │                          │   │         Asistente IA      │                │
         │                          │   │                           │                │
         │                          │   │  Consultas en lenguaje    │                │
         │                          │   │  natural con RAG          │                │
         │                          │   └─────────────┬─────────────┘                │
         │                          │                 │                               │
         │                          │                 │ <<include>>                   │
         │                          │                 ▼                               │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │  UC-08a: Búsqueda         │                │
         │                          │   │  Semántica (ChromaDB)     │                │
         │                          │   └───────────────────────────┘                │
         │                          │                                                 │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │                           │                │
         └──────────────────────────┼──>│  UC-09: Ver Pronósticos   │                │
                                    │   │                           │                │
                                    │   │  Visualiza métricas       │                │
                                    │   │  ICCE, ISN, momentum      │                │
                                    │   │  y proyecciones           │                │
                                    │   └─────────────┬─────────────┘                │
                                    │                 │                               │
                                    │                 │ <<include>>                   │
                                    │                 ▼                               │
                                    │   ┌───────────────────────────┐                │
                                    │   │  UC-09a: Calcular         │                │
                                    │   │  Holt-Winters             │                │
                                    │   └───────────────────────────┘                │
                                    │                                                 │
                                    └─────────────────────────────────────────────────┘
```

### 3.3 Módulo Electoral (E-14)

```
                                    ┌─────────────────────────────────────────────────┐
                                    │           MÓDULO ELECTORAL (E-14)               │
                                    │                                                 │
    ┌─────────┐                     │   ┌───────────────────────────┐                │
    │  ┌───┐  │                     │   │                           │                │
    │  │ ☺ │  │                     │   │  UC-10: Subir Formulario  │                │
    │  └─┬─┘  │─────────────────────┼──>│                           │                │
    │   /│\   │                     │   │  Observador sube PDF o    │                │
    │   / \   │                     │   │  imagen del formulario    │                │
    └─────────┘                     │   │  E-14 desde campo         │                │
    Observador                      │   └─────────────┬─────────────┘                │
    Electoral                       │                 │                               │
         │                          │                 │ <<include>>                   │
         │                          │                 ▼                               │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │                           │                │
         │                          │   │  UC-11: Procesar OCR      │                │
         │                          │   │                           │                │
         │                          │   │  Sistema extrae datos     │                │
         │                          │   │  con Claude Vision        │                │
         │                          │   └─────────────┬─────────────┘                │
         │                          │                 │                               │
         │                          │                 │ <<include>>                   │
         │                          │                 ▼                               │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │                           │                │
         │                          │   │  UC-12: Validar           │                │
         │                          │   │         Formulario        │                │
         │                          │   │                           │                │
         │                          │   │  Validación aritmética    │                │
         │                          │   │  automática               │                │
         │                          │   └─────────────┬─────────────┘                │
         │                          │                 │                               │
         │                          │                 │ <<extend>>                    │
         │                          │                 ▼ [si hay discrepancias]        │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │                           │                │
         │                          │   │  UC-12a: Crear Alerta     │                │
         │                          │   │                           │                │
         │                          │   │  Sistema genera alerta    │                │
         │                          │   │  automática               │                │
         │                          │   └───────────────────────────┘                │
         │                          │                                                 │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │                           │                │
         └──────────────────────────┼──>│  UC-15: Ver Resultados    │                │
                                    │   │                           │                │
                                    │   │  Consulta estado de       │                │
                                    │   │  formularios y votos      │                │
                                    │   └───────────────────────────┘                │
                                    │                                                 │
    ┌─────────┐                     │   ┌───────────────────────────┐                │
    │  ┌───┐  │                     │   │                           │                │
    │  │ ☺ │  │─────────────────────┼──>│  UC-13: Revisar           │                │
    │  └─┬─┘  │                     │   │         Manualmente       │                │
    │   /│\   │                     │   │                           │                │
    │   / \   │                     │   │  Admin revisa y aprueba   │                │
    └─────────┘                     │   │  formularios con errores  │                │
   Administrador                    │   └─────────────┬─────────────┘                │
         │                          │                 │                               │
         │                          │                 │ <<include>>                   │
         │                          │                 ▼                               │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │                           │                │
         │                          │   │  UC-13a: Registrar        │                │
         │                          │   │  en Audit Log             │                │
         │                          │   │                           │                │
         │                          │   │  Log inmutable de         │                │
         │                          │   │  todas las acciones       │                │
         │                          │   └───────────────────────────┘                │
         │                          │                                                 │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │                           │                │
         └──────────────────────────┼──>│  UC-14: Gestionar Alertas │                │
                                    │   │                           │                │
                                    │   │  Ver, reconocer y         │                │
                                    │   │  resolver alertas         │                │
                                    │   └───────────────────────────┘                │
                                    │                                                 │
                                    └─────────────────────────────────────────────────┘
```

### 3.4 Módulo de Administración

```
                                    ┌─────────────────────────────────────────────────┐
                                    │         MÓDULO DE ADMINISTRACIÓN                │
                                    │                                                 │
    ┌─────────┐                     │   ┌───────────────────────────┐                │
    │  ┌───┐  │                     │   │                           │                │
    │  │ ☺ │  │                     │   │  UC-16: Gestionar         │                │
    │  └─┬─┘  │─────────────────────┼──>│         Usuarios          │                │
    │   /│\   │                     │   │                           │                │
    │   / \   │                     │   │  CRUD de usuarios y       │                │
    └─────────┘                     │   │  asignación de roles      │                │
   Administrador                    │   └─────────────┬─────────────┘                │
         │                          │                 │                               │
         │                          │       ┌─────────┼─────────┐                    │
         │                          │       │         │         │                    │
         │                          │       ▼         ▼         ▼                    │
         │                          │   ┌───────┐ ┌───────┐ ┌───────┐               │
         │                          │   │UC-16a │ │UC-16b │ │UC-16c │               │
         │                          │   │Crear  │ │Editar │ │Desact.│               │
         │                          │   │Usuario│ │Usuario│ │Usuario│               │
         │                          │   └───────┘ └───────┘ └───────┘               │
         │                          │                                                 │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │                           │                │
         ├──────────────────────────┼──>│  UC-17: Ver Auditoría     │                │
         │                          │   │                           │                │
         │                          │   │  Consulta logs de         │                │
         │                          │   │  todas las acciones       │                │
         │                          │   │  del sistema              │                │
         │                          │   └─────────────┬─────────────┘                │
         │                          │                 │                               │
         │                          │                 │ <<extend>>                    │
         │                          │                 ▼                               │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │  UC-17a: Exportar         │                │
         │                          │   │  Auditoría                │                │
         │                          │   └───────────────────────────┘                │
         │                          │                                                 │
         │                          │   ┌───────────────────────────┐                │
         │                          │   │                           │                │
         └──────────────────────────┼──>│  UC-18: Consultar         │                │
                                    │   │         Reportes          │                │
                                    │   │                           │                │
                                    │   │  Dashboard con métricas   │                │
                                    │   │  de uso del sistema       │                │
                                    │   └─────────────┬─────────────┘                │
                                    │                 │                               │
                                    │       ┌─────────┼─────────┐                    │
                                    │       │         │         │                    │
                                    │       ▼         ▼         ▼                    │
                                    │   ┌───────┐ ┌───────┐ ┌───────┐               │
                                    │   │UC-18a │ │UC-18b │ │UC-18c │               │
                                    │   │Reporte│ │Reporte│ │Reporte│               │
                                    │   │Análisis│ │E-14   │ │Usuarios│              │
                                    │   └───────┘ └───────┘ └───────┘               │
                                    │                                                 │
                                    └─────────────────────────────────────────────────┘
```

---

## 4. Matriz Actor - Caso de Uso

| Caso de Uso | Analista | Observador | Admin | Invitado | Sistema |
|-------------|:--------:|:----------:|:-----:|:--------:|:-------:|
| **Autenticación** |
| UC-01: Registrarse | ✓ | ✓ | ✓ | ✓ | |
| UC-02: Iniciar Sesión | ✓ | ✓ | ✓ | | |
| UC-03: Cerrar Sesión | ✓ | ✓ | ✓ | | |
| **Análisis de Campaña** |
| UC-04: Analizar Sentimiento | ✓ | | ✓ | | |
| UC-05: Consultar Trending | ✓ | | ✓ | ✓ | |
| UC-06: Generar Estrategia | ✓ | | ✓ | | |
| UC-07: Generar Discurso | ✓ | | ✓ | | |
| UC-08: Chat con IA | ✓ | | ✓ | | |
| UC-09: Ver Pronósticos | ✓ | | ✓ | | |
| **Módulo Electoral** |
| UC-10: Subir Formulario | | ✓ | ✓ | | |
| UC-11: Procesar OCR | | | | | ✓ |
| UC-12: Validar Formulario | | | | | ✓ |
| UC-13: Revisar Manualmente | | | ✓ | | |
| UC-14: Gestionar Alertas | | | ✓ | | |
| UC-15: Ver Resultados | ✓ | ✓ | ✓ | | |
| **Administración** |
| UC-16: Gestionar Usuarios | | | ✓ | | |
| UC-17: Ver Auditoría | | | ✓ | | |
| UC-18: Consultar Reportes | | | ✓ | | |

---

## 5. Especificación de Casos de Uso Principales

### UC-04: Analizar Sentimiento

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ CASO DE USO: UC-04 - Analizar Sentimiento                                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Actor Principal: Analista de Campaña                                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Precondiciones:                                                                     │
│ - Usuario autenticado con rol 'analyst' o 'admin'                                   │
│ - Conexión a Twitter API disponible                                                 │
│ - Límite diario de requests no excedido (3/día Free Tier)                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Flujo Principal:                                                                    │
│ 1. Usuario selecciona ubicación (ej: Colombia, Bogotá)                             │
│ 2. Usuario selecciona tema PND (ej: Educación, Salud)                              │
│ 3. Usuario ingresa nombre del candidato                                             │
│ 4. Sistema busca tweets relevantes via Twitter API                                  │
│ 5. Sistema analiza sentimiento con modelo BETO                                      │
│ 6. Sistema clasifica tweets por eje PND                                             │
│ 7. Sistema genera resumen ejecutivo con GPT-4o                                      │
│ 8. Sistema muestra resultados con gráficos                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Flujos Alternativos:                                                                │
│ 4a. No hay tweets disponibles:                                                      │
│     - Sistema muestra mensaje "Sin datos suficientes"                               │
│ 5a. Error en API de Twitter:                                                        │
│     - Sistema usa caché si disponible (TTL 24h)                                     │
│     - Sistema notifica al usuario del error                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Postcondiciones:                                                                    │
│ - Análisis guardado en base de datos                                                │
│ - Tweets indexados en ChromaDB para RAG                                             │
│ - Métricas actualizadas                                                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Casos de Uso Incluidos:                                                             │
│ - UC-04a: Buscar Tweets (Twitter API)                                               │
│ - UC-04b: Clasificar Sentimiento (BETO)                                             │
│ - UC-06a: Generar con GPT-4o                                                        │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### UC-10: Subir Formulario E-14

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ CASO DE USO: UC-10 - Subir Formulario E-14                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Actor Principal: Observador Electoral                                               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Precondiciones:                                                                     │
│ - Usuario autenticado con rol 'observer' o 'admin'                                  │
│ - Archivo en formato PDF, PNG o JPG                                                 │
│ - Tamaño máximo: 10 MB                                                              │
│ - Máximo 20 páginas por documento                                                   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Flujo Principal:                                                                    │
│ 1. Observador selecciona departamento                                               │
│ 2. Observador selecciona municipio                                                  │
│ 3. Observador selecciona puesto de votación                                         │
│ 4. Observador selecciona número de mesa                                             │
│ 5. Observador selecciona tipo de formulario (E-14, E-24, E-26)                     │
│ 6. Observador carga archivo (drag & drop o selección)                               │
│ 7. Sistema valida formato y tamaño                                                  │
│ 8. Sistema inicia procesamiento OCR (UC-11)                                         │
│ 9. Sistema muestra confirmación con ID de seguimiento                               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Flujos Alternativos:                                                                │
│ 7a. Archivo inválido:                                                               │
│     - Sistema muestra error específico                                              │
│     - Usuario corrige y reintenta                                                   │
│ 7b. Formulario duplicado (mismo hash):                                              │
│     - Sistema alerta sobre duplicado                                                │
│     - Usuario confirma o cancela                                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Postcondiciones:                                                                    │
│ - Formulario almacenado con estado 'PENDING'                                        │
│ - Proceso OCR encolado                                                              │
│ - Registro en audit_log                                                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Casos de Uso Incluidos:                                                             │
│ - UC-11: Procesar OCR de Formulario                                                 │
│ - UC-12: Validar Formulario                                                         │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### UC-13: Revisar Manualmente (HITL)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ CASO DE USO: UC-13 - Revisar Manualmente (Human-in-the-Loop)                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Actor Principal: Administrador                                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Precondiciones:                                                                     │
│ - Usuario autenticado con rol 'admin'                                               │
│ - Formulario en estado 'NEEDS_REVIEW'                                               │
│ - Existen discrepancias o baja confianza OCR                                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Flujo Principal:                                                                    │
│ 1. Admin accede a cola de revisión                                                  │
│ 2. Sistema muestra lista priorizada por severidad                                   │
│ 3. Admin selecciona formulario a revisar                                            │
│ 4. Sistema muestra imagen original + datos extraídos                                │
│ 5. Sistema resalta campos con discrepancias                                         │
│ 6. Admin compara visualmente y corrige valores                                      │
│ 7. Admin agrega notas de revisión                                                   │
│ 8. Admin aprueba o rechaza formulario                                               │
│ 9. Sistema actualiza estado y registra en audit_log                                 │
│ 10. Sistema resuelve alertas asociadas                                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Flujos Alternativos:                                                                │
│ 8a. Admin rechaza formulario:                                                       │
│     - Sistema marca como 'FAILED'                                                   │
│     - Sistema notifica al observador para resubir                                   │
│ 6a. Admin no puede determinar valor correcto:                                       │
│     - Admin escala a otro administrador                                             │
│     - Sistema registra escalamiento                                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Postcondiciones:                                                                    │
│ - Formulario en estado 'VALIDATED' o 'FAILED'                                       │
│ - Correcciones guardadas con trazabilidad                                           │
│ - Audit log actualizado (inmutable)                                                 │
│ - Alertas resueltas                                                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Casos de Uso Incluidos:                                                             │
│ - UC-13a: Registrar en Audit Log                                                    │
│ - UC-14: Gestionar Alertas                                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### UC-08: Chatear con Asistente IA (RAG)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ CASO DE USO: UC-08 - Chatear con Asistente IA                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Actor Principal: Analista de Campaña                                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Precondiciones:                                                                     │
│ - Usuario autenticado                                                               │
│ - Existen documentos indexados en ChromaDB                                          │
│ - API de OpenAI disponible                                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Flujo Principal:                                                                    │
│ 1. Usuario abre interfaz de chat                                                    │
│ 2. Sistema carga historial de conversación (si existe)                              │
│ 3. Usuario escribe pregunta en lenguaje natural                                     │
│ 4. Sistema genera embedding de la pregunta                                          │
│ 5. Sistema busca documentos relevantes en ChromaDB                                  │
│ 6. Sistema construye contexto con documentos + historial                            │
│ 7. Sistema genera respuesta con GPT-4o                                              │
│ 8. Sistema muestra respuesta con fuentes citadas                                    │
│ 9. Sistema guarda intercambio en historial                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Flujos Alternativos:                                                                │
│ 5a. No hay documentos relevantes:                                                   │
│     - Sistema responde con conocimiento general                                     │
│     - Sistema indica que no hay datos específicos                                   │
│ 7a. Error en OpenAI API:                                                            │
│     - Sistema reintenta con backoff exponencial                                     │
│     - Sistema muestra error amigable si falla                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Postcondiciones:                                                                    │
│ - Conversación guardada en chat_history                                             │
│ - Tokens utilizados registrados                                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Casos de Uso Incluidos:                                                             │
│ - UC-08a: Búsqueda Semántica (ChromaDB)                                             │
│ - UC-06a: Generar con GPT-4o                                                        │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Diagrama de Relaciones entre Casos de Uso

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     RELACIONES ENTRE CASOS DE USO                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                 <<include>>
    ┌──────────────┐ ─────────────────────────────────> ┌──────────────┐
    │   UC-02      │                                    │   UC-02a     │
    │Iniciar Sesión│                                    │ Validar JWT  │
    └──────────────┘                                    └──────────────┘


                                 <<include>>
    ┌──────────────┐ ─────────────────────────────────> ┌──────────────┐
    │   UC-04      │                                    │   UC-04a     │
    │  Analizar    │                                    │Buscar Tweets │
    │ Sentimiento  │ ─────────────────────────────────> ├──────────────┤
    └──────────────┘            <<include>>             │   UC-04b     │
                                                        │Clasificar    │
                                                        │ Sentimiento  │
                                                        └──────────────┘


    ┌──────────────┐            <<include>>             ┌──────────────┐
    │   UC-06      │ ─────────────────────────────────> │   UC-06a     │
    │  Generar     │                                    │ Generar con  │
    │ Estrategia   │                                    │   GPT-4o     │
    └──────────────┘                                    └──────┬───────┘
                                                               ▲
    ┌──────────────┐            <<include>>                    │
    │   UC-07      │ ──────────────────────────────────────────┘
    │  Generar     │
    │  Discurso    │
    └──────────────┘


    ┌──────────────┐            <<include>>             ┌──────────────┐
    │   UC-08      │ ─────────────────────────────────> │   UC-08a     │
    │  Chat IA     │                                    │  Búsqueda    │
    │    RAG       │                                    │  Semántica   │
    └──────────────┘                                    └──────────────┘


    ┌──────────────┐            <<include>>             ┌──────────────┐
    │   UC-10      │ ─────────────────────────────────> │   UC-11      │
    │   Subir      │                                    │ Procesar OCR │
    │ Formulario   │                                    └──────┬───────┘
    └──────────────┘                                           │
                                                               │ <<include>>
                                                               ▼
                                                        ┌──────────────┐
                                                        │   UC-12      │
                                                        │  Validar     │
                                                        │ Formulario   │
                                                        └──────┬───────┘
                                                               │
                                                               │ <<extend>>
                                                               │ [discrepancias]
                                                               ▼
                                                        ┌──────────────┐
                                                        │   UC-12a     │
                                                        │ Crear Alerta │
                                                        └──────────────┘


    ┌──────────────┐            <<include>>             ┌──────────────┐
    │   UC-13      │ ─────────────────────────────────> │   UC-13a     │
    │  Revisar     │                                    │ Registrar    │
    │ Manualmente  │                                    │  Audit Log   │
    └──────────────┘                                    └──────────────┘


    ┌──────────────┐            <<extend>>              ┌──────────────┐
    │   UC-17      │ ─────────────────────────────────> │   UC-17a     │
    │    Ver       │                                    │  Exportar    │
    │  Auditoría   │                                    │  Auditoría   │
    └──────────────┘                                    └──────────────┘
```

---

## 7. Resumen de Casos de Uso

| ID | Nombre | Actor Principal | Prioridad | Complejidad |
|----|--------|-----------------|-----------|-------------|
| UC-01 | Registrarse | Usuario | Alta | Baja |
| UC-02 | Iniciar Sesión | Usuario | Alta | Baja |
| UC-03 | Cerrar Sesión | Usuario | Alta | Baja |
| UC-04 | Analizar Sentimiento | Analista | Alta | Alta |
| UC-05 | Consultar Trending | Analista | Media | Baja |
| UC-06 | Generar Estrategia | Analista | Alta | Alta |
| UC-07 | Generar Discurso | Analista | Media | Alta |
| UC-08 | Chat con IA (RAG) | Analista | Alta | Alta |
| UC-09 | Ver Pronósticos | Analista | Media | Media |
| UC-10 | Subir Formulario | Observador | Alta | Media |
| UC-11 | Procesar OCR | Sistema | Alta | Alta |
| UC-12 | Validar Formulario | Sistema | Alta | Media |
| UC-13 | Revisar Manualmente | Admin | Alta | Media |
| UC-14 | Gestionar Alertas | Admin | Alta | Baja |
| UC-15 | Ver Resultados | Todos | Media | Baja |
| UC-16 | Gestionar Usuarios | Admin | Media | Baja |
| UC-17 | Ver Auditoría | Admin | Media | Baja |
| UC-18 | Consultar Reportes | Admin | Baja | Media |

============================================================
  DESCARGADOR MASIVO DE ACTAS E14
  ~103,000 PDFs - Registraduria de Colombia
============================================================

ARCHIVOS INCLUIDOS:
-------------------
1. selenium_extractor.py    - Extrae tokens navegando el sitio
2. descargar_desde_tokens.py - Descarga PDFs con los tokens
3. descargador_masivo.py    - Version con servicio de CAPTCHA
4. instalar_y_ejecutar.sh   - Script de instalacion

============================================================
ESTRATEGIA PARA SUPERAR EL CAPTCHA
============================================================

El sitio tiene CAPTCHA que aparece al consultar un puesto.
Hay 3 estrategias:

ESTRATEGIA 1: MANUAL (Recomendada para empezar)
-----------------------------------------------
- Resuelves el CAPTCHA UNA VEZ en el navegador
- El script guarda la sesion
- Navega automaticamente por la estructura
- Si expira, resuelves de nuevo

Ventajas: Gratis, funciona seguro
Desventajas: Necesitas estar presente ocasionalmente


ESTRATEGIA 2: SERVICIO DE CAPTCHA (Para automatizacion total)
-------------------------------------------------------------
Usa servicios como 2Captcha o Anti-Captcha:

- 2Captcha: ~$2.99 por 1000 CAPTCHAs
  https://2captcha.com

- Anti-Captcha: ~$2.00 por 1000 CAPTCHAs
  https://anti-captcha.com

Para 103,000 PDFs, si el CAPTCHA aparece cada ~50 puestos:
- ~2000 CAPTCHAs necesarios
- Costo estimado: $4-6 USD


ESTRATEGIA 3: SESION PERSISTENTE
--------------------------------
- El CAPTCHA no aparece en CADA consulta
- Una vez resuelto, la sesion puede durar horas
- El script guarda cookies para reutilizar

============================================================
GUIA PASO A PASO
============================================================

PASO 1: INSTALAR DEPENDENCIAS
-----------------------------
Abre terminal en esta carpeta y ejecuta:

    chmod +x instalar_y_ejecutar.sh
    ./instalar_y_ejecutar.sh

O manualmente:

    pip install requests beautifulsoup4 selenium


PASO 2: INSTALAR CHROMEDRIVER
-----------------------------
El script de Selenium necesita ChromeDriver.

Mac (con Homebrew):
    brew install --cask chromedriver

    # Si da error de seguridad:
    xattr -d com.apple.quarantine /usr/local/bin/chromedriver

Windows:
    Descarga de https://chromedriver.chromium.org/downloads
    Extrae en C:\Windows\ o agrega al PATH

Linux:
    sudo apt install chromium-chromedriver


PASO 3: EXTRAER TOKENS
----------------------
    python3 selenium_extractor.py

El script:
1. Abre Chrome automaticamente
2. Navega al sitio de la Registraduria
3. Te pide que selecciones ubicacion y resuelvas CAPTCHA
4. Una vez resuelto, navega automaticamente
5. Extrae tokens de TODAS las mesas
6. Guarda en tokens_extraidos.json

MODOS DISPONIBLES:
- Modo 1: Automatico completo (recorre todo)
- Modo 2: Manual rapido (tu navegas, el extrae)
- Modo 3: Continuar sesion previa


PASO 4: DESCARGAR PDFs
----------------------
    python3 descargar_desde_tokens.py

El script:
1. Lee los tokens de tokens_extraidos.json
2. Descarga PDFs en paralelo (configurable)
3. Guarda progreso para poder resumir
4. Organiza por Departamento/Municipio/Puesto/


============================================================
ESTIMACIONES
============================================================

TOKENS A EXTRAER:
- 32 departamentos
- ~1100 municipios
- ~11,000 puestos de votacion
- ~103,000 mesas

TIEMPO DE EXTRACCION:
- Modo automatico: ~4-8 horas
- Depende de cuantos CAPTCHAs aparezcan

TIEMPO DE DESCARGA:
- 10 descargas paralelas: ~3 horas
- 20 descargas paralelas: ~1.5 horas
- 50 descargas paralelas: ~40 minutos
  (puede causar bloqueo del servidor)

ESPACIO EN DISCO:
- ~500 KB por PDF (promedio)
- 103,000 * 500 KB = ~50 GB

============================================================
SOLUCION DE PROBLEMAS
============================================================

ERROR: "chromedriver not found"
SOLUCION: Instalar ChromeDriver (ver PASO 2)

ERROR: "session expired" o "CAPTCHA detectado"
SOLUCION: El script pausara y te pedira resolver.
          Resuelve en el navegador y presiona Enter.

ERROR: "connection refused" o timeouts
SOLUCION: El servidor puede estar sobrecargado.
          Reduce el numero de workers paralelos.
          Espera unos minutos e intenta de nuevo.

ERROR: "Permission denied" en Mac para chromedriver
SOLUCION: xattr -d com.apple.quarantine /usr/local/bin/chromedriver

DESCARGAS INCOMPLETAS:
- El progreso se guarda automaticamente
- Ejecuta de nuevo el script de descarga
- Continuara donde se quedo

============================================================
CONFIGURACION AVANZADA
============================================================

USAR SERVICIO DE CAPTCHA (2Captcha):
------------------------------------
1. Registrate en https://2captcha.com
2. Obtiene tu API key
3. Edita descargador_masivo.py:

   config = {
       'captcha_servicio': '2captcha',
       'captcha_api_key': 'TU_API_KEY_AQUI'
   }


AJUSTAR VELOCIDAD:
------------------
En descargar_desde_tokens.py:

- workers: numero de descargas paralelas (default 10)
- delay: pausa entre grupos de descargas

Mas workers = mas rapido pero mas riesgo de bloqueo


CAMBIAR DIRECTORIO DE SALIDA:
-----------------------------
En descargar_desde_tokens.py, cuando te pregunte,
especifica el directorio deseado.

============================================================
ESTRUCTURA DE ARCHIVOS GENERADOS
============================================================

actas_e14_masivo/
├── tokens_extraidos.json    # Todos los tokens
├── tokens_python.py         # Tokens en formato Python
├── cookies_selenium.pkl     # Sesion guardada
├── cookies_requests.json    # Cookies para requests
├── descargados.json         # Progreso de descargas
├── fallidos.json            # Descargas fallidas
├── extraccion.log          # Log de extraccion
├── descarga_pdfs.log       # Log de descargas
│
└── actas_e14/              # PDFs descargados
    ├── AMAZONAS/
    │   ├── LETICIA/
    │   │   ├── PUESTO_001/
    │   │   │   ├── Mesa_001.pdf
    │   │   │   ├── Mesa_002.pdf
    │   │   │   └── ...
    │   │   └── ...
    │   └── ...
    ├── ANTIOQUIA/
    │   └── ...
    └── ...

============================================================
SOPORTE
============================================================

Si tienes problemas:
1. Revisa los archivos .log para errores
2. Verifica que el sitio este funcionando manualmente
3. Asegurate de tener Chrome actualizado

============================================================

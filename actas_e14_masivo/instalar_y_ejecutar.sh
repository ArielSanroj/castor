#!/bin/bash
# ============================================================
# INSTALADOR Y EJECUTOR - ACTAS E14
# ============================================================

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     INSTALADOR - DESCARGADOR MASIVO ACTAS E14              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 no esta instalado"
    echo "        Instala desde: https://www.python.org/downloads/"
    exit 1
fi

echo "[OK] Python 3 encontrado: $(python3 --version)"

# Crear entorno virtual (opcional pero recomendado)
echo ""
echo "[*] Creando entorno virtual..."
python3 -m venv venv 2>/dev/null

# Activar entorno virtual
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "[OK] Entorno virtual activado"
fi

# Instalar dependencias
echo ""
echo "[*] Instalando dependencias..."
pip install --upgrade pip
pip install requests beautifulsoup4 selenium

echo ""
echo "[OK] Dependencias instaladas"

# Verificar/Instalar ChromeDriver
echo ""
echo "[*] Verificando ChromeDriver..."

if command -v chromedriver &> /dev/null; then
    echo "[OK] ChromeDriver encontrado: $(chromedriver --version)"
else
    echo "[!] ChromeDriver no encontrado"
    echo ""
    echo "    Para instalar ChromeDriver:"
    echo ""
    echo "    Mac (con Homebrew):"
    echo "      brew install --cask chromedriver"
    echo "      xattr -d com.apple.quarantine /usr/local/bin/chromedriver"
    echo ""
    echo "    O descarga manualmente desde:"
    echo "      https://chromedriver.chromium.org/downloads"
    echo ""
fi

echo ""
echo "============================================================"
echo "  INSTALACION COMPLETADA"
echo "============================================================"
echo ""
echo "  PASOS PARA DESCARGAR LAS ACTAS:"
echo ""
echo "  1. Extraer tokens (requiere resolver CAPTCHA una vez):"
echo "     python3 selenium_extractor.py"
echo ""
echo "  2. Descargar PDFs con los tokens extraidos:"
echo "     python3 descargar_desde_tokens.py"
echo ""
echo "============================================================"

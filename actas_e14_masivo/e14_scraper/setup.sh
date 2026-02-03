#!/bin/bash
# ==============================================
# E-14 Scraper - Script de instalación
# ==============================================

set -e

echo "🗳️  E-14 Scraper - Instalación"
echo "================================"

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python $PYTHON_VERSION detectado"

# Crear entorno virtual
echo ""
echo "📦 Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
echo ""
echo "📥 Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

# Instalar Playwright browsers
echo ""
echo "🌐 Instalando navegadores para Playwright..."
playwright install chromium

# Copiar archivo de configuración
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creando archivo de configuración..."
    cp .env.example .env
    echo "⚠️  Recuerda editar .env con tus credenciales"
fi

# Verificar Docker (opcional)
echo ""
if command -v docker &> /dev/null; then
    echo "✅ Docker detectado"
    echo ""
    read -p "¿Deseas iniciar PostgreSQL con Docker? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose up -d postgres
        echo "✅ PostgreSQL iniciado en localhost:5432"
        echo "   Usuario: postgres"
        echo "   Password: postgres"
        echo "   Base de datos: e14_scraper"
    fi
else
    echo "⚠️  Docker no detectado. Asegúrate de tener PostgreSQL disponible."
fi

# Crear directorios necesarios
echo ""
echo "📁 Creando directorios..."
mkdir -p output
mkdir -p logs

echo ""
echo "================================"
echo "✅ Instalación completada!"
echo ""
echo "Próximos pasos:"
echo "  1. Edita .env con tus credenciales"
echo "  2. Ejecuta: source venv/bin/activate"
echo "  3. Ejecuta: python main.py init"
echo "  4. Ejecuta: python main.py run"
echo ""
echo "Para ver el estado: python main.py status"
echo "Para exportar:      python main.py export"

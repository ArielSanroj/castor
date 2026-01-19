#!/bin/bash

# Script simple para levantar el backend
# Uso: ./start_backend.sh

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Iniciando CASTOR ELECCIONES Backend${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Verificar .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Advertencia: No se encontró .env${NC}"
    echo -e "  Asegúrate de tener TWITTER_BEARER_TOKEN y OPENAI_API_KEY configurados"
fi

# Verificar que estamos en el directorio correcto
if [ ! -d "backend" ]; then
    echo -e "${YELLOW}✗ Error: Ejecuta este script desde la raíz del proyecto${NC}"
    exit 1
fi

# Matar proceso anterior si existe
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}Terminando proceso anterior en puerto 5001...${NC}"
    lsof -ti:5001 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Cambiar al directorio backend y ejecutar
cd backend
echo -e "${GREEN}✓ Iniciando backend en http://localhost:5001${NC}\n"
python3 main.py

#!/bin/bash

# Script de smoke test para verificar que el backend responde con datos reales de X/Twitter
# Este script:
# 1. Verifica que exista .env con las variables necesarias
# 2. Levanta el backend en background
# 3. Espera a que esté listo
# 4. Ejecuta los tests
# 5. Muestra los resultados

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
BACKEND_DIR="backend"
ENV_FILE=".env"
BASE_URL="http://localhost:5001"
MAX_WAIT=30  # Segundos máximos para esperar que el backend esté listo

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SMOKE TEST - CASTOR ELECCIONES${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 1. Verificar que existe .env
echo -e "${YELLOW}[1/5] Verificando archivo .env...${NC}"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}✗ Error: No se encontró el archivo .env${NC}"
    echo -e "${YELLOW}  Crea un archivo .env en la raíz del proyecto con:${NC}"
    echo -e "  TWITTER_BEARER_TOKEN=tu_token_aqui"
    echo -e "  OPENAI_API_KEY=tu_key_aqui"
    exit 1
fi
echo -e "${GREEN}✓ Archivo .env encontrado${NC}"

# 2. Verificar variables de entorno requeridas
echo -e "\n${YELLOW}[2/5] Verificando variables de entorno...${NC}"
source "$ENV_FILE"

if [ -z "$TWITTER_BEARER_TOKEN" ]; then
    echo -e "${RED}✗ Error: TWITTER_BEARER_TOKEN no está definido en .env${NC}"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}✗ Error: OPENAI_API_KEY no está definido en .env${NC}"
    exit 1
fi

echo -e "${GREEN}✓ TWITTER_BEARER_TOKEN configurado${NC}"
echo -e "${GREEN}✓ OPENAI_API_KEY configurado${NC}"

# 3. Verificar que estamos en el directorio correcto
if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}✗ Error: No se encontró el directorio backend/${NC}"
    exit 1
fi

# 4. Levantar el backend en background
echo -e "\n${YELLOW}[3/5] Levantando el backend...${NC}"
cd "$BACKEND_DIR"

# Matar cualquier proceso que esté usando el puerto 5001
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}  Puerto 5001 ya está en uso, terminando proceso anterior...${NC}"
    lsof -ti:5001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Levantar el backend
echo -e "${BLUE}  Ejecutando: python3 main.py${NC}"
python3 main.py > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

echo -e "${GREEN}✓ Backend iniciado (PID: $BACKEND_PID)${NC}"

# 5. Esperar a que el backend esté listo
echo -e "\n${YELLOW}[4/5] Esperando a que el backend esté listo...${NC}"
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -s "$BASE_URL/api/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend está listo!${NC}"
        break
    fi
    echo -n "."
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
    echo -e "\n${RED}✗ Error: El backend no respondió después de $MAX_WAIT segundos${NC}"
    echo -e "${YELLOW}  Revisa los logs en backend.log${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# 6. Ejecutar los tests
echo -e "\n${YELLOW}[5/5] Ejecutando smoke tests...${NC}"
echo -e "${BLUE}  Esto hará llamadas reales a X/Twitter y OpenAI${NC}\n"

# Ejecutar test_endpoints.py
if python3 test_endpoints.py --base-url "$BASE_URL" --media-only; then
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✓ SMOKE TEST COMPLETADO${NC}"
    echo -e "${GREEN}========================================${NC}"
    TEST_RESULT=0
else
    echo -e "\n${RED}========================================${NC}"
    echo -e "${RED}  ✗ SMOKE TEST FALLÓ${NC}"
    echo -e "${RED}========================================${NC}"
    TEST_RESULT=1
fi

# Limpiar: terminar el backend
echo -e "\n${YELLOW}Terminando el backend...${NC}"
kill $BACKEND_PID 2>/dev/null || true
wait $BACKEND_PID 2>/dev/null || true

# Mostrar logs si hubo error
if [ $TEST_RESULT -ne 0 ]; then
    echo -e "\n${YELLOW}Últimas líneas del log del backend:${NC}"
    tail -20 backend.log 2>/dev/null || true
fi

exit $TEST_RESULT

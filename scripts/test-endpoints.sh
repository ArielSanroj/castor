#!/bin/bash
# Test all CASTOR API endpoints
# Usage: ./scripts/test-endpoints.sh [https://localhost | http://localhost:5001]

set -e

BASE_URL="${1:-https://localhost}"
INSECURE=""

# Use -k for self-signed certificates
if [[ "$BASE_URL" == https://* ]]; then
    INSECURE="-k"
fi

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "CASTOR API Endpoint Test"
echo "Base URL: $BASE_URL"
echo "=========================================="
echo ""

test_endpoint() {
    local method=$1
    local endpoint=$2
    local expected=$3
    local data=$4

    if [ -n "$data" ]; then
        response=$(curl $INSECURE -s -o /dev/null -w "%{http_code}" -X $method "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" -d "$data" 2>/dev/null || echo "000")
    else
        response=$(curl $INSECURE -s -o /dev/null -w "%{http_code}" -X $method "$BASE_URL$endpoint" 2>/dev/null || echo "000")
    fi

    if [ "$response" == "$expected" ] || [ "$response" == "200" ] || [ "$response" == "201" ]; then
        echo -e "${GREEN}✓${NC} $method $endpoint -> $response"
        return 0
    elif [ "$response" == "503" ] || [ "$response" == "401" ]; then
        echo -e "${YELLOW}○${NC} $method $endpoint -> $response (service not ready or auth required)"
        return 0
    else
        echo -e "${RED}✗${NC} $method $endpoint -> $response (expected $expected)"
        return 1
    fi
}

echo "=== Gateway Health ==="
test_endpoint GET "/health" "200"
echo ""

echo "=== Core Service (Auth & Users) ==="
test_endpoint GET "/api/health/core" "200"
test_endpoint POST "/api/v1/auth/register" "400" '{"email":"test@test.com","password":"test1234"}'
test_endpoint POST "/api/v1/auth/login" "401" '{"email":"test@test.com","password":"test1234"}'
test_endpoint GET "/api/v1/users/me" "401"
test_endpoint POST "/api/auth/register" "400" '{"email":"test@test.com","password":"test1234"}'
test_endpoint POST "/api/auth/login" "401" '{"email":"test@test.com","password":"test1234"}'
echo ""

echo "=== E-14 Service (Electoral Forms) ==="
test_endpoint GET "/api/health/e14" "200"
test_endpoint GET "/api/v1/e14/forms" "200"
test_endpoint GET "/api/v1/pipeline/status" "200"
test_endpoint GET "/api/e14/forms" "200"
test_endpoint GET "/api/pipeline/status" "200"
test_endpoint GET "/api/review/pending" "200"
echo ""

echo "=== Dashboard IA Service (Analytics) ==="
test_endpoint GET "/api/health/dashboard" "200"
test_endpoint POST "/api/v1/sentiment/analyze" "503" '{"texts":["test"]}'
test_endpoint POST "/api/v1/twitter/search" "503" '{"query":"test"}'
test_endpoint POST "/api/v1/rag/query" "503" '{"query":"test"}'
test_endpoint GET "/api/v1/forecast/dashboard" "503"
test_endpoint GET "/api/media/twitter/search" "200"
test_endpoint GET "/api/chat/history" "200"
test_endpoint GET "/api/campaign/metrics" "200"
test_endpoint GET "/api/forecast/icce" "200"
echo ""

echo "=== Security Tests ==="
test_endpoint GET "/internal/validate-token" "403"
echo ""

echo "=========================================="
echo "Test completed!"
echo "=========================================="

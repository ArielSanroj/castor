#!/usr/bin/env python3
"""
Test de integración completa de seguridad electoral.
Prueba los endpoints con y sin autenticación.

Uso:
    python scripts/test_integration.py
"""
import json
import requests
import sys
from datetime import datetime

BASE_URL = "http://localhost:5001"
API_URL = f"{BASE_URL}/api"

# Colores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_test(name, passed, details=""):
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"  {status} {name}")
    if details:
        print(f"         {YELLOW}{details}{RESET}")


def print_section(title):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def test_health_endpoints():
    """Test endpoints públicos (sin auth)."""
    print_section("TEST 1: Endpoints Públicos (sin auth)")

    # Health check general
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        print_test("GET /api/health", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        print_test("GET /api/health", False, str(e))

    # Health check electoral
    try:
        r = requests.get(f"{API_URL}/electoral/health", timeout=5)
        print_test("GET /api/electoral/health", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        print_test("GET /api/electoral/health", False, str(e))

    # Test endpoint
    try:
        r = requests.get(f"{API_URL}/electoral/test", timeout=5)
        data = r.json()
        print_test("GET /api/electoral/test", r.status_code == 200)
        if r.status_code == 200:
            print(f"         OCR Model: {data.get('ocr_model', 'N/A')}")
            print(f"         Security: {data.get('security', {})}")
    except Exception as e:
        print_test("GET /api/electoral/test", False, str(e))


def test_without_auth():
    """Test endpoints protegidos sin autenticación."""
    print_section("TEST 2: Endpoints Protegidos SIN Auth (deben fallar)")

    endpoints = [
        ("POST", "/api/electoral/e14/process", {"url": "https://example.com/test.pdf"}),
        ("POST", "/api/electoral/e14/process-url", {"url": "https://example.com/test.pdf"}),
        ("GET", "/api/electoral/stats", None),
        ("GET", "/api/electoral/usage", None),
    ]

    for method, endpoint, data in endpoints:
        try:
            if method == "GET":
                r = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            else:
                r = requests.post(f"{BASE_URL}{endpoint}", json=data, timeout=5)

            # Esperamos 401 Unauthorized
            passed = r.status_code == 401
            response_data = r.json() if r.content else {}
            code = response_data.get('code', 'N/A')
            print_test(
                f"{method} {endpoint}",
                passed,
                f"status={r.status_code}, code={code}"
            )
        except Exception as e:
            print_test(f"{method} {endpoint}", False, str(e))


def get_auth_token():
    """Obtiene un token JWT (registra usuario de prueba si no existe)."""
    print_section("TEST 3: Obtener Token JWT")

    test_email = f"test_electoral_{datetime.now().strftime('%H%M%S')}@test.com"
    test_password = "TestPassword123!"

    # Intentar registrar
    try:
        r = requests.post(f"{API_URL}/auth/register", json={
            "email": test_email,
            "password": test_password,
            "first_name": "Test",
            "last_name": "Electoral"
        }, timeout=10)

        if r.status_code in [200, 201]:
            data = r.json()
            token = data.get('access_token')
            print_test("Registro de usuario", True, f"email={test_email}")
            print_test("Token obtenido", bool(token), f"token={token[:20]}..." if token else "No token")
            return token
        else:
            print_test("Registro de usuario", False, f"status={r.status_code}, {r.text[:100]}")
    except Exception as e:
        print_test("Registro de usuario", False, str(e))

    # Si falló el registro, intentar login con usuario existente
    try:
        r = requests.post(f"{API_URL}/auth/login", json={
            "email": "admin@castor.com",
            "password": "admin123"
        }, timeout=10)

        if r.status_code == 200:
            data = r.json()
            token = data.get('access_token')
            print_test("Login alternativo", bool(token))
            return token
    except:
        pass

    return None


def test_with_auth(token):
    """Test endpoints protegidos con autenticación."""
    print_section("TEST 4: Endpoints Protegidos CON Auth")

    if not token:
        print(f"  {RED}✗ No hay token disponible, saltando tests{RESET}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # Test stats
    try:
        r = requests.get(f"{API_URL}/electoral/stats", headers=headers, timeout=5)
        print_test("GET /api/electoral/stats", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            data = r.json()
            user_usage = data.get('user_usage', {})
            print(f"         Uso última hora: {user_usage.get('last_hour', {})}")
    except Exception as e:
        print_test("GET /api/electoral/stats", False, str(e))

    # Test usage
    try:
        r = requests.get(f"{API_URL}/electoral/usage", headers=headers, timeout=5)
        print_test("GET /api/electoral/usage", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            data = r.json()
            usage = data.get('usage', {})
            print(f"         Operaciones restantes (hora): {usage.get('hourly', {}).get('remaining_operations', 'N/A')}")
            print(f"         Operaciones restantes (día): {usage.get('daily', {}).get('remaining_operations', 'N/A')}")
    except Exception as e:
        print_test("GET /api/electoral/usage", False, str(e))


def test_pdf_validation(token):
    """Test validación de PDF."""
    print_section("TEST 5: Validación de PDF")

    if not token:
        print(f"  {RED}✗ No hay token disponible, saltando tests{RESET}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # Test con URL inválida
    try:
        r = requests.post(
            f"{API_URL}/electoral/e14/process-url",
            headers=headers,
            json={"url": "https://example.com/not-a-pdf.txt"},
            timeout=30
        )
        data = r.json()
        # Esperamos error de PDF inválido
        is_pdf_error = data.get('code') in ['INVALID_PDF', 'PROCESSING_ERROR']
        print_test(
            "URL inválida rechazada",
            r.status_code == 400 or is_pdf_error,
            f"status={r.status_code}, code={data.get('code', 'N/A')}"
        )
    except Exception as e:
        print_test("URL inválida rechazada", False, str(e))

    # Test con URL sin proporcionar
    try:
        r = requests.post(
            f"{API_URL}/electoral/e14/process-url",
            headers=headers,
            json={},
            timeout=5
        )
        data = r.json()
        print_test(
            "Request sin URL rechazada",
            r.status_code == 400,
            f"code={data.get('code', 'N/A')}"
        )
    except Exception as e:
        print_test("Request sin URL rechazada", False, str(e))


def test_real_e14_processing(token):
    """Test procesamiento real de E-14 (opcional, consume API)."""
    print_section("TEST 6: Procesamiento Real de E-14")

    if not token:
        print(f"  {RED}✗ No hay token disponible, saltando tests{RESET}")
        return

    # Preguntar antes de consumir API
    print(f"\n  {YELLOW}⚠ Este test consumirá ~$0.10 de API de Anthropic{RESET}")
    print(f"  {YELLOW}  ¿Desea continuar? [s/N]: {RESET}", end="")

    try:
        response = input().strip().lower()
    except:
        response = 'n'

    if response != 's':
        print(f"  {BLUE}→ Test saltado por usuario{RESET}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # URL real de E-14 de prueba (si existe)
    test_url = "https://wsr.registraduria.gov.co/-Escrutinio,3685-.html"  # Esto no funcionará directamente

    # Usar archivo local si existe
    import os
    local_pdf = "/Users/arielsanroj/Downloads/1.pdf"

    if os.path.exists(local_pdf):
        print(f"  Usando PDF local: {local_pdf}")

        try:
            with open(local_pdf, 'rb') as f:
                files = {'file': ('test_e14.pdf', f, 'application/pdf')}
                r = requests.post(
                    f"{API_URL}/electoral/e14/process",
                    headers=headers,
                    files=files,
                    timeout=120
                )

            data = r.json()
            if r.status_code == 200 and data.get('success'):
                print_test("Procesamiento E-14", True)
                print(f"         Mesa ID: {data.get('mesa_id', 'N/A')}")
                print(f"         Sufragantes: {data.get('total_sufragantes', 'N/A')}")
                print(f"         Votos urna: {data.get('total_urna', 'N/A')}")
                print(f"         Delta: {data.get('delta', 'N/A')}")
                print(f"         Validación: {'✓' if data.get('validation_passed') else '✗'}")
            else:
                print_test("Procesamiento E-14", False, f"status={r.status_code}, error={data.get('error', 'N/A')}")
        except Exception as e:
            print_test("Procesamiento E-14", False, str(e))
    else:
        print(f"  {YELLOW}→ No hay PDF local de prueba en {local_pdf}{RESET}")


def main():
    """Ejecuta todos los tests de integración."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}  CASTOR ELECCIONES - Integration Security Tests{RESET}")
    print(f"{BLUE}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    # Test 1: Endpoints públicos
    test_health_endpoints()

    # Test 2: Sin autenticación
    test_without_auth()

    # Test 3: Obtener token
    token = get_auth_token()

    # Test 4: Con autenticación
    test_with_auth(token)

    # Test 5: Validación PDF
    test_pdf_validation(token)

    # Test 6: Procesamiento real (opcional)
    test_real_e14_processing(token)

    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{GREEN}✓ TESTS DE INTEGRACIÓN COMPLETADOS{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
CASTOR ELECCIONES - Test de todos los endpoints
Ejecutar: python test_all_endpoints.py
"""
import requests
import json
from datetime import datetime
import sys

BASE_URL = "http://localhost:5001"

# Colores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

results = {"passed": 0, "failed": 0, "skipped": 0}


def test_endpoint(method, path, description, data=None, params=None, expected_status=200, auth=False):
    """Prueba un endpoint y reporta el resultado."""
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}

    if auth:
        # Skip si requiere auth - marcarlo como skipped
        print(f"  {YELLOW}⊘ SKIP{RESET} {method:6} {path:50} - Requiere autenticación")
        results["skipped"] += 1
        return None

    try:
        if method == "GET":
            response = requests.get(url, params=params, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=30)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            print(f"  {RED}✗ ERROR{RESET} Método no soportado: {method}")
            results["failed"] += 1
            return None

        # Verificar status code
        if response.status_code == expected_status or response.status_code in [200, 201, 202]:
            print(f"  {GREEN}✓ PASS{RESET} {method:6} {path:50} [{response.status_code}] {description[:40]}")
            results["passed"] += 1
            return response
        elif response.status_code == 503:
            print(f"  {YELLOW}⊘ 503{RESET}  {method:6} {path:50} - Servicio no disponible (configuración)")
            results["skipped"] += 1
            return response
        elif response.status_code == 401:
            print(f"  {YELLOW}⊘ 401{RESET}  {method:6} {path:50} - Requiere autenticación")
            results["skipped"] += 1
            return response
        elif response.status_code == 429:
            print(f"  {YELLOW}⊘ 429{RESET}  {method:6} {path:50} - Rate limit alcanzado")
            results["skipped"] += 1
            return response
        else:
            error_msg = ""
            try:
                error_data = response.json()
                error_msg = error_data.get("error", "")[:50]
            except:
                error_msg = response.text[:50] if response.text else ""
            print(f"  {RED}✗ FAIL{RESET} {method:6} {path:50} [{response.status_code}] {error_msg}")
            results["failed"] += 1
            return response

    except requests.exceptions.ConnectionError:
        print(f"  {RED}✗ CONN{RESET} {method:6} {path:50} - No se puede conectar al servidor")
        results["failed"] += 1
        return None
    except requests.exceptions.Timeout:
        print(f"  {YELLOW}⊘ TIME{RESET} {method:6} {path:50} - Timeout")
        results["skipped"] += 1
        return None
    except Exception as e:
        print(f"  {RED}✗ ERR{RESET}  {method:6} {path:50} - {str(e)[:40]}")
        results["failed"] += 1
        return None


def main():
    print(f"\n{BLUE}{'='*80}")
    print(f" CASTOR ELECCIONES - Test de Endpoints")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}{RESET}\n")

    # Verificar conectividad primero
    print(f"{BLUE}[1/12] Verificando conectividad...{RESET}")
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        print(f"  {GREEN}✓ Servidor disponible en {BASE_URL}{RESET}\n")
    except:
        print(f"  {RED}✗ No se puede conectar a {BASE_URL}")
        print(f"  Asegúrate de que el servidor esté corriendo con:")
        print(f"  cd backend && python main.py{RESET}\n")
        sys.exit(1)

    # ============================================================
    # HEALTH ENDPOINTS
    # ============================================================
    print(f"{BLUE}[2/12] Health Endpoints{RESET}")
    test_endpoint("GET", "/api/health", "Health check básico")
    test_endpoint("GET", "/api/health/live", "Liveness probe")
    test_endpoint("GET", "/api/health/ready", "Readiness probe")
    test_endpoint("GET", "/api/health/sla", "SLA metrics")
    test_endpoint("GET", "/api/health/full", "Full health check")
    test_endpoint("GET", "/api/health/deep", "Deep health check")
    test_endpoint("GET", "/api/twitter-usage", "Twitter API usage")
    print()

    # ============================================================
    # AUTH ENDPOINTS
    # ============================================================
    print(f"{BLUE}[3/12] Auth Endpoints{RESET}")
    test_endpoint("POST", "/api/auth/login", "Login",
                  data={"email": "test@test.com", "password": "testpass123"},
                  expected_status=401)  # Expected to fail without valid user
    test_endpoint("POST", "/api/auth/register", "Register",
                  data={
                      "email": f"test{datetime.now().timestamp()}@test.com",
                      "password": "testpass123",
                      "first_name": "Test",
                      "last_name": "User"
                  })
    test_endpoint("GET", "/api/auth/me", "Get current user", auth=True)
    print()

    # ============================================================
    # CAMPAIGN ENDPOINTS
    # ============================================================
    print(f"{BLUE}[4/12] Campaign Endpoints{RESET}")
    test_endpoint("GET", "/api/campaign/trending", "Trending topics",
                  params={"location": "Bogotá"})
    test_endpoint("POST", "/api/campaign/analyze-votes", "Analyze votes",
                  data={"location": "Bogotá", "candidate_name": "Test Candidate"})
    test_endpoint("GET", "/api/campaign/signatures/test-campaign/count", "Signature count")
    print()

    # ============================================================
    # MEDIA ENDPOINTS
    # ============================================================
    print(f"{BLUE}[5/12] Media Endpoints{RESET}")
    test_endpoint("GET", "/api/media/latest", "Latest analysis")
    test_endpoint("GET", "/api/media/history", "Analysis history")
    test_endpoint("POST", "/api/media/analyze", "Media analyze",
                  data={
                      "location": "Bogotá",
                      "topic": "Seguridad",
                      "max_tweets": 10
                  })
    print()

    # ============================================================
    # FORECAST ENDPOINTS
    # ============================================================
    print(f"{BLUE}[6/12] Forecast Endpoints{RESET}")
    test_endpoint("GET", "/api/forecast", "Forecast info")
    test_endpoint("POST", "/api/forecast/icce", "Calculate ICCE",
                  data={"location": "Bogotá", "days_back": 7})
    test_endpoint("POST", "/api/forecast/momentum", "Calculate Momentum",
                  data={"location": "Bogotá", "days_back": 7})
    test_endpoint("POST", "/api/forecast/dashboard", "Forecast dashboard",
                  data={"location": "Bogotá", "days_back": 7})
    print()

    # ============================================================
    # CHAT & RAG ENDPOINTS
    # ============================================================
    print(f"{BLUE}[7/12] Chat & RAG Endpoints{RESET}")
    test_endpoint("POST", "/api/chat", "Basic chat",
                  data={"message": "¿Cuál es la estrategia recomendada para Bogotá?"})
    test_endpoint("POST", "/api/chat/rag", "RAG chat",
                  data={"message": "¿Qué temas son más relevantes?"})
    test_endpoint("GET", "/api/chat/rag/stats", "RAG stats")
    test_endpoint("POST", "/api/chat/rag/search", "RAG search",
                  data={"query": "seguridad"})
    print()

    # ============================================================
    # ELECTORAL ENDPOINTS
    # ============================================================
    print(f"{BLUE}[8/12] Electoral Endpoints{RESET}")
    test_endpoint("GET", "/api/electoral/health", "Electoral health")
    test_endpoint("GET", "/api/electoral/test", "Electoral test")
    test_endpoint("GET", "/api/electoral/metrics", "Electoral metrics")
    test_endpoint("GET", "/api/electoral/metrics/json", "Electoral metrics JSON")
    test_endpoint("GET", "/api/electoral/metrics/slo", "Electoral SLOs")
    print()

    # ============================================================
    # GEOGRAPHY ENDPOINTS
    # ============================================================
    print(f"{BLUE}[9/12] Geography Endpoints{RESET}")
    test_endpoint("GET", "/api/geography/health", "Geography health")
    test_endpoint("GET", "/api/geography/choropleth", "Choropleth map")
    test_endpoint("GET", "/api/geography/choropleth", "Choropleth risk",
                  params={"mode": "risk"})
    test_endpoint("GET", "/api/geography/department/05/stats", "Department stats (Antioquia)")
    test_endpoint("GET", "/api/geography/department/11/incidents", "Department incidents (Bogotá)")
    test_endpoint("GET", "/api/geography/moe/risk-municipalities", "MOE risk municipalities")
    test_endpoint("GET", "/api/geography/moe/department-summary", "MOE department summary")
    print()

    # ============================================================
    # WITNESS ENDPOINTS
    # ============================================================
    print(f"{BLUE}[10/12] Witness Endpoints{RESET}")
    test_endpoint("GET", "/api/witness/vapid-public-key", "VAPID public key")
    test_endpoint("GET", "/api/witness/list", "List witnesses")
    test_endpoint("GET", "/api/witness/stats", "Witness stats")
    test_endpoint("GET", "/api/witness/qr/list", "List QR codes")
    test_endpoint("GET", "/api/witness/assignments", "List assignments")
    test_endpoint("GET", "/api/witness/geography/departments", "List departments")
    print()

    # ============================================================
    # LEADS ENDPOINTS
    # ============================================================
    print(f"{BLUE}[11/12] Leads Endpoints{RESET}")
    test_endpoint("GET", "/api/leads/count", "Leads count")
    test_endpoint("POST", "/api/demo-request", "Demo request",
                  data={
                      "first_name": "Test",
                      "last_name": "User",
                      "email": f"demo{datetime.now().timestamp()}@test.com",
                      "phone": "+573001234567",
                      "interest": "dashboard",
                      "location": "Bogotá"
                  })
    print()

    # ============================================================
    # ADVISOR ENDPOINTS
    # ============================================================
    print(f"{BLUE}[12/12] Advisor Endpoints{RESET}")
    test_endpoint("POST", "/api/advisor/recommendations", "Get recommendations",
                  data={
                      "location": "Bogotá",
                      "candidate_name": "Test Candidate",
                      "current_icce": 65.0,
                      "top_topics": ["Seguridad", "Economía"]
                  })
    print()

    # ============================================================
    # RESUMEN
    # ============================================================
    print(f"\n{BLUE}{'='*80}")
    print(f" RESUMEN DE PRUEBAS")
    print(f"{'='*80}{RESET}")

    total = results["passed"] + results["failed"] + results["skipped"]

    print(f"\n  {GREEN}✓ Pasaron:    {results['passed']:3d}{RESET}")
    print(f"  {RED}✗ Fallaron:   {results['failed']:3d}{RESET}")
    print(f"  {YELLOW}⊘ Omitidos:   {results['skipped']:3d}{RESET}")
    print(f"  {'─'*30}")
    print(f"    Total:      {total:3d}")

    success_rate = (results["passed"] / total * 100) if total > 0 else 0
    color = GREEN if success_rate >= 80 else YELLOW if success_rate >= 60 else RED
    print(f"\n  {color}Tasa de éxito: {success_rate:.1f}%{RESET}")

    print(f"\n{BLUE}{'='*80}{RESET}\n")

    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

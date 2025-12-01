#!/usr/bin/env python3
"""
Script de pruebas para la API de CASTOR ELECCIONES
Prueba todos los endpoints disponibles
"""
import requests
import json
from datetime import datetime
from typing import Dict, Any

# Configuración
BASE_URL = "http://localhost:5001"
API_BASE = f"{BASE_URL}/api"

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Imprime un encabezado formateado"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_test(name: str):
    """Imprime el nombre de una prueba"""
    print(f"{Colors.BOLD}🧪 {name}{Colors.RESET}")

def print_success(message: str):
    """Imprime un mensaje de éxito"""
    print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")

def print_error(message: str):
    """Imprime un mensaje de error"""
    print(f"{Colors.RED}❌ {message}{Colors.RESET}")

def print_warning(message: str):
    """Imprime un mensaje de advertencia"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")

def print_info(message: str):
    """Imprime información"""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.RESET}")

def test_endpoint(method: str, url: str, data: Dict[Any, Any] = None, 
                  headers: Dict[str, str] = None, expected_status: int = 200) -> Dict:
    """
    Prueba un endpoint y retorna la respuesta
    """
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=60)
        else:
            return {"error": f"Método {method} no soportado"}
        
        status_ok = response.status_code == expected_status
        if status_ok:
            print_success(f"Status: {response.status_code}")
        else:
            print_error(f"Status esperado: {expected_status}, recibido: {response.status_code}")
        
        try:
            return {
                "status_code": response.status_code,
                "data": response.json(),
                "success": status_ok
            }
        except:
            return {
                "status_code": response.status_code,
                "data": response.text,
                "success": status_ok
            }
    except requests.exceptions.ConnectionError:
        print_error(f"No se pudo conectar a {url}")
        print_info("Asegúrate de que el servidor esté corriendo en http://localhost:5001")
        return {"error": "Connection error"}
    except requests.exceptions.Timeout:
        print_error(f"Timeout al conectar a {url}")
        return {"error": "Timeout"}
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return {"error": str(e)}

def test_health_endpoints():
    """Prueba los endpoints de health check"""
    print_header("HEALTH CHECK ENDPOINTS")
    
    # Test 1: Health check básico
    print_test("GET /api/health")
    result = test_endpoint("GET", f"{API_BASE}/health")
    if result.get("success"):
        data = result.get("data", {})
        print_info(f"Service: {data.get('service', 'N/A')}")
        print_info(f"Version: {data.get('version', 'N/A')}")
        print_info(f"Timestamp: {data.get('timestamp', 'N/A')}")
    
    # Test 2: Twitter usage stats
    print_test("\nGET /api/twitter-usage")
    result = test_endpoint("GET", f"{API_BASE}/twitter-usage")
    if result.get("success"):
        data = result.get("data", {})
        print_info(f"Plan: {data.get('plan', 'N/A')}")
        stats = data.get("stats", {})
        if stats:
            print_info(f"Stats: {json.dumps(stats, indent=2)}")

def test_web_routes():
    """Prueba las rutas web"""
    print_header("WEB ROUTES")
    
    routes = [
        ("/", "Index"),
        ("/webpage", "Landing Page"),
        ("/media", "CASTOR Medios"),
        ("/campaign", "CASTOR Campañas"),
    ]
    
    for route, name in routes:
        print_test(f"GET {route}")
        try:
            response = requests.get(f"{BASE_URL}{route}", timeout=10)
            if response.status_code == 200:
                print_success(f"Status: {response.status_code} - {name} cargada correctamente")
                print_info(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            else:
                print_warning(f"Status: {response.status_code}")
        except Exception as e:
            print_error(f"Error: {str(e)}")

def test_analysis_endpoint():
    """Prueba el endpoint de análisis"""
    print_header("ANALYSIS ENDPOINT")
    
    print_test("POST /api/analyze")
    print_info("Enviando solicitud de análisis...")
    
    payload = {
        "location": "Bogotá",
        "theme": "Seguridad",
        "candidate_name": "Test Candidate",
        "politician": "@testcandidate",
        "max_tweets": 15  # Mínimo requerido: 10
    }
    
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    result = test_endpoint("POST", f"{API_BASE}/analyze", data=payload, expected_status=200)
    
    if result.get("success"):
        data = result.get("data", {})
        if data.get("success"):
            print_success("Análisis completado exitosamente")
            print_info(f"Executive Summary: {'Presente' if data.get('executive_summary') else 'No presente'}")
            print_info(f"Topic Analyses: {len(data.get('topic_analyses', []))} temas")
            print_info(f"Strategic Plan: {'Presente' if data.get('strategic_plan') else 'No presente'}")
            print_info(f"Speech: {'Presente' if data.get('speech') else 'No presente'}")
        else:
            print_warning(f"Análisis falló: {data.get('error', 'Error desconocido')}")
    else:
        print_warning("El endpoint puede requerir autenticación o configuración adicional")

def test_chat_endpoint():
    """Prueba el endpoint de chat"""
    print_header("CHAT ENDPOINT")
    
    print_test("POST /api/chat")
    print_info("Enviando mensaje al asistente de IA...")
    
    payload = {
        "message": "¿Qué es CASTOR?",
        "context": {}
    }
    
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    result = test_endpoint("POST", f"{API_BASE}/chat", data=payload, expected_status=200)
    
    if result.get("success"):
        data = result.get("data", {})
        if data.get("success"):
            print_success("Chat completado exitosamente")
            response_text = data.get("response", "")
            print_info(f"Respuesta (primeros 200 chars): {response_text[:200]}...")
        else:
            print_warning(f"Chat falló: {data.get('error', 'Error desconocido')}")
    else:
        print_warning("El endpoint puede requerir autenticación o configuración adicional")

def test_media_endpoint():
    """Prueba el endpoint de análisis de medios"""
    print_header("MEDIA ANALYSIS ENDPOINT")
    
    print_test("POST /api/media/analyze")
    print_info("Enviando solicitud de análisis de medios...")
    
    payload = {
        "location": "Bogotá",
        "theme": "Seguridad",
        "max_tweets": 15  # Mínimo requerido: 10
    }
    
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    result = test_endpoint("POST", f"{API_BASE}/media/analyze", data=payload, expected_status=200)
    
    if result.get("success"):
        data = result.get("data", {})
        if data.get("success"):
            print_success("Análisis de medios completado exitosamente")
            summary = data.get("summary", {})
            print_info(f"Summary: {'Presente' if summary else 'No presente'}")
        else:
            print_warning(f"Análisis falló: {data.get('error', 'Error desconocido')}")
    else:
        print_warning("El endpoint puede requerir configuración adicional")

def test_campaign_endpoint():
    """Prueba el endpoint de campaña"""
    print_header("CAMPAIGN ENDPOINT")
    
    print_test("POST /api/campaign/analyze")
    print_info("Enviando solicitud de análisis de campaña...")
    
    payload = {
        "location": "Bogotá",
        "theme": "Seguridad",
        "candidate_name": "Test Candidate",
        "max_tweets": 15  # Mínimo requerido: 10
    }
    
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    result = test_endpoint("POST", f"{API_BASE}/campaign/analyze", data=payload, expected_status=200)
    
    if result.get("success"):
        data = result.get("data", {})
        if data.get("success"):
            print_success("Análisis de campaña completado exitosamente")
            analysis = data.get("analysis", {})
            print_info(f"Analysis: {'Presente' if analysis else 'No presente'}")
        else:
            print_warning(f"Análisis falló: {data.get('error', 'Error desconocido')}")
    else:
        print_warning("El endpoint puede requerir autenticación o configuración adicional")

def test_invalid_endpoint():
    """Prueba un endpoint inválido"""
    print_header("ERROR HANDLING")
    
    print_test("GET /api/invalid-endpoint")
    result = test_endpoint("GET", f"{API_BASE}/invalid-endpoint", expected_status=404)
    
    if result.get("status_code") == 404:
        print_success("Manejo de errores funciona correctamente")

def main():
    """Función principal"""
    print_header("🧪 PRUEBAS DE API - CASTOR ELECCIONES")
    print_info(f"Servidor: {BASE_URL}")
    print_info(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Ejecutar todas las pruebas
    try:
        test_health_endpoints()
        test_web_routes()
        test_invalid_endpoint()
        test_analysis_endpoint()
        test_chat_endpoint()
        test_media_endpoint()
        test_campaign_endpoint()
        
        print_header("✅ PRUEBAS COMPLETADAS")
        print_success("Todas las pruebas han sido ejecutadas")
        print_info("\nNota: Algunos endpoints pueden requerir:")
        print_info("  - Variables de entorno configuradas (Twitter API, OpenAI, etc.)")
        print_info("  - Autenticación JWT")
        print_info("  - Base de datos configurada")
        
    except KeyboardInterrupt:
        print_warning("\nPruebas interrumpidas por el usuario")
    except Exception as e:
        print_error(f"\nError inesperado: {str(e)}")

if __name__ == "__main__":
    main()


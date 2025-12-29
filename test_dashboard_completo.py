#!/usr/bin/env python3
"""
Test completo del dashboard - Verifica todos los componentes
"""
import requests
import json
import sys

BASE_URL = "http://localhost:5001"

def test_dashboard_page():
    """Test que la página del dashboard carga."""
    print("\n" + "="*70)
    print("TEST 1: Dashboard Page")
    print("="*70)
    
    try:
        response = requests.get(f"{BASE_URL}/dashboard", timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            if "analytics_dashboard" in content.lower() or "dashboard" in content.lower():
                print("✅ Dashboard page carga correctamente")
                print(f"   Tamaño: {len(content)} bytes")
                return True
            else:
                print("❌ Contenido del dashboard no encontrado")
                return False
        else:
            print(f"❌ Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_apis():
    """Test de las APIs del dashboard."""
    print("\n" + "="*70)
    print("TEST 2: APIs del Dashboard")
    print("="*70)
    
    results = []
    
    # Test Media API
    print("\n📰 Media API:")
    try:
        response = requests.post(
            f"{BASE_URL}/api/media/analyze",
            json={"location": "Colombia", "max_tweets": 5, "time_window_days": 7, "language": "es"},
            timeout=30
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Media API funciona")
            results.append(True)
        elif response.status_code == 503:
            data = response.json()
            print(f"   ⚠️  Media API: {data.get('error', 'Servicio no disponible')}")
            results.append(False)
        else:
            print(f"   ❌ Media API: Error {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results.append(False)
    
    # Test Forecast API
    print("\n📈 Forecast API:")
    try:
        response = requests.post(
            f"{BASE_URL}/api/forecast/dashboard",
            json={"location": "Colombia", "days_back": 7, "forecast_days": 7},
            timeout=30
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Forecast API funciona")
            results.append(True)
        elif response.status_code == 503:
            data = response.json()
            print(f"   ⚠️  Forecast API: {data.get('error', 'Servicio no disponible')}")
            results.append(False)
        else:
            print(f"   ❌ Forecast API: Error {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results.append(False)
    
    # Test Trending API
    print("\n🔥 Trending API:")
    try:
        response = requests.get(
            f"{BASE_URL}/api/campaign/trending?location=Colombia&limit=3",
            timeout=15
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Trending API funciona")
            print(f"   Topics: {len(data.get('trending_topics', []))}")
            results.append(True)
        else:
            print(f"   ❌ Trending API: Error {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results.append(False)
    
    return results

def test_health():
    """Test health check."""
    print("\n" + "="*70)
    print("TEST 3: Health Check")
    print("="*70)
    
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check: {data.get('status', 'unknown')}")
            print(f"   Servicios:")
            checks = data.get('checks', {})
            print(f"   - Twitter: {checks.get('circuit_breakers', {}).get('twitter', {}).get('state', 'unknown')}")
            print(f"   - OpenAI: {checks.get('circuit_breakers', {}).get('openai', {}).get('state', 'unknown')}")
            print(f"   - Redis: {checks.get('redis', {}).get('status', 'unknown')}")
            return True
        else:
            print(f"❌ Health check: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("  PRUEBA COMPLETA DEL DASHBOARD")
    print("="*70)
    
    # Test 1: Página
    page_ok = test_dashboard_page()
    
    # Test 2: Health
    health_ok = test_health()
    
    # Test 3: APIs
    api_results = test_apis()
    
    # Resumen
    print("\n" + "="*70)
    print("RESUMEN")
    print("="*70)
    print(f"Dashboard Page: {'✅ OK' if page_ok else '❌ FALLO'}")
    print(f"Health Check: {'✅ OK' if health_ok else '❌ FALLO'}")
    print(f"APIs:")
    print(f"  - Media: {'✅ OK' if api_results[0] else '⚠️  Parcial/Fallo'}")
    print(f"  - Forecast: {'✅ OK' if api_results[1] else '⚠️  Parcial/Fallo'}")
    print(f"  - Trending: {'✅ OK' if api_results[2] else '❌ FALLO'}")
    
    print("\n" + "="*70)
    print("CONCLUSIÓN")
    print("="*70)
    
    if page_ok and health_ok:
        print("✅ Dashboard básico funciona")
        if any(api_results):
            print("⚠️  Algunas APIs funcionan parcialmente")
            print("💡 El dashboard debería mostrar datos parciales")
        else:
            print("⚠️  APIs no disponibles - Dashboard mostrará mensajes de 'sin datos'")
            print("💡 Configura TWITTER_BEARER_TOKEN y OPENAI_API_KEY para funcionalidad completa")
    else:
        print("❌ Hay problemas básicos con el servidor")
    
    print("\n🌐 Dashboard URL: http://localhost:5001/dashboard")
    print("="*70 + "\n")
    
    return 0 if (page_ok and health_ok) else 1

if __name__ == "__main__":
    sys.exit(main())



#!/usr/bin/env python3
"""
Script para probar todos los endpoints de la API CASTOR
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5001"

def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def test_endpoint(name, method, url, payload=None, headers=None):
    """Prueba un endpoint y muestra el resultado."""
    print(f"🔍 Probando: {name}")
    print(f"   {method} {url}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=payload, headers=headers, timeout=120)
        else:
            print(f"   ❌ Método {method} no soportado")
            return False
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ Éxito")
                print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                
                # Mostrar resumen según el tipo de respuesta
                if isinstance(data, dict):
                    if "success" in data:
                        print(f"   Success: {data['success']}")
                    if "candidate_name" in data:
                        print(f"   Candidato: {data['candidate_name']}")
                    if "location" in data:
                        print(f"   Ubicación: {data['location']}")
                    if "icce" in data:
                        print(f"   ICCE actual: {data['icce'].get('current_icce', 'N/A')}")
                    if "momentum" in data:
                        print(f"   Momentum: {data['momentum'].get('current_momentum', 'N/A')}")
                    if "summary" in data:
                        print(f"   Summary: {data['summary'].get('overview', '')[:100]}...")
                    if "executive_summary" in data:
                        print(f"   Executive Summary: {data['executive_summary'].get('overview', '')[:100]}...")
                
                return True
            except json.JSONDecodeError:
                print(f"   ⚠️  Respuesta no es JSON válido")
                print(f"   Response text: {response.text[:200]}")
                return False
        else:
            print(f"   ❌ Error HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   ⏱️  Timeout (más de 120 segundos)")
        return False
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Error de conexión - ¿Está el servidor corriendo?")
        return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def main():
    print_section("PRUEBA DE TODOS LOS ENDPOINTS DE CASTOR API")
    
    results = {}
    
    # 1. Health Check
    print_section("1. HEALTH CHECK")
    results["health"] = test_endpoint(
        "Health Check",
        "GET",
        f"{BASE_URL}/api/health"
    )
    
    # 2. Media Analyze
    print_section("2. MEDIA ANALYZE")
    media_payload = {
        "location": "Bogotá",
        "topic": "Seguridad",
        "max_tweets": 10,
        "time_window_days": 7,
        "language": "es"
    }
    results["media"] = test_endpoint(
        "Media Analyze",
        "POST",
        f"{BASE_URL}/api/media/analyze",
        payload=media_payload,
        headers={"Content-Type": "application/json"}
    )
    
    # 3. Campaign Analyze
    print_section("3. CAMPAIGN ANALYZE")
    campaign_payload = {
        "location": "Bogotá",
        "theme": "Seguridad",
        "candidate_name": "Juan Pérez",
        "max_tweets": 50,
        "language": "es"
    }
    results["campaign"] = test_endpoint(
        "Campaign Analyze",
        "POST",
        f"{BASE_URL}/api/campaign/analyze",
        payload=campaign_payload,
        headers={"Content-Type": "application/json"}
    )
    
    # 4. Forecast Dashboard
    print_section("4. FORECAST DASHBOARD")
    forecast_payload = {
        "location": "Bogotá",
        "candidate_name": "Juan Pérez",
        "days_back": 30,
        "forecast_days": 14
    }
    results["forecast_dashboard"] = test_endpoint(
        "Forecast Dashboard",
        "POST",
        f"{BASE_URL}/api/forecast/dashboard",
        payload=forecast_payload,
        headers={"Content-Type": "application/json"}
    )
    
    # 5. Forecast Narrative Metrics
    print_section("5. FORECAST NARRATIVE METRICS")
    narrative_payload = {
        "location": "Bogotá",
        "candidate_name": "Juan Pérez",
        "topic": "Seguridad",
        "days_back": 7
    }
    results["forecast_narrative"] = test_endpoint(
        "Forecast Narrative Metrics",
        "POST",
        f"{BASE_URL}/api/forecast/narrative-metrics",
        payload=narrative_payload,
        headers={"Content-Type": "application/json"}
    )
    
    # 6. Forecast ICCE
    print_section("6. FORECAST ICCE")
    icce_payload = {
        "location": "Bogotá",
        "candidate_name": "Juan Pérez",
        "days_back": 30
    }
    results["forecast_icce"] = test_endpoint(
        "Forecast ICCE",
        "POST",
        f"{BASE_URL}/api/forecast/icce",
        payload=icce_payload,
        headers={"Content-Type": "application/json"}
    )
    
    # 7. Forecast Momentum
    print_section("7. FORECAST MOMENTUM")
    momentum_payload = {
        "location": "Bogotá",
        "candidate_name": "Juan Pérez",
        "days_back": 30
    }
    results["forecast_momentum"] = test_endpoint(
        "Forecast Momentum",
        "POST",
        f"{BASE_URL}/api/forecast/momentum",
        payload=momentum_payload,
        headers={"Content-Type": "application/json"}
    )
    
    # 8. Forecast Forecast (proyección)
    print_section("8. FORECAST FORECAST (PROYECCIÓN)")
    forecast_forecast_payload = {
        "location": "Bogotá",
        "candidate_name": "Juan Pérez",
        "days_back": 30,
        "forecast_days": 14
    }
    results["forecast_forecast"] = test_endpoint(
        "Forecast Forecast",
        "POST",
        f"{BASE_URL}/api/forecast/forecast",
        payload=forecast_forecast_payload,
        headers={"Content-Type": "application/json"}
    )
    
    # Resumen final
    print_section("RESUMEN DE PRUEBAS")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    print(f"Total de endpoints probados: {total}")
    print(f"✅ Exitosos: {passed}")
    print(f"❌ Fallidos: {failed}")
    print()
    
    print("Detalle por endpoint:")
    for endpoint, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {endpoint}")
    
    print("\n" + "="*80)
    
    if failed == 0:
        print("🎉 ¡Todos los endpoints funcionan correctamente!")
    else:
        print(f"⚠️  {failed} endpoint(s) fallaron. Revisa los logs arriba.")

if __name__ == "__main__":
    main()


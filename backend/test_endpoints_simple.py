#!/usr/bin/env python3
"""
Script simplificado para pruebas rápidas de los endpoints.
Muestra solo la información clave de forma visual.
"""
import json
import requests
import sys

def test_endpoint(name: str, url: str, payload: dict):
    """Prueba un endpoint y muestra resultados clave."""
    print(f"\n{'='*80}")
    print(f"  {name}")
    print(f"{'='*80}\n")
    
    print(f"📤 Enviando solicitud a: {url}")
    print(f"📋 Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}\n")
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Respuesta exitosa!\n")
            
            # MEDIOS: Mostrar resumen
            if "summary" in data:
                print("📊 RESUMEN EJECUTIVO:")
                print(f"   {data['summary'].get('overview', 'N/A')[:200]}...")
                if data['summary'].get('key_stats'):
                    print("\n   📈 Estadísticas:")
                    for stat in data['summary']['key_stats'][:3]:
                        print(f"      • {stat}")
                if data['summary'].get('key_findings'):
                    print("\n   🔍 Hallazgos:")
                    for finding in data['summary']['key_findings'][:3]:
                        print(f"      • {finding}")
            
            # CAMPAÑAS: Mostrar resumen ejecutivo
            if "executive_summary" in data:
                print("📊 RESUMEN EJECUTIVO:")
                print(f"   {data['executive_summary'].get('overview', 'N/A')[:200]}...")
                if data['executive_summary'].get('key_findings'):
                    print("\n   🔍 Hallazgos:")
                    for finding in data['executive_summary']['key_findings'][:3]:
                        print(f"      • {finding}")
                if data['executive_summary'].get('recommendations'):
                    print("\n   💡 Recomendaciones:")
                    for rec in data['executive_summary']['recommendations'][:3]:
                        print(f"      • {rec}")
            
            # TEMAS
            topics = data.get("topics") or data.get("topic_analyses", [])
            if topics:
                print(f"\n📑 TEMAS ANALIZADOS ({len(topics)}):")
                for topic in topics[:5]:  # Mostrar solo los primeros 5
                    sentiment = topic.get("sentiment", {})
                    pos = sentiment.get("positive", 0) * 100
                    neg = sentiment.get("negative", 0) * 100
                    neu = sentiment.get("neutral", 0) * 100
                    print(f"   • {topic.get('topic', 'N/A')}: {topic.get('tweet_count', 0)} tweets")
                    print(f"     Sentimiento: {pos:.1f}% positivo, {neg:.1f}% negativo, {neu:.1f}% neutro")
            
            # PLAN ESTRATÉGICO (solo campañas)
            if "strategic_plan" in data and data["strategic_plan"].get("objectives"):
                print(f"\n🎯 PLAN ESTRATÉGICO ({len(data['strategic_plan']['objectives'])} objetivos):")
                for obj in data["strategic_plan"]["objectives"][:3]:
                    print(f"   • {obj.get('name', 'N/A')}")
                    if obj.get("description"):
                        print(f"     {obj['description'][:100]}...")
            
            # DISCURSO (solo campañas)
            if "speech" in data:
                speech = data["speech"]
                print(f"\n🎤 DISCURSO:")
                if speech.get("title"):
                    print(f"   Título: {speech['title']}")
                if speech.get("key_points"):
                    print(f"   Puntos clave: {len(speech['key_points'])}")
                    for point in speech["key_points"][:3]:
                        print(f"      • {point}")
                if speech.get("content"):
                    print(f"   Contenido: {len(speech['content'])} caracteres")
                    print(f"   {speech['content'][:150]}...")
            
            # METADATA
            if "metadata" in data:
                meta = data["metadata"]
                print(f"\n📋 METADATA:")
                print(f"   Ubicación: {meta.get('location', 'N/A')}")
                print(f"   Tweets analizados: {meta.get('tweets_analyzed', 0)}")
                if meta.get("theme"):
                    print(f"   Tema: {meta['theme']}")
                if meta.get("candidate_name"):
                    print(f"   Candidato: {meta['candidate_name']}")
            
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5001"
    
    print("\n" + "="*80)
    print("  PRUEBAS RÁPIDAS - ENDPOINTS CASTOR ELECCIONES")
    print("="*80)
    print(f"\n🔗 Servidor: {base_url}\n")
    
    # Prueba MEDIOS
    test_endpoint(
        "ENDPOINT MEDIOS",
        f"{base_url}/api/media/analyze",
        {
            "location": "Bogotá",
            "topic": "Seguridad",
            "max_tweets": 10,
            "time_window_days": 7,
            "language": "es"
        }
    )
    
    # Prueba CAMPAÑAS
    test_endpoint(
        "ENDPOINT CAMPAÑAS",
        f"{base_url}/api/campaign/analyze",
        {
            "location": "Bogotá",
            "theme": "Seguridad",
            "candidate_name": "Juan Pérez",
            "max_tweets": 50,
            "language": "es"
        }
    )
    
    print("\n" + "="*80)
    print("  PRUEBAS COMPLETADAS")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()


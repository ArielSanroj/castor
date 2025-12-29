#!/usr/bin/env python3
"""
Script de prueba para verificar cómo se ven los datos de medios y campañas.
Ejecuta llamadas a los endpoints y muestra los resultados de forma clara.
"""
import json
import requests
import sys
from typing import Dict, Any
from datetime import datetime

# Colores para la terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str):
    """Imprime un encabezado formateado."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

def print_section(text: str):
    """Imprime una sección formateada."""
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}{text}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{'-'*len(text)}{Colors.ENDC}")

def print_success(text: str):
    """Imprime un mensaje de éxito."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text: str):
    """Imprime un mensaje de error."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text: str):
    """Imprime información."""
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")

def print_json(data: Dict[str, Any], indent: int = 2):
    """Imprime JSON formateado."""
    print(json.dumps(data, indent=indent, ensure_ascii=False, default=str))

def test_media_endpoint(base_url: str = "http://localhost:5001"):
    """Prueba el endpoint de medios."""
    print_header("PRUEBA ENDPOINT MEDIOS (/api/media/analyze)")
    
    url = f"{base_url}/api/media/analyze"
    
    payload = {
        "location": "Bogotá",
        "topic": "Seguridad",
        "candidate_name": None,
        "politician": None,
        "max_tweets": 10,
        "time_window_days": 7,
        "language": "es"
    }
    
    print_info(f"URL: {url}")
    print_info(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print()
    
    try:
        print_info("Enviando solicitud...")
        response = requests.post(url, json=payload, timeout=300)  # 5 minutos para dar tiempo a rate limits
        
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print_success("Respuesta exitosa!")
            data = response.json()
            
            # Mostrar estructura de la respuesta
            print_section("ESTRUCTURA DE LA RESPUESTA")
            print_json(data, indent=2)
            
            # Mostrar resumen formateado
            print_section("RESUMEN EJECUTIVO")
            if data.get("success") and data.get("summary"):
                summary = data["summary"]
                print(f"\n{Colors.BOLD}Overview:{Colors.ENDC}")
                print(f"  {summary.get('overview', 'N/A')}")
                
                if summary.get("key_stats"):
                    print(f"\n{Colors.BOLD}Estadísticas clave:{Colors.ENDC}")
                    for stat in summary["key_stats"]:
                        print(f"  • {stat}")
                
                if summary.get("key_findings"):
                    print(f"\n{Colors.BOLD}Hallazgos clave:{Colors.ENDC}")
                    for finding in summary["key_findings"]:
                        print(f"  • {finding}")
            
            # Mostrar temas
            print_section("TEMAS ANALIZADOS")
            if data.get("topics"):
                for i, topic in enumerate(data["topics"], 1):
                    print(f"\n{Colors.BOLD}Tema {i}: {topic.get('topic', 'N/A')}{Colors.ENDC}")
                    print(f"  Tweets analizados: {topic.get('tweet_count', 0)}")
                    sentiment = topic.get("sentiment", {})
                    print(f"  Sentimiento:")
                    print(f"    • Positivo: {sentiment.get('positive', 0)*100:.1f}%")
                    print(f"    • Neutro: {sentiment.get('neutral', 0)*100:.1f}%")
                    print(f"    • Negativo: {sentiment.get('negative', 0)*100:.1f}%")
            
            # Mostrar metadata
            print_section("METADATA")
            if data.get("metadata"):
                metadata = data["metadata"]
                print(f"  Ubicación: {metadata.get('location', 'N/A')}")
                print(f"  Tema: {metadata.get('topic', 'N/A')}")
                print(f"  Tweets analizados: {metadata.get('tweets_analyzed', 0)}")
                print(f"  Ventana temporal: {metadata.get('time_window_from', 'N/A')} - {metadata.get('time_window_to', 'N/A')}")
                if metadata.get("trending_topic"):
                    print(f"  Tema en tendencia: {metadata['trending_topic']}")
            
            return data
        else:
            print_error(f"Error en la respuesta: {response.status_code}")
            print_error(f"Respuesta: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print_error(f"Error al hacer la solicitud: {e}")
        return None

def test_campaign_endpoint(base_url: str = "http://localhost:5001"):
    """Prueba el endpoint de campañas."""
    print_header("PRUEBA ENDPOINT CAMPAÑAS (/api/campaign/analyze)")
    
    url = f"{base_url}/api/campaign/analyze"
    
    payload = {
        "location": "Bogotá",
        "theme": "Seguridad",
        "candidate_name": "Juan Pérez",
        "politician": None,
        "max_tweets": 50,
        "language": "es"
    }
    
    print_info(f"URL: {url}")
    print_info(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print()
    
    try:
        print_info("Enviando solicitud...")
        response = requests.post(url, json=payload, timeout=300)  # 5 minutos para dar tiempo a rate limits
        
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print_success("Respuesta exitosa!")
            data = response.json()
            
            # Mostrar estructura de la respuesta
            print_section("ESTRUCTURA DE LA RESPUESTA")
            print_json(data, indent=2)
            
            # Mostrar resumen ejecutivo
            print_section("RESUMEN EJECUTIVO")
            if data.get("success") and data.get("executive_summary"):
                summary = data["executive_summary"]
                print(f"\n{Colors.BOLD}Overview:{Colors.ENDC}")
                print(f"  {summary.get('overview', 'N/A')}")
                
                if summary.get("key_findings"):
                    print(f"\n{Colors.BOLD}Hallazgos clave:{Colors.ENDC}")
                    for finding in summary["key_findings"]:
                        print(f"  • {finding}")
                
                if summary.get("recommendations"):
                    print(f"\n{Colors.BOLD}Recomendaciones:{Colors.ENDC}")
                    for rec in summary["recommendations"]:
                        print(f"  • {rec}")
            
            # Mostrar análisis de temas
            print_section("ANÁLISIS DE TEMAS")
            if data.get("topic_analyses"):
                for i, topic in enumerate(data["topic_analyses"], 1):
                    print(f"\n{Colors.BOLD}Tema {i}: {topic.get('topic', 'N/A')}{Colors.ENDC}")
                    print(f"  Tweets analizados: {topic.get('tweet_count', 0)}")
                    sentiment = topic.get("sentiment", {})
                    print(f"  Sentimiento:")
                    print(f"    • Positivo: {sentiment.get('positive', 0)*100:.1f}%")
                    print(f"    • Neutro: {sentiment.get('neutral', 0)*100:.1f}%")
                    print(f"    • Negativo: {sentiment.get('negative', 0)*100:.1f}%")
            
            # Mostrar plan estratégico
            print_section("PLAN ESTRATÉGICO")
            if data.get("strategic_plan") and data["strategic_plan"].get("objectives"):
                for i, obj in enumerate(data["strategic_plan"]["objectives"], 1):
                    print(f"\n{Colors.BOLD}Objetivo {i}: {obj.get('name', 'N/A')}{Colors.ENDC}")
                    if obj.get("description"):
                        print(f"  Descripción: {obj['description']}")
                    if obj.get("actions"):
                        print(f"  Acciones:")
                        for action in obj["actions"]:
                            priority = action.get("priority", "N/A")
                            desc = action.get("description", "N/A")
                            print(f"    • [{priority}] {desc}")
            
            # Mostrar discurso
            print_section("DISCURSO")
            if data.get("speech"):
                speech = data["speech"]
                if speech.get("title"):
                    print(f"\n{Colors.BOLD}Título: {speech['title']}{Colors.ENDC}")
                if speech.get("key_points"):
                    print(f"\n{Colors.BOLD}Puntos clave:{Colors.ENDC}")
                    for point in speech["key_points"]:
                        print(f"  • {point}")
                if speech.get("content"):
                    print(f"\n{Colors.BOLD}Contenido:{Colors.ENDC}")
                    print(f"  {speech['content'][:500]}..." if len(speech['content']) > 500 else f"  {speech['content']}")
                if speech.get("duration_minutes"):
                    print(f"\n  Duración aproximada: {speech['duration_minutes']} minutos")
            
            # Mostrar metadata
            print_section("METADATA")
            if data.get("metadata"):
                metadata = data["metadata"]
                print(f"  Ubicación: {metadata.get('location', 'N/A')}")
                print(f"  Tema: {metadata.get('theme', 'N/A')}")
                print(f"  Candidato: {metadata.get('candidate_name', 'N/A')}")
                print(f"  Tweets analizados: {metadata.get('tweets_analyzed', 0)}")
                print(f"  Generado en: {metadata.get('generated_at', 'N/A')}")
                if metadata.get("trending_topic"):
                    print(f"  Tema en tendencia: {metadata['trending_topic']}")
            
            return data
        else:
            print_error(f"Error en la respuesta: {response.status_code}")
            print_error(f"Respuesta: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print_error(f"Error al hacer la solicitud: {e}")
        return None

def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Prueba los endpoints de medios y campañas")
    parser.add_argument(
        "--base-url",
        default="http://localhost:5001",
        help="URL base del servidor (default: http://localhost:5001)"
    )
    parser.add_argument(
        "--media-only",
        action="store_true",
        help="Solo probar el endpoint de medios"
    )
    parser.add_argument(
        "--campaign-only",
        action="store_true",
        help="Solo probar el endpoint de campañas"
    )
    
    args = parser.parse_args()
    
    print_header("SCRIPT DE PRUEBA - ENDPOINTS CASTOR ELECCIONES")
    print_info(f"Servidor: {args.base_url}")
    print_info(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Probar endpoint de medios
    if not args.campaign_only:
        print()
        media_result = test_media_endpoint(args.base_url)
        results["media"] = media_result
    
    # Probar endpoint de campañas
    if not args.media_only:
        print()
        campaign_result = test_campaign_endpoint(args.base_url)
        results["campaign"] = campaign_result
    
    # Resumen final
    print_header("RESUMEN DE PRUEBAS")
    if results.get("media"):
        print_success("Endpoint de medios: ✓ Funcionando")
    else:
        print_error("Endpoint de medios: ✗ Error")
    
    if results.get("campaign"):
        print_success("Endpoint de campañas: ✓ Funcionando")
    else:
        print_error("Endpoint de campañas: ✗ Error")
    
    print()
    print_info("Para guardar los resultados en un archivo JSON, usa:")
    print_info("  python test_endpoints.py > resultados.json 2>&1")

if __name__ == "__main__":
    main()


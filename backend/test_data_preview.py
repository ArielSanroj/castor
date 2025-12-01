#!/usr/bin/env python3
"""
Script para previsualizar cómo se ven los datos de medios y campañas.
Usa datos de ejemplo para mostrar la estructura sin hacer llamadas reales.
"""
import json
from datetime import datetime, timedelta

def print_section(title: str):
    """Imprime una sección formateada."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_json(data, indent=2):
    """Imprime JSON formateado."""
    print(json.dumps(data, indent=indent, ensure_ascii=False, default=str))

def get_media_example():
    """Genera un ejemplo de respuesta del endpoint de medios."""
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    
    return {
        "success": True,
        "summary": {
            "overview": "Un análisis de tweets recientes en Bogotá sobre el tema de Seguridad revela preocupaciones ciudadanas significativas. Se analizaron aproximadamente 10 tweets en español, excluyendo retweets, relacionados con temas de seguridad ciudadana, delincuencia y políticas públicas de seguridad.",
            "key_stats": [
                "10 tweets analizados en los últimos 7 días",
                "Distribución de sentimiento: 30% positivo, 40% negativo, 30% neutro",
                "Tema principal identificado: Seguridad ciudadana"
            ],
            "key_findings": [
                "La mayoría de los tweets muestran preocupación por la seguridad en barrios específicos",
                "Se identifican menciones frecuentes a la necesidad de mayor presencia policial",
                "Los ciudadanos expresan frustración con la respuesta de las autoridades"
            ]
        },
        "sentiment_overview": {
            "positive": 0.3,
            "negative": 0.4,
            "neutral": 0.3,
            "total_tweets": 10
        },
        "topics": [
            {
                "topic": "Seguridad",
                "tweet_count": 10,
                "sentiment": {
                    "positive": 0.3,
                    "negative": 0.4,
                    "neutral": 0.3
                }
            }
        ],
        "peaks": [],
        "chart_data": {
            "by_topic_sentiment": {
                "type": "bar",
                "data": {
                    "labels": ["Seguridad"],
                    "datasets": [
                        {
                            "label": "Positivo",
                            "data": [3],
                            "backgroundColor": "rgba(66, 214, 151, 0.8)"
                        },
                        {
                            "label": "Neutral",
                            "data": [3],
                            "backgroundColor": "rgba(136, 146, 176, 0.8)"
                        },
                        {
                            "label": "Negativo",
                            "data": [4],
                            "backgroundColor": "rgba(255, 107, 129, 0.8)"
                        }
                    ]
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "legend": {
                            "position": "top"
                        },
                        "title": {
                            "display": True,
                            "text": "Sentimiento por tema"
                        }
                    },
                    "scales": {
                        "y": {
                            "beginAtZero": True
                        }
                    }
                }
            }
        },
        "metadata": {
            "tweets_analyzed": 10,
            "location": "Bogotá",
            "topic": "Seguridad",
            "time_window_from": week_ago.isoformat(),
            "time_window_to": now.isoformat(),
            "trending_topic": None,
            "raw_query": "Bogotá AND Seguridad"
        }
    }

def get_campaign_example():
    """Genera un ejemplo de respuesta del endpoint de campañas."""
    now = datetime.utcnow()
    
    return {
        "success": True,
        "executive_summary": {
            "overview": "Un análisis de tweets recientes en Bogotá sobre Seguridad revela preocupaciones ciudadanas alineadas con conceptos clave del Plan Nacional de Desarrollo (PND 2022-2026). Se recolectaron y clasificaron aproximadamente 50 tweets en español relacionados con temas de seguridad ciudadana, delincuencia y políticas públicas.",
            "key_findings": [
                "La mayoría de los tweets muestran un tono mixto, con predominio de negativo (40%), seguido de neutral (30%) y positivo (30%)",
                "Los temas más críticos incluyen seguridad en barrios específicos y necesidad de mayor presencia policial",
                "Los ciudadanos expresan frustración con la respuesta de las autoridades ante incidentes de seguridad"
            ],
            "recommendations": [
                "Priorizar temas críticos en la estrategia de campaña, especialmente seguridad en barrios",
                "Enfocarse en soluciones prácticas para temas con sentimiento negativo predominante",
                "Aprovechar el sentimiento positivo para construir narrativas exitosas"
            ]
        },
        "topic_analyses": [
            {
                "topic": "Seguridad",
                "tweet_count": 50,
                "sentiment": {
                    "positive": 0.3,
                    "negative": 0.4,
                    "neutral": 0.3
                },
                "sample_tweets": [
                    {
                        "text": "Necesitamos más seguridad en nuestros barrios",
                        "url": "https://twitter.com/user/status/123456",
                        "sentiment": "negative"
                    },
                    {
                        "text": "Excelente trabajo de la policía en el operativo de hoy",
                        "url": "https://twitter.com/user/status/123457",
                        "sentiment": "positive"
                    }
                ]
            }
        ],
        "strategic_plan": {
            "objectives": [
                {
                    "name": "Seguridad",
                    "description": "Mejorar la seguridad ciudadana en Bogotá",
                    "actions": [
                        {
                            "description": "Aumentar la presencia policial en barrios críticos",
                            "priority": "Alta",
                            "estimated_timeline": "3 meses",
                            "expected_impact": "Reducción del 30% en índices de criminalidad"
                        },
                        {
                            "description": "Implementar programas de prevención del delito",
                            "priority": "Media",
                            "estimated_timeline": "6 meses",
                            "expected_impact": "Mayor participación ciudadana en seguridad"
                        }
                    ]
                }
            ],
            "timeline": {
                "short_term": "0-3 meses",
                "medium_term": "3-6 meses",
                "long_term": "6-12 meses"
            },
            "overall_expected_impact": "Mejora significativa en la percepción de seguridad ciudadana"
        },
        "speech": {
            "title": "Discurso sobre Seguridad para Bogotá",
            "key_points": [
                "Seguridad como prioridad número uno",
                "Mayor presencia policial en barrios",
                "Programas de prevención del delito",
                "Participación ciudadana en seguridad"
            ],
            "content": """Queridos ciudadanos de Bogotá, soy Juan Pérez, un candidato comprometido con nuestra seguridad.

Respecto a seguridad: La seguridad en Bogotá es nuestra prioridad número uno. Trabajaremos con la comunidad para crear espacios seguros donde nuestras familias puedan vivir en paz.

Implementaremos mayor presencia policial en los barrios que más lo necesitan, y crearemos programas de prevención del delito que involucren a toda la comunidad.

El gobierno de Bogotá será transparente y participativo. Cada peso público se invertirá con honestidad para garantizar la seguridad de todos los ciudadanos.

Juntos podemos hacer de Bogotá una ciudad más segura para todos.""",
            "duration_minutes": 5,
            "trending_topic": "Seguridad"
        },
        "chart_data": {
            "by_topic_sentiment": {
                "type": "bar",
                "data": {
                    "labels": ["Seguridad"],
                    "datasets": [
                        {
                            "label": "Positivo",
                            "data": [15],
                            "backgroundColor": "rgba(66, 214, 151, 0.8)"
                        },
                        {
                            "label": "Neutral",
                            "data": [15],
                            "backgroundColor": "rgba(136, 146, 176, 0.8)"
                        },
                        {
                            "label": "Negativo",
                            "data": [20],
                            "backgroundColor": "rgba(255, 107, 129, 0.8)"
                        }
                    ]
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "legend": {
                            "position": "top"
                        },
                        "title": {
                            "display": True,
                            "text": "Sentimiento por tema"
                        }
                    },
                    "scales": {
                        "y": {
                            "beginAtZero": True
                        }
                    }
                }
            }
        },
        "metadata": {
            "tweets_analyzed": 50,
            "location": "Bogotá",
            "theme": "Seguridad",
            "candidate_name": "Juan Pérez",
            "politician": None,
            "generated_at": now.isoformat(),
            "trending_topic": "Seguridad",
            "raw_query": "Bogotá AND Seguridad"
        }
    }

def main():
    """Función principal."""
    print_section("PREVISUALIZACIÓN DE DATOS - ENDPOINT MEDIOS")
    
    media_data = get_media_example()
    print("📊 ESTRUCTURA COMPLETA DE LA RESPUESTA:")
    print_json(media_data)
    
    print_section("RESUMEN EJECUTIVO (MEDIOS)")
    print(f"Overview: {media_data['summary']['overview']}")
    print(f"\nEstadísticas clave:")
    for stat in media_data['summary']['key_stats']:
        print(f"  • {stat}")
    print(f"\nHallazgos:")
    for finding in media_data['summary']['key_findings']:
        print(f"  • {finding}")
    
    print_section("TEMAS ANALIZADOS (MEDIOS)")
    for topic in media_data['topics']:
        print(f"Tema: {topic['topic']}")
        print(f"  Tweets: {topic['tweet_count']}")
        print(f"  Sentimiento: {topic['sentiment']['positive']*100:.1f}% positivo, "
              f"{topic['sentiment']['negative']*100:.1f}% negativo, "
              f"{topic['sentiment']['neutral']*100:.1f}% neutro")
    
    print_section("METADATA (MEDIOS)")
    meta = media_data['metadata']
    print(f"Ubicación: {meta['location']}")
    print(f"Tema: {meta['topic']}")
    print(f"Tweets analizados: {meta['tweets_analyzed']}")
    print(f"Ventana temporal: {meta['time_window_from']} - {meta['time_window_to']}")
    
    print("\n" + "="*80)
    print("="*80)
    
    print_section("PREVISUALIZACIÓN DE DATOS - ENDPOINT CAMPAÑAS")
    
    campaign_data = get_campaign_example()
    print("📊 ESTRUCTURA COMPLETA DE LA RESPUESTA:")
    print_json(campaign_data)
    
    print_section("RESUMEN EJECUTIVO (CAMPAÑAS)")
    print(f"Overview: {campaign_data['executive_summary']['overview']}")
    print(f"\nHallazgos clave:")
    for finding in campaign_data['executive_summary']['key_findings']:
        print(f"  • {finding}")
    print(f"\nRecomendaciones:")
    for rec in campaign_data['executive_summary']['recommendations']:
        print(f"  • {rec}")
    
    print_section("PLAN ESTRATÉGICO (CAMPAÑAS)")
    for obj in campaign_data['strategic_plan']['objectives']:
        print(f"Objetivo: {obj['name']}")
        print(f"  Descripción: {obj['description']}")
        print(f"  Acciones:")
        for action in obj['actions']:
            print(f"    • [{action['priority']}] {action['description']}")
            print(f"      Timeline: {action['estimated_timeline']}")
            print(f"      Impacto: {action['expected_impact']}")
    
    print_section("DISCURSO (CAMPAÑAS)")
    speech = campaign_data['speech']
    print(f"Título: {speech['title']}")
    print(f"Puntos clave:")
    for point in speech['key_points']:
        print(f"  • {point}")
    print(f"\nContenido (primeros 300 caracteres):")
    print(f"  {speech['content'][:300]}...")
    print(f"\nDuración: {speech['duration_minutes']} minutos")
    
    print_section("METADATA (CAMPAÑAS)")
    meta = campaign_data['metadata']
    print(f"Ubicación: {meta['location']}")
    print(f"Tema: {meta['theme']}")
    print(f"Candidato: {meta['candidate_name']}")
    print(f"Tweets analizados: {meta['tweets_analyzed']}")
    print(f"Generado en: {meta['generated_at']}")
    
    print("\n" + "="*80)
    print("  PREVISUALIZACIÓN COMPLETADA")
    print("="*80 + "\n")
    
    print("💡 NOTA: Estos son datos de ejemplo para mostrar la estructura.")
    print("   Para probar con datos reales, ejecuta:")
    print("   python3 test_endpoints_simple.py http://localhost:5001")

if __name__ == "__main__":
    main()


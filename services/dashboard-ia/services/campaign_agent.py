"""
Campaign Agent - AI agent that analyzes what wins votes and generates strategies.
This agent learns from trending topics, campaign actions, and effectiveness metrics.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from services.openai_service import OpenAIService
from services.trending_service import TrendingService
from services.database_service import DatabaseService
from models.database import CampaignAction, VoteStrategy

logger = logging.getLogger(__name__)


class CampaignAgent:
    """
    AI Agent that analyzes what wins votes and generates winning strategies.
    
    This agent:
    1. Analyzes trending topics to understand what people care about
    2. Learns from past campaign actions (what worked, what didn't)
    3. Generates strategies to win votes
    4. Provides recommendations for signature collection
    """
    
    def __init__(self):
        """Initialize campaign agent."""
        self.openai_service = OpenAIService()
        self.trending_service = TrendingService()
        self.db_service = DatabaseService()
        logger.info("CampaignAgent initialized")
    
    def analyze_what_wins_votes(
        self,
        location: str,
        user_id: str,
        candidate_name: str
    ) -> Dict[str, Any]:
        """
        Analyze what strategies win votes in a location.
        
        Args:
            location: Location to analyze
            user_id: User ID
            candidate_name: Candidate name
            
        Returns:
            Analysis of what wins votes with specific strategies
        """
        try:
            logger.info(f"Analyzing what wins votes in {location}")
            
            # 1. Get trending topics (what people care about NOW)
            trending_topics = self.trending_service.detect_trending_topics(location)
            
            # 2. Get past successful campaign actions
            successful_actions = self.db_service.get_effective_strategies(user_id, limit=10)
            
            # 3. Analyze sentiment and engagement patterns
            sentiment_analysis = self._analyze_sentiment_patterns(trending_topics)
            
            # 4. Generate winning strategies using AI
            strategies = self._generate_winning_strategies(
                location=location,
                candidate_name=candidate_name,
                trending_topics=trending_topics,
                successful_actions=successful_actions,
                sentiment_analysis=sentiment_analysis
            )
            
            # 5. Calculate vote predictions
            vote_predictions = self._predict_votes(strategies)
            
            return {
                'location': location,
                'candidate_name': candidate_name,
                'trending_topics': [t['topic'] for t in trending_topics[:5]],
                'strategies': strategies,
                'vote_predictions': vote_predictions,
                'key_insights': self._extract_key_insights(trending_topics, successful_actions),
                'recommendations': self._generate_recommendations(strategies, sentiment_analysis)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing what wins votes: {e}", exc_info=True)
            return {
                'error': str(e),
                'strategies': [],
                'vote_predictions': {}
            }
    
    def _analyze_sentiment_patterns(self, trending_topics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment patterns from trending topics."""
        if not trending_topics:
            return {}
        
        total_positive = sum(t['sentiment_positive'] for t in trending_topics)
        total_negative = sum(t['sentiment_negative'] for t in trending_topics)
        total_neutral = sum(t['sentiment_neutral'] for t in trending_topics)
        count = len(trending_topics)
        
        return {
            'avg_positive': total_positive / count if count > 0 else 0,
            'avg_negative': total_negative / count if count > 0 else 0,
            'avg_neutral': total_neutral / count if count > 0 else 0,
            'dominant_sentiment': 'positive' if total_positive > total_negative else 'negative',
            'opportunity_score': total_positive / (total_negative + 0.1)  # Higher = more opportunity
        }
    
    def _generate_winning_strategies(
        self,
        location: str,
        candidate_name: str,
        trending_topics: List[Dict[str, Any]],
        successful_actions: List[CampaignAction],
        sentiment_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate winning strategies using AI."""
        
        # Build context for AI
        trending_summary = "\n".join([
            f"- {t['topic']}: {t['tweet_count']} tweets, engagement: {t['engagement_score']}, "
            f"sentiment: {t['sentiment_positive']:.2%} positivo"
            for t in trending_topics[:5]
        ])
        
        successful_summary = "\n".join([
            f"- {a.action_type}: {a.title} - ROI: {a.roi:.2f}, Votes: {a.actual_votes}"
            for a in successful_actions[:5]
        ]) if successful_actions else "No hay acciones previas registradas"
        
        prompt = f"""Eres un experto estratega político en Colombia. Analiza los siguientes datos y genera estrategias concretas para ganar votos.

UBICACIÓN: {location}
CANDIDATO: {candidate_name}

TEMAS TRENDING (lo que la gente está discutiendo ahora):
{trending_summary}

ACCIONES EXITOSAS PREVIAS (lo que funcionó antes):
{successful_summary}

ANÁLISIS DE SENTIMIENTO:
- Sentimiento promedio positivo: {sentiment_analysis.get('avg_positive', 0):.2%}
- Sentimiento promedio negativo: {sentiment_analysis.get('avg_negative', 0):.2%}
- Oportunidad: {sentiment_analysis.get('opportunity_score', 0):.2f}

Genera 5 estrategias concretas para ganar votos. Cada estrategia debe incluir:

1. Nombre de la estrategia
2. Descripción detallada
3. Mensajes clave a comunicar
4. Canales recomendados (redes sociales, eventos, medios, etc.)
5. Timing (cuándo ejecutar)
6. Demografía objetivo
7. Votos estimados
8. Nivel de confianza (0-1)
9. Nivel de riesgo (bajo, medio, alto)

Formato JSON:
{{
    "strategies": [
        {{
            "strategy_name": "Nombre",
            "description": "Descripción",
            "key_messages": ["mensaje 1", "mensaje 2"],
            "channels": ["canal 1", "canal 2"],
            "timing": "cuándo ejecutar",
            "target_demographic": "demografía",
            "predicted_votes": 1000,
            "confidence_score": 0.85,
            "risk_level": "medio"
        }}
    ]
}}"""

        try:
            response = self.openai_service.client.chat.completions.create(
                model=self.openai_service.model,
                messages=[
                    {"role": "system", "content": "Eres un estratega político experto. Responde siempre en español y formato JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            strategies = result.get('strategies', [])
            
            # Add trending topic context
            for strategy in strategies:
                strategy['based_on_trending_topics'] = [t['topic'] for t in trending_topics[:3]]
                strategy['sentiment_alignment'] = sentiment_analysis.get('opportunity_score', 0)
            
            return strategies
            
        except Exception as e:
            logger.error(f"Error generating strategies: {e}", exc_info=True)
            # Return fallback strategies
            return [
                {
                    'strategy_name': 'Enfoque en Temas Trending',
                    'description': f'Alinear discurso con temas trending en {location}',
                    'key_messages': ['Mensaje alineado con preocupaciones ciudadanas'],
                    'channels': ['Twitter', 'Facebook', 'Eventos públicos'],
                    'timing': 'Inmediato',
                    'target_demographic': 'General',
                    'predicted_votes': 500,
                    'confidence_score': 0.7,
                    'risk_level': 'bajo'
                }
            ]
    
    def _predict_votes(self, strategies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Predict votes for each strategy."""
        predictions = {}
        
        for strategy in strategies:
            base_votes = strategy.get('predicted_votes', 0)
            confidence = strategy.get('confidence_score', 0.5)
            
            # Adjust based on confidence
            adjusted_votes = int(base_votes * confidence)
            
            predictions[strategy.get('strategy_name', 'Unknown')] = {
                'base_prediction': base_votes,
                'confidence_adjusted': adjusted_votes,
                'confidence': confidence,
                'risk_level': strategy.get('risk_level', 'medio')
            }
        
        total_predicted = sum(p['confidence_adjusted'] for p in predictions.values())
        
        return {
            'by_strategy': predictions,
            'total_predicted': total_predicted,
            'best_strategy': max(predictions.items(), key=lambda x: x[1]['confidence_adjusted'])[0] if predictions else None
        }
    
    def _extract_key_insights(
        self,
        trending_topics: List[Dict[str, Any]],
        successful_actions: List[CampaignAction]
    ) -> List[str]:
        """Extract key insights."""
        insights = []
        
        if trending_topics:
            top_topic = trending_topics[0]
            insights.append(
                f"El tema más trending es '{top_topic['topic']}' con "
                f"{top_topic['tweet_count']} menciones y engagement de {top_topic['engagement_score']:.0f}"
            )
        
        if successful_actions:
            best_action = successful_actions[0]
            insights.append(
                f"La acción más exitosa fue '{best_action.title}' con ROI de {best_action.roi:.2f}"
            )
        
        if trending_topics:
            avg_sentiment = sum(t['sentiment_positive'] for t in trending_topics) / len(trending_topics)
            if avg_sentiment > 0.5:
                insights.append("El sentimiento general es positivo - oportunidad para mensajes optimistas")
            else:
                insights.append("El sentimiento es negativo - enfocarse en soluciones concretas")
        
        return insights
    
    def _generate_recommendations(
        self,
        strategies: List[Dict[str, Any]],
        sentiment_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if strategies:
            best_strategy = max(strategies, key=lambda x: x.get('confidence_score', 0))
            recommendations.append(
                f"Estrategia recomendada: '{best_strategy.get('strategy_name')}' "
                f"(Confianza: {best_strategy.get('confidence_score', 0):.0%})"
            )
        
        if sentiment_analysis.get('opportunity_score', 0) > 1.5:
            recommendations.append("Alta oportunidad: El sentimiento positivo es favorable para campaña")
        
        recommendations.append("Ejecutar estrategias en los próximos 7 días para maximizar impacto")
        recommendations.append("Monitorear trending topics diariamente para ajustar mensajes")
        
        return recommendations
    
    def generate_signature_collection_strategy(
        self,
        campaign_id: str,
        location: str,
        target_signatures: int
    ) -> Dict[str, Any]:
        """
        Generate strategy for collecting signatures.
        
        Args:
            campaign_id: Campaign identifier
            location: Location
            target_signatures: Target number of signatures
            
        Returns:
            Strategy for signature collection
        """
        try:
            current_signatures = self.db_service.get_campaign_signatures(campaign_id)
            remaining = max(0, target_signatures - current_signatures)
            
            prompt = f"""Genera una estrategia para recolectar {remaining} firmas más en {location}.

Firmas actuales: {current_signatures}
Meta: {target_signatures}
Faltan: {remaining}

Genera estrategia con:
1. Canales de recolección (digital, presencial, híbrido)
2. Mensajes persuasivos
3. Incentivos o llamados a la acción
4. Timing y frecuencia
5. Métricas de seguimiento

Formato JSON con estrategia detallada."""

            response = self.openai_service.client.chat.completions.create(
                model=self.openai_service.model,
                messages=[
                    {"role": "system", "content": "Eres experto en recolección de firmas para campañas políticas."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            import json
            strategy = json.loads(response.choices[0].message.content)
            
            return {
                'current_signatures': current_signatures,
                'target': target_signatures,
                'remaining': remaining,
                'strategy': strategy,
                'recommendations': [
                    f"Usar {strategy.get('channels', ['múltiples canales'])} para recolección",
                    f"Enfocarse en mensajes: {', '.join(strategy.get('key_messages', [])[:2])}",
                    f"Ejecutar en: {strategy.get('timing', 'próximos días')}"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating signature strategy: {e}", exc_info=True)
            return {
                'current_signatures': current_signatures,
                'target': target_signatures,
                'remaining': remaining,
                'strategy': {
                    'channels': ['Redes sociales', 'Eventos presenciales', 'WhatsApp'],
                    'key_messages': ['Tu firma cuenta', 'Juntos por el cambio'],
                    'timing': 'Inmediato'
                }
            }


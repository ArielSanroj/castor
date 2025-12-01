"""
Narrative Metrics Service - Calculates electoral narrative indices.
Implements SVE, SNA, CP, NMI, and IVN without predicting actual vote intention.
"""
import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict
import re

logger = logging.getLogger(__name__)


class NarrativeMetricsService:
    """
    Service for calculating narrative electoral metrics.
    These metrics measure narrative strength, not vote intention.
    """

    def calculate_share_of_voice_electoral(
        self,
        tweets: List[Dict[str, Any]],
        candidate_name: Optional[str] = None,
        topic: Optional[str] = None
    ) -> float:
        """
        Calculate Share of Voice Electoral (SVE).
        
        SVE = mentions_candidate / total_mentions_in_topic
        
        Returns:
            Float between 0.0 and 1.0
        """
        if not tweets:
            return 0.0
        
        if not candidate_name:
            # If no candidate specified, calculate average SVE for all candidates mentioned
            return 0.5  # Neutral baseline
        
        candidate_mentions = 0
        total_mentions = len(tweets)
        
        # Normalize candidate name for matching
        candidate_lower = candidate_name.lower()
        candidate_words = candidate_lower.split()
        
        for tweet in tweets:
            text = tweet.get('text', '').lower()
            
            # Check for candidate name mentions
            if any(word in text for word in candidate_words if len(word) > 3):
                candidate_mentions += 1
        
        sve = candidate_mentions / total_mentions if total_mentions > 0 else 0.0
        return min(1.0, max(0.0, sve))

    def calculate_sentiment_net_adjusted(
        self,
        tweets: List[Dict[str, Any]],
        sentiment_scores: List[Dict[str, float]]
    ) -> float:
        """
        Calculate Sentiment Net Adjusted (SNA).
        
        SNA = (positive - negative) / total
        
        Returns:
            Float between -1.0 and 1.0
        """
        if not tweets or not sentiment_scores:
            return 0.0
        
        total_positive = 0.0
        total_negative = 0.0
        total = len(sentiment_scores)
        
        for sentiment in sentiment_scores:
            total_positive += sentiment.get('positive', 0.0)
            total_negative += sentiment.get('negative', 0.0)
        
        if total == 0:
            return 0.0
        
        sna = (total_positive - total_negative) / total
        return max(-1.0, min(1.0, sna))

    def calculate_comparative_preference(
        self,
        tweets: List[Dict[str, Any]],
        candidate_name: Optional[str] = None
    ) -> float:
        """
        Calculate Comparative Preference (CP).
        
        Detects tweets that compare candidates/proposals.
        CP = favorable_comparisons / total_comparisons
        
        Returns:
            Float between 0.0 and 1.0
        """
        if not tweets or not candidate_name:
            return 0.5  # Neutral baseline
        
        comparison_patterns = [
            r'más\s+(bueno|mejor|convincente|sólido|claro)',
            r'prefiero\s+(a\s+)?',
            r'me\s+gusta\s+más',
            r'vs\s+',
            r'comparado\s+con',
            r'en\s+comparación'
        ]
        
        favorable_keywords = [
            'mejor', 'más', 'prefiero', 'me gusta', 'convincente',
            'sólido', 'claro', 'correcto', 'acertado'
        ]
        
        unfavorable_keywords = [
            'peor', 'menos', 'no me gusta', 'débil', 'confuso',
            'incorrecto', 'equivocado'
        ]
        
        candidate_lower = candidate_name.lower()
        comparisons = 0
        favorable = 0
        
        for tweet in tweets:
            text = tweet.get('text', '').lower()
            
            # Check if tweet contains comparison patterns
            has_comparison = any(re.search(pattern, text) for pattern in comparison_patterns)
            
            if has_comparison and candidate_lower in text:
                comparisons += 1
                
                # Check if comparison is favorable
                has_favorable = any(keyword in text for keyword in favorable_keywords)
                has_unfavorable = any(keyword in text for keyword in unfavorable_keywords)
                
                if has_favorable and not has_unfavorable:
                    favorable += 1
                elif has_unfavorable and not has_favorable:
                    # Unfavorable comparison
                    pass
        
        if comparisons == 0:
            return 0.5  # Neutral if no comparisons found
        
        cp = favorable / comparisons
        return max(0.0, min(1.0, cp))

    def calculate_narrative_motivation_index(
        self,
        tweets: List[Dict[str, Any]],
        sentiment_scores: List[Dict[str, float]]
    ) -> float:
        """
        Calculate Narrative Motivation Index (NMI).
        
        NMI = (hope + pride) - (frustration + anger)
        
        Uses sentiment analysis to infer emotional motivation.
        
        Returns:
            Float between -1.0 and 1.0
        """
        if not tweets or not sentiment_scores:
            return 0.0
        
        # Map sentiment to emotions
        # Positive sentiment → hope/pride
        # Negative sentiment → frustration/anger
        # Neutral → neutral
        
        hope_pride = 0.0
        frustration_anger = 0.0
        
        positive_emotion_keywords = [
            'esperanza', 'confianza', 'orgullo', 'optimismo', 'fe',
            'mejor', 'progreso', 'avance', 'éxito', 'logro'
        ]
        
        negative_emotion_keywords = [
            'frustración', 'enojo', 'ira', 'desilusión', 'decepción',
            'fracaso', 'problema', 'crisis', 'preocupación', 'miedo'
        ]
        
        for i, tweet in enumerate(tweets):
            text = tweet.get('text', '').lower()
            sentiment = sentiment_scores[i] if i < len(sentiment_scores) else {}
            
            positive_score = sentiment.get('positive', 0.0)
            negative_score = sentiment.get('negative', 0.0)
            
            # Check for emotional keywords
            has_positive_emotion = any(keyword in text for keyword in positive_emotion_keywords)
            has_negative_emotion = any(keyword in text for keyword in negative_emotion_keywords)
            
            if has_positive_emotion or positive_score > 0.6:
                hope_pride += positive_score
            elif has_negative_emotion or negative_score > 0.6:
                frustration_anger += negative_score
        
        total = len(tweets)
        if total == 0:
            return 0.0
        
        nmi = (hope_pride - frustration_anger) / total
        return max(-1.0, min(1.0, nmi))

    def calculate_ivn_score(
        self,
        sve: float,
        sna: float,
        cp: float,
        nmi: float
    ) -> Dict[str, Any]:
        """
        Calculate Intención de Voto Narrativa (IVN).
        
        IVN = 0.4*SVE + 0.3*SNA + 0.2*CP + 0.1*NMI
        
        Returns:
            Dict with IVN score and interpretation
        """
        # Normalize inputs to 0-1 range
        sve_norm = max(0.0, min(1.0, sve))
        sna_norm = (sna + 1.0) / 2.0  # Convert -1,1 to 0,1
        cp_norm = max(0.0, min(1.0, cp))
        nmi_norm = (nmi + 1.0) / 2.0  # Convert -1,1 to 0,1
        
        # Calculate IVN
        ivn = (
            0.4 * sve_norm +
            0.3 * sna_norm +
            0.2 * cp_norm +
            0.1 * nmi_norm
        )
        
        # Interpret IVN
        if ivn >= 0.80:
            interpretation = "Narrativa dominante (alta probabilidad de consolidación)"
            risk_level = "bajo"
        elif ivn >= 0.60:
            interpretation = "Competitivo con sesgo positivo"
            risk_level = "medio-bajo"
        elif ivn >= 0.40:
            interpretation = "Territorio neutral, depende de ejecución"
            risk_level = "medio"
        elif ivn >= 0.20:
            interpretation = "Pérdida de narrativa"
            risk_level = "medio-alto"
        else:
            interpretation = "Narrativa rota o crisis"
            risk_level = "alto"
        
        return {
            "ivn": ivn,
            "interpretation": interpretation,
            "risk_level": risk_level,
            "components": {
                "sve": sve_norm,
                "sna": sna_norm,
                "cp": cp_norm,
                "nmi": nmi_norm
            }
        }

    def calculate_all_metrics(
        self,
        tweets: List[Dict[str, Any]],
        sentiment_scores: List[Dict[str, float]],
        candidate_name: Optional[str] = None,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate all narrative metrics at once.
        
        Returns:
            Dict with all metrics and IVN score
        """
        sve = self.calculate_share_of_voice_electoral(tweets, candidate_name, topic)
        sna = self.calculate_sentiment_net_adjusted(tweets, sentiment_scores)
        cp = self.calculate_comparative_preference(tweets, candidate_name)
        nmi = self.calculate_narrative_motivation_index(tweets, sentiment_scores)
        
        ivn_result = self.calculate_ivn_score(sve, sna, cp, nmi)
        
        return {
            "sve": sve,
            "sna": sna,
            "cp": cp,
            "nmi": nmi,
            "ivn": ivn_result
        }


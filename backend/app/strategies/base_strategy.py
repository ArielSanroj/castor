"""
Base Topic Strategy with common functionality.
Template Method Pattern - defines skeleton, subclasses override specifics.
"""
import re
from typing import List, Dict, Any, Optional
from app.interfaces.topic_strategy import (
    ITopicStrategy,
    TopicConfig,
    PNDTopic,
)


class BaseTopicStrategy(ITopicStrategy):
    """
    Base implementation with common topic strategy functionality.
    Subclasses override topic-specific behavior.
    """

    def __init__(self):
        self._config: Optional[TopicConfig] = None

    @property
    def topic(self) -> PNDTopic:
        """Override in subclass."""
        raise NotImplementedError

    @property
    def config(self) -> TopicConfig:
        """Override in subclass or set _config in __init__."""
        if self._config is None:
            raise NotImplementedError("Subclass must set _config")
        return self._config

    def get_search_keywords(self, location: Optional[str] = None) -> str:
        """Build search query from keywords."""
        keywords = self.config.keywords
        query = " OR ".join(keywords)

        if location:
            query = f"({query}) {location}"

        return query

    def get_hashtags(self) -> List[str]:
        """Get hashtags from config."""
        return self.config.hashtags

    def classify_tweet(self, tweet_text: str) -> float:
        """
        Calculate relevance score based on keyword matches.
        """
        if not tweet_text:
            return 0.0

        text_lower = tweet_text.lower()
        keywords = [k.lower() for k in self.config.keywords]

        # Count keyword matches
        matches = sum(1 for kw in keywords if kw in text_lower)

        # Normalize to 0-1 range
        if not keywords:
            return 0.0

        score = min(matches / len(keywords), 1.0)

        # Boost for hashtag matches
        hashtags = [h.lower() for h in self.config.hashtags]
        hashtag_matches = sum(1 for h in hashtags if h in text_lower)
        if hashtag_matches > 0:
            score = min(score + 0.2, 1.0)

        return score

    def interpret_sentiment(
        self,
        sentiment_scores: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Default sentiment interpretation.
        Override for topic-specific interpretation.
        """
        positive = sentiment_scores.get("positive", 0.33)
        negative = sentiment_scores.get("negative", 0.33)
        neutral = sentiment_scores.get("neutral", 0.34)

        # Determine dominant sentiment
        if positive > negative and positive > neutral:
            dominant = "positive"
            interpretation = f"Percepción favorable sobre {self.config.display_name}"
        elif negative > positive and negative > neutral:
            dominant = "negative"
            interpretation = f"Preocupación ciudadana sobre {self.config.display_name}"
        else:
            dominant = "neutral"
            interpretation = f"Opinión dividida sobre {self.config.display_name}"

        # Calculate intensity
        max_score = max(positive, negative, neutral)
        if max_score > 0.7:
            intensity = "alta"
        elif max_score > 0.5:
            intensity = "moderada"
        else:
            intensity = "baja"

        return {
            "dominant": dominant,
            "intensity": intensity,
            "interpretation": interpretation,
            "scores": sentiment_scores,
            "topic": self.config.name,
            "context": context
        }

    def generate_insights(
        self,
        tweets: List[Dict[str, Any]],
        aggregated_sentiment: Dict[str, float]
    ) -> List[str]:
        """
        Generate basic insights from analyzed tweets.
        Override for topic-specific insights.
        """
        insights = []
        tweet_count = len(tweets)

        if tweet_count == 0:
            return [f"No se encontraron tweets sobre {self.config.display_name}"]

        # Volume insight
        insights.append(
            f"Se analizaron {tweet_count} tweets relacionados con {self.config.display_name}"
        )

        # Sentiment insight
        positive = aggregated_sentiment.get("positive", 0)
        negative = aggregated_sentiment.get("negative", 0)

        if positive > negative * 1.5:
            insights.append(
                f"El sentimiento general hacia {self.config.display_name} es positivo"
            )
        elif negative > positive * 1.5:
            insights.append(
                f"Existe preocupación significativa sobre {self.config.display_name}"
            )
        else:
            insights.append(
                f"Las opiniones sobre {self.config.display_name} están divididas"
            )

        return insights

    def get_recommendations(
        self,
        sentiment: Dict[str, float],
        location: str,
        candidate_name: Optional[str] = None
    ) -> List[str]:
        """
        Generate basic recommendations.
        Override for topic-specific recommendations.
        """
        recommendations = []
        candidate = candidate_name or "el candidato"
        positive = sentiment.get("positive", 0)
        negative = sentiment.get("negative", 0)

        if negative > positive:
            recommendations.append(
                f"Priorizar {self.config.display_name} en el discurso de {candidate} para {location}"
            )
            recommendations.append(
                f"Desarrollar propuestas concretas sobre {self.config.display_name}"
            )
        else:
            recommendations.append(
                f"Mantener el enfoque positivo en {self.config.display_name}"
            )
            recommendations.append(
                f"Comunicar logros y planes futuros sobre {self.config.display_name}"
            )

        return recommendations

    def _extract_common_words(
        self,
        tweets: List[Dict[str, Any]],
        top_n: int = 10
    ) -> List[str]:
        """Extract most common words from tweets (excluding stopwords)."""
        stopwords = {
            "de", "la", "que", "el", "en", "y", "a", "los", "se", "del",
            "las", "un", "por", "con", "no", "una", "su", "para", "es",
            "al", "lo", "como", "más", "pero", "sus", "le", "ya", "o",
            "este", "ha", "me", "sin", "sobre", "ser", "tiene", "también"
        }

        word_count: Dict[str, int] = {}
        for tweet in tweets:
            text = tweet.get("text", "").lower()
            words = re.findall(r'\b\w+\b', text)
            for word in words:
                if len(word) > 3 and word not in stopwords:
                    word_count[word] = word_count.get(word, 0) + 1

        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:top_n]]

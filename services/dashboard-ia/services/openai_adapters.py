"""
OpenAI Schema Adapters for CASTOR ELECCIONES.
Converts between old and new schema formats for content generation.
"""
from typing import List

from models.schemas import PNDTopicAnalysis, SentimentData
from app.schemas.core import CoreAnalysisResult
from app.schemas.campaign import (
    CampaignAnalysisRequest as NewCampaignRequest,
    ExecutiveSummary as NewExecutiveSummary,
    StrategicPlan as NewStrategicPlan,
    Speech as NewSpeech,
)


def convert_to_pnd_analyses(core_result: CoreAnalysisResult) -> List[PNDTopicAnalysis]:
    """Convert core result topics to PNDTopicAnalysis format."""
    return [
        PNDTopicAnalysis(
            topic=t.topic,
            sentiment=SentimentData(
                positive=t.sentiment.positive if hasattr(t, 'sentiment') else 0.33,
                negative=t.sentiment.negative if hasattr(t, 'sentiment') else 0.33,
                neutral=t.sentiment.neutral if hasattr(t, 'sentiment') else 0.34
            ),
            tweet_count=t.tweet_count if hasattr(t, 'tweet_count') else 0,
            key_insights=t.key_insights if hasattr(t, 'key_insights') else [],
            sample_tweets=t.sample_tweets if hasattr(t, 'sample_tweets') else []
        )
        for t in core_result.topics
    ]


class OpenAIAdapters:
    """Schema adapters for OpenAI service."""

    def __init__(self, service):
        """
        Initialize with OpenAI service.

        Args:
            service: OpenAIService instance
        """
        self.service = service

    def generate_executive_summary_new(
        self,
        core_result: CoreAnalysisResult,
        request: NewCampaignRequest
    ) -> NewExecutiveSummary:
        """Generate executive summary using new schema format."""
        topic_analyses = convert_to_pnd_analyses(core_result)
        result = self.service.generate_executive_summary(
            request.location,
            topic_analyses,
            request.candidate_name
        )
        return NewExecutiveSummary(
            overview=result.overview,
            key_findings=result.key_findings,
            recommendations=result.recommendations
        )

    def generate_strategic_plan_new(
        self,
        core_result: CoreAnalysisResult,
        request: NewCampaignRequest
    ) -> NewStrategicPlan:
        """Generate strategic plan using new schema format."""
        topic_analyses = convert_to_pnd_analyses(core_result)
        result = self.service.generate_strategic_plan(
            request.location,
            topic_analyses,
            request.candidate_name
        )
        return NewStrategicPlan(
            objectives=result.objectives,
            actions=result.actions,
            timeline=result.timeline,
            expected_impact=result.expected_impact
        )

    def generate_speech_new(
        self,
        core_result: CoreAnalysisResult,
        request: NewCampaignRequest
    ) -> NewSpeech:
        """Generate speech using new schema format."""
        topic_analyses = convert_to_pnd_analyses(core_result)
        trending = {"topic": core_result.trending_topic} if core_result.trending_topic else None
        result = self.service.generate_speech(
            request.location,
            topic_analyses,
            request.candidate_name or "el candidato",
            trending
        )
        return NewSpeech(
            title=result.title,
            content=result.content,
            key_points=result.key_points,
            duration_minutes=result.duration_minutes
        )

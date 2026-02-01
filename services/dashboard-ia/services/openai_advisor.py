"""
OpenAI Advisor Service for CASTOR ELECCIONES.
Handles advisor recommendations generation.
"""
import logging
from typing import Callable, Dict, Any

from app.schemas.advisor import AdvisorRequest, AdvisorResponse, AdvisorDraft
from .openai_prompts import ADVISOR_SYSTEM, build_advisor_prompt

logger = logging.getLogger(__name__)


class AdvisorGenerator:
    """Generates advisor recommendations using OpenAI."""

    def __init__(self, make_json_completion: Callable):
        """
        Initialize with JSON completion function.

        Args:
            make_json_completion: Function to make JSON API calls
        """
        self._make_json_completion = make_json_completion

    def generate_recommendations(self, req: AdvisorRequest) -> AdvisorResponse:
        """Generate human-in-the-loop draft suggestions (no auto-posting)."""
        prompt = self._build_prompt(req)

        try:
            result = self._make_json_completion(ADVISOR_SYSTEM, prompt, temperature=0.6)
            drafts = [AdvisorDraft(**item) for item in result.get("drafts", [])]
            guidance = result.get("guidance", "Revisar y aprobar manualmente antes de publicar.")
            return AdvisorResponse(success=True, approval_required=True, guidance=guidance, drafts=drafts)
        except Exception as e:
            logger.error("Error generating advisor recommendations: %s", e, exc_info=True)
            return self._fallback_response(req)

    def _build_prompt(self, req: AdvisorRequest) -> str:
        """Build advisor prompt from request."""
        profile = req.candidate_profile
        return build_advisor_prompt(
            location=req.location,
            topics=", ".join(req.topics) if req.topics else "tema general",
            profile_name=profile.name or "candidato",
            profile_role=profile.role or "candidato",
            profile_tone=profile.tone,
            values=", ".join(profile.values) or "transparencia, bienestar",
            red_lines=", ".join(profile.red_lines) or "desinformacion, ataques",
            goals=", ".join(req.goals) if req.goals else "claridad narrativa",
            constraints=", ".join(req.constraints) if req.constraints else "evitar ataques personales",
            source_summary=req.source_summary
        )

    def _fallback_response(self, req: AdvisorRequest) -> AdvisorResponse:
        """Return fallback advisor response on error."""
        topics = ", ".join(req.topics) if req.topics else "tema general"
        fallback = [AdvisorDraft(
            kind="post",
            intent="informar",
            draft=f"Hoy el tema {topics} concentra la conversacion en {req.location}. Seguiremos informando con datos verificables.",
            rationale="Mantiene tono institucional y reconoce el tema dominante.",
            risk_level="bajo",
            best_time="tarde"
        )]
        return AdvisorResponse(
            success=True,
            approval_required=True,
            guidance="Borradores generados automaticamente. Revisar antes de publicar.",
            drafts=fallback
        )

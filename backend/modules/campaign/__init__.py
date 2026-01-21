"""
Campaign Module.

Handles campaign content generation, strategic planning, and advisor recommendations.
This module can be extracted as a microservice in the future.

Public Interface:
    - CampaignModule: Main facade for campaign operations
"""

from .facade import CampaignModule

__all__ = [
    "CampaignModule",
]

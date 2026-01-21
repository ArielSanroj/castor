"""
Analysis Module.

Handles social media analysis, sentiment processing, and topic classification.
This module can be extracted as a microservice in the future.

Public Interface:
    - AnalysisModule: Main facade for analysis operations
    - AnalysisRequest: Request model for analysis
    - AnalysisResult: Result model for analysis
"""

from .facade import AnalysisModule
from .models import AnalysisRequest, AnalysisResult

__all__ = [
    "AnalysisModule",
    "AnalysisRequest",
    "AnalysisResult",
]

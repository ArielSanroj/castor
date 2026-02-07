"""
Analyzers for the Electoral Intelligence Agent.
These components process data and generate insights.
"""
from services.agent.analyzers.anomaly_detector import AnomalyDetector
from services.agent.analyzers.legal_classifier import LegalClassifier
from services.agent.analyzers.risk_scorer import RiskScorer
from services.agent.analyzers.pattern_recognizer import PatternRecognizer

__all__ = ['AnomalyDetector', 'LegalClassifier', 'RiskScorer', 'PatternRecognizer']

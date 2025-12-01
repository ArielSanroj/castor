"""
Singleton pattern for BETO model to avoid loading it multiple times.
This significantly reduces memory usage and startup time.
"""
import logging
import threading
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import Tuple, Optional
from config import Config

logger = logging.getLogger(__name__)

# Global cache for model instances
_model_cache: dict = {}
_model_lock = threading.Lock()


def get_beto_model() -> Tuple[AutoModelForSequenceClassification, AutoTokenizer, torch.device]:
    """
    Get or create BETO model singleton.
    
    Returns:
        Tuple of (model, tokenizer, device)
    """
    global _model_cache
    model_key = Config.BETO_MODEL_PATH
    
    if model_key not in _model_cache:
        with _model_lock:
            # Double-check pattern
            if model_key not in _model_cache:
                logger.info(f"Loading BETO model singleton: {model_key}")
                try:
                    tokenizer = AutoTokenizer.from_pretrained(model_key)
                    model = AutoModelForSequenceClassification.from_pretrained(
                        model_key,
                        num_labels=3  # positive, negative, neutral
                    )
                    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                    model.to(device)
                    model.eval()
                    _model_cache[model_key] = (model, tokenizer, device)
                    logger.info(f"BETO model singleton loaded successfully on {device}")
                except Exception as e:
                    logger.error(f"Error loading BETO model: {e}", exc_info=True)
                    raise
    
    return _model_cache[model_key]


def clear_model_cache():
    """Clear model cache (useful for testing)."""
    global _model_cache
    with _model_lock:
        _model_cache.clear()
        logger.info("BETO model cache cleared")


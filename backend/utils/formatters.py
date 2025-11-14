"""
Formatting utilities.
"""
import re
from typing import Optional


def format_phone_number(phone_number: str) -> str:
    """
    Format phone number to standard format.
    
    Args:
        phone_number: Phone number to format
        
    Returns:
        Formatted phone number
    """
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone_number)
    
    # Ensure it starts with +
    if not cleaned.startswith('+'):
        cleaned = '+' + cleaned
    
    return cleaned


def format_tweet_text(text: str, max_length: int = 280) -> str:
    """
    Format and truncate tweet text.
    
    Args:
        text: Tweet text
        max_length: Maximum length
        
    Returns:
        Formatted text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Truncate if needed
    if len(text) > max_length:
        text = text[:max_length - 3] + "..."
    
    return text


def format_location(location: str) -> str:
    """
    Format location string (title case).
    
    Args:
        location: Location string
        
    Returns:
        Formatted location
    """
    if not location:
        return ""
    
    # Title case but preserve special cases
    words = location.split()
    formatted_words = []
    
    for word in words:
        if word.lower() in ['de', 'del', 'la', 'el', 'y', 'en']:
            formatted_words.append(word.lower())
        else:
            formatted_words.append(word.capitalize())
    
    return ' '.join(formatted_words)


import logging
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

def calculate_confidence(matches: List[Tuple[str, float, str]]) -> Tuple[str, float, str]:
    """
    Calculate the overall confidence based on multiple matching results.
    
    Args:
        matches: List of tuples (target_url, confidence_score, reason)
        
    Returns:
        The best match as a tuple (target_url, confidence_score, reason)
    """
    if not matches:
        return None, 0.0, "No matches found"
    
    # Sort matches by confidence score
    sorted_matches = sorted(matches, key=lambda x: x[1], reverse=True)
    
    # Return the best match
    return sorted_matches[0]

def adjust_confidence(base_confidence: float, factors: Dict[str, float]) -> float:
    """
    Adjust a base confidence score with various factors.
    
    Args:
        base_confidence: The starting confidence score (0-1)
        factors: Dictionary of factors to adjust the score (values can be positive or negative)
        
    Returns:
        Adjusted confidence score (clamped to 0-1 range)
    """
    # Apply all factors
    adjusted = base_confidence
    
    for factor_name, factor_value in factors.items():
        adjusted += factor_value
        logger.debug(f"Applied factor {factor_name}: {factor_value}, new score: {adjusted}")
    
    # Clamp to 0-1 range
    return max(0.0, min(1.0, adjusted)) 
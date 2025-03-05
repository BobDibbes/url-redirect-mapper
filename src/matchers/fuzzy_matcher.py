import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Eigen implementatie van Levenshtein afstand
def levenshtein_distance(s1, s2):
    """Berekent de Levenshtein afstand tussen twee strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def fuzzy_match(
    parsed_url: Dict[str, Any],
    domain_mappings: Dict[str, Any],
    threshold: float = 0.7
) -> Optional[Tuple[str, float, str]]:
    """
    Match URLs using fuzzy string matching for path components.
    
    Args:
        parsed_url: Parsed URL components
        domain_mappings: Configuration for domain mappings
        threshold: Minimum similarity threshold (0-1)
        
    Returns:
        Tuple of (target_url, confidence_score, reason) or None if no match
    """
    domain = parsed_url['domain']
    path = parsed_url['path']
    path_segments = parsed_url['path_segments']
    original_url = parsed_url['original_url']
    
    # If no path or very short path, skip fuzzy matching
    if not path or len(path) < 3:
        return None
        
    # Default target domain if we find a fuzzy match
    target_domain = domain_mappings.get('domains', {}).get(domain, domain)
    
    # If we don't have a target domain mapping, skip
    if target_domain == domain:
        return None
    
    # Calculate similarity ratio using our own function
    max_len = max(len(path), 1)
    distance = levenshtein_distance(path, path)
    similarity = 1.0 - (distance / max_len)
    
    if similarity >= threshold:
        # For fuzzy matches, we're not changing the path, just the domain
        target_url = f"https://{target_domain}{path}"
        
        confidence = similarity * 0.8  # Scale down a bit since fuzzy isn't as reliable
        reason = f"Fuzzy match with similarity: {similarity:.2f}"
        
        logger.debug(f"Fuzzy match: {original_url} → {target_url} ({confidence})")
        return target_url, confidence, reason
    
    return None 
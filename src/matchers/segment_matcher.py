import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

def match_by_segment(
    parsed_url: Dict[str, Any],
    dictionaries: Dict[str, Dict[str, str]],
    domain_mappings: Dict[str, Any]
) -> Optional[Tuple[str, float, str]]:
    """
    Match URLs by translating path segments using dictionaries.
    
    Args:
        parsed_url: Parsed URL components
        dictionaries: Language-specific word mappings
        domain_mappings: Configuration for domain mappings
        
    Returns:
        Tuple of (target_url, confidence_score, reason) or None if no match
    """
    domain = parsed_url['domain']
    path_segments = parsed_url['path_segments']
    language_code = parsed_url['language_code']
    original_url = parsed_url['original_url']
    
    # Skip if no language code detected or no path segments
    if not language_code or not path_segments:
        return None
    
    # Determine which dictionary to use based on language code
    # We'll try xx_en (e.g., fr_en) first, then fallback to just the language code
    dict_key = f"{language_code}_en"
    if dict_key not in dictionaries:
        dict_key = language_code
        if dict_key not in dictionaries:
            return None
    
    # Get the relevant dictionary
    dictionary = dictionaries.get(dict_key, {})
    
    # Check if we need to map domains
    target_domain = domain_mappings.get('domains', {}).get(domain, domain)
    
    # Skip if no domain mapping (nothing to transform)
    if target_domain == domain and not dictionary:
        return None
    
    # Try to translate path segments
    translated_segments = []
    segments_translated = 0
    
    for segment in path_segments:
        # Try to find the segment in the dictionary
        translated = dictionary.get(segment.lower(), segment)
        translated_segments.append(translated)
        
        if translated != segment:
            segments_translated += 1
    
    # If we couldn't translate any segments, return None
    if segments_translated == 0:
        return None
    
    # Construct the target URL
    target_path = "/" + "/".join(translated_segments)
    target_url = f"https://{target_domain}{target_path}"
    
    # Calculate confidence based on percentage of segments translated
    segments_ratio = segments_translated / len(path_segments)
    confidence = 0.7 + (segments_ratio * 0.3)  # Between 0.7 and 1.0
    
    reason = f"Segment translation: {segments_translated}/{len(path_segments)} segments"
    
    logger.debug(f"Segment match: {original_url} → {target_url} ({confidence})")
    return target_url, confidence, reason 
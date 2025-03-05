from typing import Dict, Tuple, List, Optional, Any
import logging
import re

logger = logging.getLogger(__name__)

def match_by_language(
    parsed_url: Dict[str, Any],
    domain_mappings: Dict[str, str],
    language_config: Dict[str, Any]
) -> Optional[Tuple[str, float, str]]:
    """Match URLs based on language codes and domain mappings.
    
    Args:
        parsed_url: Parsed URL components
        domain_mappings: Configuration for domain mappings
        language_config: Configuration for language handling
        
    Returns:
        Tuple of (target_url, confidence_score, reason) or None if no match
    """
    original_url = parsed_url['original_url']
    domain = parsed_url['domain']
    subdomain = parsed_url['subdomain']
    path = parsed_url['path']
    language_code = parsed_url['language_code']
    
    # No language code detected
    if not language_code:
        return None
        
    # Check if this domain has a mapping
    if domain not in domain_mappings.get('domains', {}):
        return None
    
    target_domain = domain_mappings['domains'].get(domain)
    
    # Get language mapping configuration
    lang_mappings = language_config.get('mappings', {})
    default_target_lang = language_config.get('default_target', 'en')
    
    # Map source language to target language
    target_lang = lang_mappings.get(language_code, default_target_lang)
    
    # Determine target URL structure based on config
    target_url_structure = language_config.get('url_structures', {}).get(target_domain, 'path')
    
    # Get path without language code if it's in the path
    path_without_lang = re.sub(r'^/[a-z]{2}(-[a-z]{2})?(\/|$)', '/', path)
    
    # Construct target URL based on structure preference
    if target_url_structure == 'subdomain':
        # Language in subdomain: en.example.com
        target_url = f"https://{target_lang}.{target_domain}{path_without_lang}"
        
    elif target_url_structure == 'path':
        # Language in path: example.com/en/
        target_url = f"https://{target_domain}/{target_lang}{path_without_lang}"
        
    else:
        # Default structure
        target_url = f"https://{target_domain}{path_without_lang}"
    
    confidence = 0.85  # High confidence for language-based matching
    reason = f"Language-based mapping: {language_code} → {target_lang} on {target_domain}"
    
    logger.debug(f"Language match: {original_url} → {target_url} ({confidence})")
    return target_url, confidence, reason 
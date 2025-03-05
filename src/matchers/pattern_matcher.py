import re
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

def match_by_pattern(
    parsed_url: Dict[str, Any],
    domain_mappings: Dict[str, Any]
) -> Optional[Tuple[str, float, str]]:
    """
    Match URLs based on regex patterns defined in the domain mappings.
    
    Args:
        parsed_url: Parsed URL components
        domain_mappings: Configuration for domain mappings
        
    Returns:
        Tuple of (target_url, confidence_score, reason) or None if no match
    """
    domain = parsed_url['domain']
    path = parsed_url['path']
    original_url = parsed_url['original_url']
    
    # Get patterns from domain mappings
    patterns = domain_mappings.get('patterns', [])
    
    for pattern_config in patterns:
        source_pattern = pattern_config.get('source_pattern')
        target_pattern = pattern_config.get('target_pattern')
        applicable_domains = pattern_config.get('domains', [])
        
        # Skip if this pattern is not applicable for this domain
        if applicable_domains and domain not in applicable_domains:
            continue
            
        # Try to match the pattern
        match = re.match(source_pattern, path)
        if match:
            # Apply the target pattern with captured groups
            try:
                target_path = re.sub(source_pattern, target_pattern, path)
                
                # Construct the target URL
                target_domain = domain_mappings.get('domains', {}).get(domain, domain)
                target_url = f"https://{target_domain}{target_path}"
                
                confidence = 0.9  # High confidence for pattern matches
                reason = f"Pattern match: {source_pattern} → {target_pattern}"
                
                logger.debug(f"Pattern match: {original_url} → {target_url} ({confidence})")
                return target_url, confidence, reason
                
            except Exception as e:
                logger.error(f"Error applying pattern {source_pattern} to {path}: {str(e)}")
    
    # No match found
    return None 
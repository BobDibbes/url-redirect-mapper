from urllib.parse import urlparse, parse_qs, unquote
from typing import Dict, Tuple, List, Optional, Any
import re

def parse_url(url: str) -> Optional[Dict[str, Any]]:
    """Parse a URL into its components with additional metadata.
    
    Args:
        url: The URL to parse
        
    Returns:
        Dictionary containing URL components and metadata
    """
    try:
        # Normalize the URL
        url = normalize_url(url)
        
        # Parse with urllib
        parsed = urlparse(url)
        
        # Extract components
        scheme = parsed.scheme
        netloc = parsed.netloc
        path = parsed.path
        query = parse_qs(parsed.query)
        fragment = parsed.fragment
        
        # Split domain parts
        domain_parts = netloc.split('.')
        
        # Handle subdomains
        if len(domain_parts) > 2:
            subdomain = '.'.join(domain_parts[:-2])
            domain = '.'.join(domain_parts[-2:])
        else:
            subdomain = ''
            domain = netloc
            
        # Extract language code from subdomain or path
        lang_code = extract_language_code(subdomain, path)
        
        # Split path into segments
        path_segments = [seg for seg in path.split('/') if seg]
        
        return {
            'original_url': url,
            'scheme': scheme,
            'netloc': netloc,
            'domain': domain,
            'subdomain': subdomain,
            'path': path,
            'query': query,
            'fragment': fragment,
            'path_segments': path_segments,
            'language_code': lang_code
        }
    except Exception as e:
        return None

def normalize_url(url: str) -> str:
    """Normalize a URL by ensuring scheme and decoding.
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL
    """
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    # Decode URL-encoded characters
    url = unquote(url)
    
    # Remove trailing slash if present (except for domain root)
    if url.endswith('/') and url.count('/') > 3:
        url = url[:-1]
        
    return url

def extract_language_code(subdomain: str, path: str) -> Optional[str]:
    """Extract language code from subdomain or path.
    
    Args:
        subdomain: The subdomain part of the URL
        path: The path part of the URL
        
    Returns:
        Language code if found, otherwise None
    """
    # Check for language code in subdomain (e.g., en.example.com)
    if subdomain and len(subdomain) in (2, 5):  # 2 for 'en', 5 for 'en-us'
        if re.match(r'^[a-z]{2}(-[a-z]{2})?$', subdomain, re.IGNORECASE):
            return subdomain.lower()
    
    # Check for language code in path (e.g., example.com/en/)
    if path and len(path) >= 3:
        match = re.match(r'^/([a-z]{2}(-[a-z]{2})?)(\/|$)', path, re.IGNORECASE)
        if match:
            return match.group(1).lower()
    
    return None

def get_path_similarity(path1: str, path2: str) -> float:
    """Calculate similarity between two URL paths.
    
    Args:
        path1: First path
        path2: Second path
        
    Returns:
        Similarity score between 0 and 1
    """
    segments1 = [s for s in path1.split('/') if s]
    segments2 = [s for s in path2.split('/') if s]
    
    # If both paths are empty, they're identical
    if not segments1 and not segments2:
        return 1.0
        
    # If one path is empty but the other isn't, they're less similar
    if not segments1 or not segments2:
        return 0.0
    
    # Compare path lengths
    max_segments = max(len(segments1), len(segments2))
    min_segments = min(len(segments1), len(segments2))
    
    # Check how many segments match in order
    matching_segments = 0
    for i in range(min_segments):
        if segments1[i].lower() == segments2[i].lower():
            matching_segments += 1
        else:
            # More penalty for mismatches early in the path
            break
    
    # Calculate similarity score
    return matching_segments / max_segments 
import os
import pandas as pd
from urllib.parse import urlparse, parse_qs
import json
import logging
from typing import Dict, List, Tuple, Optional, Any

from utils.url_parser import parse_url, normalize_url
from utils.confidence_calculator import calculate_confidence
from utils.export import export_to_csv, export_to_htaccess
from matchers.pattern_matcher import match_by_pattern
from matchers.fuzzy_matcher import fuzzy_match
from matchers.segment_matcher import match_by_segment
from matchers.language_matcher import match_by_language

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RedirectMapper:
    """Main class for handling URL redirects with special support for multilingual sites."""
    
    def __init__(self, config_dir: str = "config"):
        """Initialize the RedirectMapper with configurations.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = config_dir
        self.domain_mappings = self._load_config('domains.json')
        self.language_config = self._load_config('languages.json')
        self.dictionaries = self._load_dictionaries()
        logger.info("RedirectMapper initialized with configurations")
    
    def _load_config(self, filename: str) -> Dict:
        """Load a configuration file from the config directory."""
        try:
            with open(os.path.join(self.config_dir, filename), 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Configuration file {filename} not found. Using empty config.")
            return {}
    
    def _load_dictionaries(self) -> Dict[str, Dict[str, str]]:
        """Load all language-specific dictionaries."""
        dictionaries = {}
        dict_dir = os.path.join(self.config_dir, "dictionaries")
        
        if not os.path.exists(dict_dir):
            logger.warning(f"Dictionary directory not found at {dict_dir}")
            return dictionaries
            
        for file in os.listdir(dict_dir):
            if file.endswith('.json'):
                lang_pair = file.split('.')[0]  # e.g., fr_en
                with open(os.path.join(dict_dir, file), 'r', encoding='utf-8') as f:
                    dictionaries[lang_pair] = json.load(f)
        
        return dictionaries
    
    def load_data(self, input_file: str, source_col: str = "source_url", 
                 target_col: Optional[str] = None, **kwargs) -> pd.DataFrame:
        """Load URL data from various file formats.
        
        Args:
            input_file: Path to the input file (CSV, Excel, etc)
            source_col: Column name for source URLs
            target_col: Optional column name for target URLs (for training or verification)
            **kwargs: Additional arguments to pass to pandas read functions
            
        Returns:
            DataFrame with loaded data
        """
        file_ext = os.path.splitext(input_file)[1].lower()
        
        try:
            if file_ext == '.csv':
                df = pd.read_csv(input_file, **kwargs)
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(input_file, **kwargs)
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
                
            # Validate required columns
            if source_col not in df.columns:
                raise ValueError(f"Source column '{source_col}' not found in the input file")
                
            # If target column is specified but not present, add an empty one
            if target_col and target_col not in df.columns:
                df[target_col] = None
                
            # Add columns for results if they don't exist
            if 'suggested_target' not in df.columns:
                df['suggested_target'] = None
            if 'confidence_score' not in df.columns:
                df['confidence_score'] = 0.0
            if 'matching_reason' not in df.columns:
                df['matching_reason'] = None
                
            logger.info(f"Successfully loaded {len(df)} URLs from {input_file}")
            return df
            
        except Exception as e:
            logger.error(f"Error loading data from {input_file}: {str(e)}")
            raise
    
    def process_urls(self, df: pd.DataFrame, source_col: str = "source_url",
                    target_col: str = "suggested_target", 
                    confidence_threshold: float = 0.0) -> pd.DataFrame:
        """Process URLs and generate redirect mappings.
        
        Args:
            df: DataFrame containing URLs to process
            source_col: Column name for source URLs
            target_col: Column name for target URLs
            confidence_threshold: Minimum confidence score to include a mapping
            
        Returns:
            DataFrame with processed mappings
        """
        results = []
        
        for idx, row in df.iterrows():
            source_url = row[source_col]
            
            if not source_url or pd.isna(source_url):
                continue
                
            # Parse the URL to get components
            parsed_url = parse_url(source_url)
            if not parsed_url:
                logger.warning(f"Could not parse URL: {source_url}")
                continue
            
            # Try different matching strategies
            matches = []
            
            # 1. Try domain and language-based matching
            domain_match = match_by_language(
                parsed_url, 
                self.domain_mappings, 
                self.language_config
            )
            if domain_match:
                matches.append(domain_match)
            
            # 2. Try pattern-based matching
            pattern_match = match_by_pattern(parsed_url, self.domain_mappings)
            if pattern_match:
                matches.append(pattern_match)
            
            # 3. Try segment-based matching using dictionaries
            segment_match = match_by_segment(
                parsed_url, 
                self.dictionaries, 
                self.domain_mappings
            )
            if segment_match:
                matches.append(segment_match)
            
            # 4. Try fuzzy matching if other methods didn't yield high confidence
            if not matches or max(m[1] for m in matches) < 0.8:
                fuzzy = fuzzy_match(parsed_url, self.domain_mappings)
                if fuzzy:
                    matches.append(fuzzy)
            
            # Choose the best match based on confidence score
            if matches:
                matches.sort(key=lambda x: x[1], reverse=True)
                best_match = matches[0]
                target_url, confidence, reason = best_match
                
                if confidence >= confidence_threshold:
                    df.at[idx, target_col] = target_url
                    df.at[idx, 'confidence_score'] = confidence
                    df.at[idx, 'matching_reason'] = reason
            
        logger.info(f"Processed {len(df)} URLs with confidence threshold {confidence_threshold}")
        return df
    
    def export_results(self, df: pd.DataFrame, output_file: str,
                      format_type: str = 'csv') -> None:
        """Export the mapping results to the specified format.
        
        Args:
            df: DataFrame with mapping results
            output_file: Path to the output file
            format_type: Format type ('csv', 'htaccess', 'nginx', etc.)
        """
        try:
            if format_type.lower() == 'csv':
                export_to_csv(df, output_file)
            elif format_type.lower() == 'htaccess':
                export_to_htaccess(df, output_file)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
                
            logger.info(f"Successfully exported results to {output_file} in {format_type} format")
            
        except Exception as e:
            logger.error(f"Error exporting results: {str(e)}")
            raise 
import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class RedirectConfig:
    """Configuration manager for URL redirection mappings."""
    
    def __init__(self, config_dir: str = "config"):
        """Initialize configuration from files.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = config_dir
        self.domains = {}
        self.languages = {}
        self.dictionaries = {}
        
        self._load_configs()
    
    def _load_configs(self) -> None:
        """Load all configuration files."""
        self._load_domains()
        self._load_languages()
        self._load_dictionaries()
    
    def _load_domains(self) -> None:
        """Load domain mapping configuration."""
        try:
            domain_file = os.path.join(self.config_dir, "domains.json")
            if os.path.exists(domain_file):
                with open(domain_file, 'r', encoding='utf-8') as f:
                    self.domains = json.load(f)
                logger.info(f"Loaded domain mappings: {len(self.domains.get('domains', {}))} domains")
            else:
                self._create_default_domain_config()
        except Exception as e:
            logger.error(f"Error loading domain config: {str(e)}")
            self._create_default_domain_config()
    
    def _load_languages(self) -> None:
        """Load language configuration."""
        try:
            lang_file = os.path.join(self.config_dir, "languages.json")
            if os.path.exists(lang_file):
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.languages = json.load(f)
                logger.info(f"Loaded language config with {len(self.languages.get('mappings', {}))} mappings")
            else:
                self._create_default_language_config()
        except Exception as e:
            logger.error(f"Error loading language config: {str(e)}")
            self._create_default_language_config()
    
    def _load_dictionaries(self) -> None:
        """Load language-specific dictionaries."""
        dict_dir = os.path.join(self.config_dir, "dictionaries")
        
        if not os.path.exists(dict_dir):
            os.makedirs(dict_dir, exist_ok=True)
            self._create_sample_dictionary()
            return
            
        for file in os.listdir(dict_dir):
            if file.endswith('.json'):
                lang_pair = file.split('.')[0]  # e.g., fr_en
                try:
                    with open(os.path.join(dict_dir, file), 'r', encoding='utf-8') as f:
                        self.dictionaries[lang_pair] = json.load(f)
                    logger.info(f"Loaded dictionary for {lang_pair} with {len(self.dictionaries[lang_pair])} entries")
                except Exception as e:
                    logger.error(f"Error loading dictionary {file}: {str(e)}")
    
    def _create_default_domain_config(self) -> None:
        """Create default domain mapping configuration."""
        self.domains = {
            "domains": {
                "example.com": "example.org",
                "old-site.com": "new-site.com"
            },
            "patterns": [
                {
                    "source_pattern": r"^/blog/(\d+)/(\d+)/(.+)$",
                    "target_pattern": r"/articles/\3",
                    "domains": ["example.com", "old-site.com"]
                },
                {
                    "source_pattern": r"^/products/(.+)$",
                    "target_pattern": r"/shop/\1",
                    "domains": ["example.com"]
                }
            ]
        }
        
        # Save the default config
        os.makedirs(self.config_dir, exist_ok=True)
        with open(os.path.join(self.config_dir, "domains.json"), 'w', encoding='utf-8') as f:
            json.dump(self.domains, f, indent=4)
        
        logger.info("Created default domain configuration")
    
    def _create_default_language_config(self) -> None:
        """Create default language configuration."""
        self.languages = {
            "mappings": {
                "fr": "en",
                "fr-fr": "en-us",
                "fr-ca": "en-ca",
                "nl": "en",
                "nl-nl": "en-gb",
                "de": "en",
                "es": "en"
            },
            "default_target": "en",
            "url_structures": {
                "example.org": "path",
                "new-site.com": "subdomain"
            }
        }
        
        # Save the default config
        os.makedirs(self.config_dir, exist_ok=True)
        with open(os.path.join(self.config_dir, "languages.json"), 'w', encoding='utf-8') as f:
            json.dump(self.languages, f, indent=4)
        
        logger.info("Created default language configuration")
    
    def _create_sample_dictionary(self) -> None:
        """Create a sample dictionary for French to English."""
        sample_dict = {
            "nouvelles": "news",
            "entreprises": "business",
            "produits": "products",
            "a-propos": "about",
            "contactez-nous": "contact-us",
            "emplois": "jobs",
            "recherche": "search"
        }
        
        dict_dir = os.path.join(self.config_dir, "dictionaries")
        os.makedirs(dict_dir, exist_ok=True)
        
        with open(os.path.join(dict_dir, "fr_en.json"), 'w', encoding='utf-8') as f:
            json.dump(sample_dict, f, indent=4)
        
        self.dictionaries["fr_en"] = sample_dict
        logger.info("Created sample French to English dictionary") 
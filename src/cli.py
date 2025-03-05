import argparse
import logging
import os
import sys
import pandas as pd
from typing import List, Optional

from .redirect_mapper import RedirectMapper
from .config import RedirectConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='URL Redirect Mapping Tool for multilingual websites'
    )
    
    parser.add_argument(
        'input_file',
        help='Input file containing URLs to process (CSV, Excel)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file path',
        default='redirects_output.csv'
    )
    
    parser.add_argument(
        '-f', '--format',
        help='Output format (csv, htaccess, nginx)',
        choices=['csv', 'htaccess', 'nginx'],
        default='csv'
    )
    
    parser.add_argument(
        '-s', '--source-col',
        help='Column name for source URLs',
        default='source_url'
    )
    
    parser.add_argument(
        '-t', '--target-col',
        help='Column name for target URLs (if verifying existing mappings)',
        default=None
    )
    
    parser.add_argument(
        '-c', '--config-dir',
        help='Directory containing configuration files',
        default='config'
    )
    
    parser.add_argument(
        '--threshold',
        help='Confidence threshold (0.0-1.0)',
        type=float,
        default=0.5
    )
    
    parser.add_argument(
        '-v', '--verbose',
        help='Enable verbose logging',
        action='store_true'
    )
    
    parser.add_argument(
        '--init-config',
        help='Initialize config files with defaults',
        action='store_true'
    )
    
    return parser.parse_args(args)

def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI application."""
    args = parse_args(args)
    
    # Set log level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize configuration
    if args.init_config:
        logger.info(f"Initializing configuration in {args.config_dir}")
        config = RedirectConfig(args.config_dir)
        return 0
    
    # Validate input file
    if not os.path.exists(args.input_file):
        logger.error(f"Input file does not exist: {args.input_file}")
        return 1
    
    try:
        # Initialize the redirect mapper
        mapper = RedirectMapper(args.config_dir)
        
        # Load data
        logger.info(f"Loading data from {args.input_file}")
        df = mapper.load_data(
            args.input_file,
            source_col=args.source_col,
            target_col=args.target_col
        )
        
        # Process URLs
        logger.info(f"Processing URLs with confidence threshold {args.threshold}")
        result_df = mapper.process_urls(
            df,
            source_col=args.source_col,
            confidence_threshold=args.threshold
        )
        
        # Export results
        logger.info(f"Exporting results to {args.output} in {args.format} format")
        mapper.export_results(result_df, args.output, args.format)
        
        logger.info("URL redirect mapping completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error processing URLs: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
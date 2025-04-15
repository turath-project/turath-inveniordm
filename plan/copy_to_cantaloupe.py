#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to copy PDF files from InvenioRDM to Cantaloupe for IIIF serving.

This script demonstrates how to:
1. Extract the file path from an InvenioRDM record
2. Copy the file to Cantaloupe's directory structure
3. Verify the file is accessible by Cantaloupe
"""

import os
import sys
import shutil
import logging
import argparse
import requests
from urllib.parse import quote
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cantaloupe-file-sync')

# Default paths - should be configurable
CANTALOUPE_DATA_DIR = "/opt/cantaloupe/images"
CANTALOUPE_URL = "https://localhost:8182"

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Copy PDF files from InvenioRDM to Cantaloupe")
    parser.add_argument('--record-id', required=True, help='InvenioRDM record ID')
    parser.add_argument('--file-path', required=True, help='Path to the PDF file')
    parser.add_argument('--filename', help='Filename to use in Cantaloupe (defaults to basename of file-path)')
    parser.add_argument('--cantaloupe-dir', default=CANTALOUPE_DATA_DIR, 
                       help=f'Cantaloupe data directory (default: {CANTALOUPE_DATA_DIR})')
    parser.add_argument('--cantaloupe-url', default=CANTALOUPE_URL,
                       help=f'Cantaloupe server URL (default: {CANTALOUPE_URL})')
    parser.add_argument('--verify-ssl', action='store_true', help='Verify SSL certificates for Cantaloupe requests')
    parser.add_argument('--test', action='store_true', help='Test Cantaloupe access after copying')
    return parser.parse_args()

def copy_pdf_to_cantaloupe(record_id, source_path, cantaloupe_dir, filename=None):
    """
    Copy a PDF file to the Cantaloupe directory structure.
    
    Args:
        record_id: InvenioRDM record ID
        source_path: Path to the source PDF file
        cantaloupe_dir: Base directory for Cantaloupe
        filename: Optional filename to use (defaults to basename of source_path)
    
    Returns:
        Tuple of (success, target_path)
    """
    # Verify source file exists
    if not os.path.exists(source_path):
        logger.error(f"Source file does not exist: {source_path}")
        return False, None
    
    # Get filename if not provided
    if not filename:
        filename = os.path.basename(source_path)
    
    # Create target directory structure
    # Use a directory structure like: {cantaloupe_dir}/private/{record_id}/
    target_dir = os.path.join(cantaloupe_dir, "private", record_id)
    target_path = os.path.join(target_dir, filename)
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)
        logger.info(f"Created directory: {target_dir}")
        
        # Copy the file
        shutil.copy2(source_path, target_path)
        logger.info(f"Copied file from {source_path} to {target_path}")
        
        return True, target_path
    except Exception as e:
        logger.error(f"Error copying file to Cantaloupe: {str(e)}")
        return False, None

def test_cantaloupe_access(record_id, filename, cantaloupe_url, verify_ssl=False):
    """
    Test if Cantaloupe can access the PDF file.
    
    Args:
        record_id: InvenioRDM record ID
        filename: Filename in Cantaloupe
        cantaloupe_url: Cantaloupe server URL
        verify_ssl: Whether to verify SSL certificates
    
    Returns:
        Boolean indicating success
    """
    # Construct the Cantaloupe identifier (URL-encoded path)
    identifier = f"private%2F{record_id}%2F{filename}"
    
    # Test the info.json endpoint
    info_url = f"{cantaloupe_url}/iiif/3/{identifier}/info.json"
    
    try:
        logger.info(f"Testing Cantaloupe access: {info_url}")
        response = requests.get(info_url, verify=verify_ssl, timeout=10)
        
        if response.status_code == 200:
            logger.info("✓ Successfully retrieved info.json from Cantaloupe")
            
            # For PDF files, test page access
            image_url = f"{cantaloupe_url}/iiif/3/{identifier}/full/,200/0/default.jpg?page=1"
            logger.info(f"Testing page access: {image_url}")
            
            img_response = requests.get(image_url, verify=verify_ssl, timeout=10)
            if img_response.status_code == 200:
                logger.info("✓ Successfully retrieved page image from Cantaloupe")
                return True
            else:
                logger.error(f"✗ Failed to retrieve page image. Status: {img_response.status_code}")
                return False
        else:
            logger.error(f"✗ Failed to retrieve info.json. Status: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"✗ Error testing Cantaloupe access: {str(e)}")
        return False

def get_cantaloupe_url(record_id, filename, cantaloupe_url):
    """
    Generate the proper Cantaloupe URL for a PDF file.
    
    Args:
        record_id: InvenioRDM record ID
        filename: Filename in Cantaloupe
        cantaloupe_url: Cantaloupe server URL
    
    Returns:
        URL template string
    """
    # URL-encode the path components
    identifier = f"private%2F{record_id}%2F{filename}"
    
    # Base URL for the PDF in Cantaloupe
    base_url = f"{cantaloupe_url}/iiif/3/{identifier}"
    
    # Template for accessing specific pages
    page_url_template = f"{base_url}/full/full/0/default.jpg?page={{page_number}}"
    
    return page_url_template

def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Copy the PDF file to Cantaloupe
    filename = args.filename or os.path.basename(args.file_path)
    success, target_path = copy_pdf_to_cantaloupe(
        args.record_id, 
        args.file_path, 
        args.cantaloupe_dir,
        filename
    )
    
    if not success:
        logger.error("Failed to copy PDF to Cantaloupe")
        sys.exit(1)
    
    # Get the Cantaloupe URL template
    url_template = get_cantaloupe_url(args.record_id, filename, args.cantaloupe_url)
    logger.info(f"Cantaloupe URL template: {url_template}")
    
    # Test Cantaloupe access if requested
    if args.test:
        if test_cantaloupe_access(args.record_id, filename, args.cantaloupe_url, args.verify_ssl):
            logger.info("✓ Cantaloupe access test passed")
        else:
            logger.error("✗ Cantaloupe access test failed")
            sys.exit(1)
    
    # Output successful result
    print(f"""
PDF File Successfully Copied to Cantaloupe
------------------------------------------
Record ID: {args.record_id}
Source File: {args.file_path}
Target Path: {target_path}
URL Template: {url_template}

To access page 1:
{url_template.format(page_number=1)}
""")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
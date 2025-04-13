#!/usr/bin/env python
"""
Test IIIF integration for PDF files.

This script:
1. Tests the connection to the IIIF server
2. Tests manifest generation for PDF files
3. Tests viewing individual pages of a PDF

Usage:
    python scripts/AlA/test_iiif_integration.py [--server-url=URL] [--record-id=ID] [--filename=NAME]
"""

import os
import sys
import json
import requests
import logging
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("test-iiif")

# Default values
server_url = "http://127.0.0.1:5002"  # Default to local test server
record_id = "202"  # Default record ID
filename = "test.pdf"  # Default filename

# Parse command line arguments
for arg in sys.argv:
    if arg.startswith('--server-url='):
        server_url = arg.split('=', 1)[1]
    elif arg.startswith('--record-id='):
        record_id = arg.split('=', 1)[1]
    elif arg.startswith('--filename='):
        filename = arg.split('=', 1)[1]

def test_server_connection():
    """Test connection to the IIIF server."""
    logger.info(f"Testing connection to server: {server_url}")
    
    try:
        response = requests.get(server_url)
        if response.status_code == 200:
            logger.info("✅ Successfully connected to server")
            return True
        else:
            logger.error(f"❌ Error connecting to server: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Error connecting to server: {e}")
        return False

def test_record_access():
    """Test access to the record API."""
    url = urljoin(server_url, f"/api/records/{record_id}")
    logger.info(f"Testing record access: {url}")
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            logger.info("✅ Successfully accessed record API")
            try:
                record_data = response.json()
                logger.info(f"Record title: {record_data.get('metadata', {}).get('title', 'Unknown')}")
                return record_data
            except Exception as e:
                logger.error(f"❌ Error parsing record data: {e}")
                return None
        else:
            logger.error(f"❌ Error accessing record: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"❌ Error accessing record: {e}")
        return None

def test_manifest_generation():
    """Test IIIF manifest generation for a PDF file."""
    url = urljoin(server_url, f"/api/iiif/manifest/{record_id}")
    logger.info(f"Testing manifest generation: {url}")
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            logger.info("✅ Successfully generated manifest")
            try:
                manifest = response.json()
                
                # Check for required manifest fields
                required_fields = ["@context", "@id", "@type", "sequences"]
                missing_fields = [field for field in required_fields if field not in manifest]
                
                if missing_fields:
                    logger.warning(f"⚠️ Manifest missing required fields: {', '.join(missing_fields)}")
                
                # Get number of canvases (pages)
                if "sequences" in manifest and manifest["sequences"]:
                    canvases = manifest["sequences"][0].get("canvases", [])
                    logger.info(f"Manifest contains {len(canvases)} canvas(es) (pages)")
                else:
                    logger.warning("⚠️ Manifest has no canvases/pages")
                
                return manifest
            except Exception as e:
                logger.error(f"❌ Error parsing manifest: {e}")
                return None
        else:
            logger.error(f"❌ Error generating manifest: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"❌ Error generating manifest: {e}")
        return None

def test_pdf_image_access(page=1):
    """Test accessing a PDF page as an image."""
    url = urljoin(server_url, f"/api/iiif/image/{record_id}/{filename}")
    params = {
        "page": page,
        "region": "full",
        "size": "full"
    }
    
    logger.info(f"Testing PDF image access for page {page}: {url}")
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            logger.info(f"✅ Successfully accessed page {page} as image")
            content_type = response.headers.get('Content-Type', 'unknown')
            logger.info(f"Image content type: {content_type}")
            return True
        else:
            logger.error(f"❌ Error accessing PDF page {page}: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Error accessing PDF page {page}: {e}")
        return False

def test_pdf_direct_access():
    """Test direct access to the PDF file."""
    url = urljoin(server_url, f"/files/{filename}")
    logger.info(f"Testing direct PDF access: {url}")
    
    try:
        # Use HEAD request to avoid downloading the entire file
        response = requests.head(url)
        if response.status_code == 200:
            logger.info("✅ Successfully accessed PDF file directly")
            content_type = response.headers.get('Content-Type', 'unknown')
            logger.info(f"PDF content type: {content_type}")
            return True
        else:
            logger.error(f"❌ Error accessing PDF file: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Error accessing PDF file: {e}")
        return False

def main():
    """Main function to run all tests."""
    logger.info("=== IIIF Integration Test ===")
    logger.info(f"Server URL: {server_url}")
    logger.info(f"Record ID: {record_id}")
    logger.info(f"Filename: {filename}")
    
    # Test server connection
    if not test_server_connection():
        logger.error("❌ Server connection test failed - aborting further tests")
        return False
    
    # Test record access
    record_data = test_record_access()
    if not record_data:
        logger.error("❌ Record access test failed - continuing with other tests")
    
    # Test manifest generation
    manifest = test_manifest_generation()
    if not manifest:
        logger.error("❌ Manifest generation test failed - continuing with other tests")
    
    # Test PDF image access for multiple pages
    page_count = 3  # Default to testing 3 pages
    
    # If we have the manifest, get the actual page count
    if manifest and "sequences" in manifest and manifest["sequences"]:
        canvases = manifest["sequences"][0].get("canvases", [])
        if canvases:
            page_count = len(canvases)
    
    # Test each page
    for page in range(1, page_count + 1):
        test_pdf_image_access(page)
    
    # Test direct PDF access
    test_pdf_direct_access()
    
    # Overall results
    logger.info("=== Test Summary ===")
    logger.info("Tests completed. Check the log for any errors.")
    
    return True

if __name__ == "__main__":
    main() 
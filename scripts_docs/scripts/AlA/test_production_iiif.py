#!/usr/bin/env python
"""
Test IIIF integration on the actual production instance.

This script:
1. Tests the connection to the production IIIF server
2. Tests manifest generation for PDF files
3. Tests viewing individual pages of a PDF
4. Tests actual Cantaloupe image server responses

Usage:
    python scripts/AlA/test_production_iiif.py --server-url=https://yourinstance.example.com
"""

import os
import sys
import json
import requests
import logging
from urllib.parse import urljoin, urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("test-production-iiif")

# Default values - using local test server since that's what's running
server_url = "http://127.0.0.1:5002"  # Local test server
record_id = "202"  # Default record ID
filename = "test.pdf"  # Default filename to test

# Parse command line arguments
for arg in sys.argv:
    if arg.startswith('--server-url='):
        server_url = arg.split('=', 1)[1]
    elif arg.startswith('--record-id='):
        record_id = arg.split('=', 1)[1]
    elif arg.startswith('--filename='):
        filename = arg.split('=', 1)[1]

def test_server_connection():
    """Test connection to the production server."""
    logger.info(f"Testing connection to server: {server_url}")
    
    try:
        response = requests.get(server_url, timeout=10)
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
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Successfully accessed record API")
            try:
                record_data = response.json()
                logger.info(f"Record title: {record_data.get('metadata', {}).get('title', 'Unknown')}")
                
                # Extract file information
                files = record_data.get('files', {}).get('entries', [])
                for file in files:
                    logger.info(f"File: {file.get('key')} ({file.get('size')} bytes, {file.get('mimetype')})")
                
                return record_data
            except Exception as e:
                logger.error(f"❌ Error parsing record data: {e}")
                return None
        else:
            logger.error(f"❌ Error accessing record: {response.status_code}")
            logger.error(f"Response: {response.text[:500]}")
            return None
    except Exception as e:
        logger.error(f"❌ Error accessing record: {e}")
        return None

def test_manifest_generation():
    """Test IIIF manifest generation for a PDF file."""
    url = urljoin(server_url, f"/api/iiif/manifest/{record_id}")
    logger.info(f"Testing manifest generation: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Successfully generated manifest")
            try:
                manifest = response.json()
                
                # Check for required manifest fields
                required_fields = ["@context", "@id", "@type", "sequences"]
                missing_fields = [field for field in required_fields if field not in manifest]
                
                if missing_fields:
                    logger.warning(f"⚠️ Manifest missing required fields: {', '.join(missing_fields)}")
                else:
                    logger.info("✅ Manifest contains all required fields")
                
                # Get number of canvases (pages)
                if "sequences" in manifest and manifest["sequences"]:
                    canvases = manifest["sequences"][0].get("canvases", [])
                    logger.info(f"Manifest contains {len(canvases)} canvas(es) (pages)")
                    
                    # Print canvas IDs
                    for i, canvas in enumerate(canvases[:3]):  # Show first 3 canvases
                        logger.info(f"Canvas {i+1} ID: {canvas.get('@id', 'Unknown')}")
                        
                        # Check for images in canvas
                        if "images" in canvas and canvas["images"]:
                            image = canvas["images"][0]
                            resource = image.get("resource", {})
                            image_url = resource.get("@id", "Unknown")
                            logger.info(f"  Image URL: {image_url}")
                        else:
                            logger.warning(f"  ⚠️ Canvas {i+1} has no images")
                else:
                    logger.warning("⚠️ Manifest has no canvases/pages")
                
                return manifest
            except Exception as e:
                logger.error(f"❌ Error parsing manifest: {e}")
                logger.error(f"Response content: {response.text[:500]}")
                return None
        else:
            logger.error(f"❌ Error generating manifest: {response.status_code}")
            logger.error(f"Response: {response.text[:500]}")
            return None
    except Exception as e:
        logger.error(f"❌ Error generating manifest: {e}")
        return None

def test_cantaloupe_server():
    """Test direct access to the Cantaloupe server."""
    # Extract the Cantaloupe server URL from the manifest
    manifest = test_manifest_generation()
    if not manifest:
        logger.error("❌ Cannot test Cantaloupe server without manifest")
        return False
    
    # Try to find an image URL in the manifest
    cantaloupe_url = None
    if "sequences" in manifest and manifest["sequences"]:
        canvases = manifest["sequences"][0].get("canvases", [])
        for canvas in canvases:
            if "images" in canvas and canvas["images"]:
                image = canvas["images"][0]
                resource = image.get("resource", {})
                image_url = resource.get("@id", "")
                if image_url:
                    cantaloupe_url = image_url
                    break
    
    if not cantaloupe_url:
        logger.error("❌ Cannot find Cantaloupe URL in manifest")
        return False
    
    # Parse the URL to get the Cantaloupe base URL
    parsed_url = urlparse(cantaloupe_url)
    cantaloupe_base = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    logger.info(f"Testing Cantaloupe server: {cantaloupe_base}")
    
    try:
        response = requests.get(cantaloupe_base, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Successfully connected to Cantaloupe server")
            return True
        else:
            logger.error(f"❌ Error connecting to Cantaloupe server: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Error connecting to Cantaloupe server: {e}")
        return False

def test_image_access(image_url):
    """Test accessing an image through Cantaloupe."""
    logger.info(f"Testing image access: {image_url}")
    
    try:
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', 'unknown')
            logger.info(f"✅ Successfully accessed image. Content type: {content_type}")
            return True
        else:
            logger.error(f"❌ Error accessing image: {response.status_code}")
            logger.error(f"Response: {response.text[:500]}")
            return False
    except Exception as e:
        logger.error(f"❌ Error accessing image: {e}")
        return False

def test_pdf_access():
    """Test direct access to the PDF file."""
    # For the test server, we can access the PDF directly
    pdf_url = urljoin(server_url, f"/files/{filename}")
    logger.info(f"Testing PDF access: {pdf_url}")
    
    try:
        # Use HEAD request to avoid downloading the entire file
        response = requests.head(pdf_url, timeout=10)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', 'unknown')
            logger.info(f"✅ Successfully accessed PDF. Content type: {content_type}")
            content_length = response.headers.get('Content-Length', 'unknown')
            logger.info(f"  Content length: {content_length} bytes")
            return True
        else:
            logger.error(f"❌ Error accessing PDF: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Error accessing PDF: {e}")
        return False

def test_iiif_configuration():
    """Test IIIF configuration by examining the manifest content."""
    manifest = test_manifest_generation()
    if not manifest:
        logger.error("❌ Cannot test IIIF configuration without manifest")
        return False
    
    logger.info("=== Testing IIIF Configuration ===")
    
    # Check context
    context = manifest.get('@context', '')
    if 'http://iiif.io/api/presentation/' in str(context):
        logger.info(f"✅ Manifest uses IIIF Presentation API context: {context}")
    else:
        logger.warning(f"⚠️ Manifest does not use standard IIIF context: {context}")
    
    # Check if the manifest includes a PDF profile or mimetype
    has_pdf_references = False
    
    # Check sequences and canvases for PDF references
    if "sequences" in manifest and manifest["sequences"]:
        for sequence in manifest["sequences"]:
            for canvas in sequence.get("canvases", []):
                for image in canvas.get("images", []):
                    resource = image.get("resource", {})
                    format = resource.get("format", "")
                    if "pdf" in format.lower():
                        has_pdf_references = True
                        logger.info(f"✅ Found PDF reference in canvas: {format}")
    
    if not has_pdf_references:
        logger.warning("⚠️ No PDF references found in manifest")
    
    # Return if configuration appears to be correct
    return True

def test_individual_page_access():
    """Test accessing individual pages of the PDF."""
    logger.info("=== Testing Individual Page Access ===")
    
    # Test different pages
    for page in range(1, 4):  # Test the first 3 pages
        url = urljoin(server_url, f"/api/iiif/image/{record_id}/{filename}")
        params = {
            "page": page,
            "region": "full",
            "size": "full",
            "rotation": "0",
            "quality": "default",
            "format": "jpg"
        }
        
        logger.info(f"Testing access to page {page}: {url}")
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', 'unknown')
                logger.info(f"✅ Successfully accessed page {page}. Content type: {content_type}")
            else:
                logger.error(f"❌ Error accessing page {page}: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error accessing page {page}: {e}")

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
    
    # Test Cantaloupe server
    test_cantaloupe_server()
    
    # Test image access from manifest
    if manifest and "sequences" in manifest and manifest["sequences"]:
        canvases = manifest["sequences"][0].get("canvases", [])
        for i, canvas in enumerate(canvases[:3]):  # Test first 3 canvases
            if "images" in canvas and canvas["images"]:
                image = canvas["images"][0]
                resource = image.get("resource", {})
                image_url = resource.get("@id", "")
                if image_url:
                    test_image_access(image_url)
    
    # Test individual page access
    test_individual_page_access()
    
    # Test direct PDF access
    test_pdf_access()
    
    # Test IIIF configuration
    test_iiif_configuration()
    
    # Overall results
    logger.info("=== Test Summary ===")
    logger.info("Tests completed. Check the log for any errors.")
    
    return True

if __name__ == "__main__":
    main() 
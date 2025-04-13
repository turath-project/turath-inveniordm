#!/usr/bin/env python
"""
Test script for Cantaloupe IIIF server with PDF.

This script:
1. Tests the Cantaloupe server connection
2. Copies a test PDF to the Cantaloupe directory
3. Requests the IIIF manifest and images from Cantaloupe

Usage:
    python scripts/AlA/cantaloupe_test.py
"""

import os
import sys
import json
import requests
import shutil
import logging
from urllib.parse import quote

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("cantaloupe-test")

# Configuration
CANTALOUPE_URL = "http://localhost:8182"
CANTALOUPE_DATA_DIR = "/opt/cantaloupe/images"  # Use default Cantaloupe directory
RECORD_ID = "202"
FILE_KEY = "test.pdf"

def test_cantaloupe_connection():
    """Test connection to Cantaloupe server."""
    logger.info("=== Testing Cantaloupe Server Connection ===")
    
    try:
        response = requests.get(f"{CANTALOUPE_URL}/iiif/2", timeout=5)
        if response.status_code == 200:
            logger.info(f"✓ Cantaloupe server is responsive at {CANTALOUPE_URL}")
            return True
        else:
            logger.error(f"✗ Cantaloupe server returned status code {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"✗ Error connecting to Cantaloupe server: {e}")
        return False

def copy_pdf_to_cantaloupe():
    """Copy test PDF to Cantaloupe directory."""
    logger.info("=== Copying Test PDF to Cantaloupe ===")
    
    # Check if test PDF exists
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(script_dir, "test.pdf")
    
    if not os.path.exists(pdf_path):
        logger.error(f"✗ Test PDF not found at {pdf_path}")
        return False
    
    logger.info(f"Found test PDF at {pdf_path}")
    
    # Create the destination path - use a path expected by Cantaloupe
    # Typically in Cantaloupe, it follows a structure like: {data_dir}/private/{record_id}/{filename}
    dest_dir = f"{CANTALOUPE_DATA_DIR}/private/{RECORD_ID}"
    dest_path = os.path.join(dest_dir, FILE_KEY)
    
    try:
        # Create directory if it doesn't exist
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
            logger.info(f"Created directory: {dest_dir}")
        
        # Copy the file
        shutil.copy2(pdf_path, dest_path)
        logger.info(f"✓ Copied PDF to {dest_path}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Error copying PDF to Cantaloupe: {e}")
        return False

def test_info_json():
    """Test requesting info.json from Cantaloupe."""
    logger.info("=== Testing info.json Request ===")
    
    # Construct the Cantaloupe identifier
    identifier = f"private%2F{RECORD_ID}%2F{FILE_KEY}"
    url = f"{CANTALOUPE_URL}/iiif/2/{identifier}/info.json"
    
    logger.info(f"Requesting: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            info = response.json()
            logger.info(f"✓ Successfully retrieved info.json")
            
            # Check if it has the expected structure
            if 'width' in info and 'height' in info:
                logger.info(f"✓ Got dimensions: {info['width']} x {info['height']}")
            
            # For PDFs, check if it has page information
            if 'sizes' in info:
                logger.info(f"✓ PDF has {len(info['sizes'])} pages/sizes")
            
            return info
        else:
            logger.error(f"✗ info.json request failed with status code {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
    except Exception as e:
        logger.error(f"✗ Error requesting info.json: {e}")
        return None

def test_image_request():
    """Test requesting an image from Cantaloupe."""
    logger.info("=== Testing Image Request ===")
    
    # Construct the Cantaloupe identifier
    identifier = f"private%2F{RECORD_ID}%2F{FILE_KEY}"
    
    # For PDFs, we might need to specify a page
    page_param = "?page=1"
    
    # Construct the IIIF URL
    url = f"{CANTALOUPE_URL}/iiif/2/{identifier}/full/!200,200/0/default.jpg{page_param}"
    
    logger.info(f"Requesting: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            logger.info(f"✓ Successfully retrieved image, Content-Type: {content_type}")
            
            # Save the image to verify it's valid
            image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output.jpg")
            with open(image_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"✓ Saved image to {image_path}")
            
            return True
        else:
            logger.error(f"✗ Image request failed with status code {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"✗ Error requesting image: {e}")
        return False

def generate_cantaloupe_manifest():
    """Generate a simple IIIF manifest for the PDF test file."""
    logger.info("=== Generating IIIF Manifest ===")
    
    # First get the info.json to determine page count
    info = test_info_json()
    if not info:
        logger.error("✗ Cannot generate manifest without info.json")
        return None
    
    # Determine number of pages
    num_pages = 1
    if 'sizes' in info:
        num_pages = len(info['sizes'])
    
    logger.info(f"Generating manifest with {num_pages} pages")
    
    # Construct the Cantaloupe identifier
    identifier = f"private%2F{RECORD_ID}%2F{FILE_KEY}"
    
    # Create the manifest
    manifest = {
        "@context": "http://iiif.io/api/presentation/2/context.json",
        "@type": "sc:Manifest",
        "@id": f"{CANTALOUPE_URL}/iiif/2/{identifier}/manifest.json",
        "label": FILE_KEY,
        "metadata": [
            {
                "label": "Record ID",
                "value": RECORD_ID
            },
            {
                "label": "Filename",
                "value": FILE_KEY
            }
        ],
        "sequences": [
            {
                "@type": "sc:Sequence",
                "canvases": []
            }
        ]
    }
    
    # Create a canvas for each page
    for page in range(1, num_pages + 1):
        canvas = {
            "@type": "sc:Canvas",
            "@id": f"{CANTALOUPE_URL}/iiif/2/{identifier}/canvas/p{page}",
            "label": f"Page {page}",
            "width": info.get('width', 612),
            "height": info.get('height', 792),
            "images": [
                {
                    "@type": "oa:Annotation",
                    "motivation": "sc:painting",
                    "resource": {
                        "@id": f"{CANTALOUPE_URL}/iiif/2/{identifier}/full/!1000,1000/0/default.jpg?page={page}",
                        "@type": "dctypes:Image",
                        "format": "image/jpeg",
                        "width": info.get('width', 612),
                        "height": info.get('height', 792),
                        "service": {
                            "@context": "http://iiif.io/api/image/2/context.json",
                            "@id": f"{CANTALOUPE_URL}/iiif/2/{identifier}?page={page}",
                            "profile": "http://iiif.io/api/image/2/level2.json"
                        }
                    },
                    "on": f"{CANTALOUPE_URL}/iiif/2/{identifier}/canvas/p{page}"
                }
            ]
        }
        
        manifest['sequences'][0]['canvases'].append(canvas)
    
    # Save the manifest to a file
    manifest_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_manifest.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    logger.info(f"✓ Generated manifest with {num_pages} pages")
    logger.info(f"✓ Saved manifest to {manifest_path}")
    
    return manifest

def main():
    """Main function."""
    logger.info("=== Cantaloupe PDF Test ===")
    
    # Test Cantaloupe connection
    if not test_cantaloupe_connection():
        logger.error("Cantaloupe server is not responsive. Aborting test.")
        return False
    
    # Copy PDF to Cantaloupe
    if not copy_pdf_to_cantaloupe():
        logger.warning("Failed to copy PDF to Cantaloupe. Continuing anyway...")
    
    # Test info.json
    test_info_json()
    
    # Test image request
    test_image_request()
    
    # Generate manifest
    generate_cantaloupe_manifest()
    
    logger.info("=== Test Complete ===")
    logger.info(f"You can access the IIIF image at: {CANTALOUPE_URL}/iiif/2/private%2F{RECORD_ID}%2F{FILE_KEY}/full/!200,200/0/default.jpg?page=1")
    logger.info(f"You can view the manifest at: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_manifest.json')}")
    
    return True

if __name__ == "__main__":
    main() 
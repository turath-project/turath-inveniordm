#!/usr/bin/env python
"""
Test PDF manifest generation for a specific record and file.
This script helps diagnose issues with PDF manifest generation.
"""

import os
import sys
import json
import argparse
import requests
import logging
from urllib.parse import quote
from flask import current_app
from invenio_app.factory import create_app

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_pdf_manifest")

class CantaloupeTestProxy:
    """Test class for Cantaloupe proxy."""
    
    def __init__(self, server_url=None):
        """Initialize with an optional server URL."""
        self.app = create_app()
        with self.app.app_context():
            self.server_url = server_url or current_app.config.get(
                "RDM_IIIF_SERVER_URL", "http://localhost:8182"
            )
            self.base_path = current_app.config.get(
                "RDM_IIIF_BASE_PATH", "/iiif/2"
            )
        
        logger.info(f"Initialized CantaloupeProxy with server_url={self.server_url}")
    
    def _is_pdf(self, filename):
        """Check if a file is a PDF based on extension."""
        return filename.lower().endswith('.pdf')
    
    def _get_file_path(self, record_id, filename):
        """Get the file path for a record file."""
        if self._is_pdf(filename):
            # Path structure for PDFs in Cantaloupe
            return f"private/{record_id}/{filename}"
        else:
            # Legacy PTIF structure 
            recid_str = str(record_id)
            ch1 = recid_str[0:2].ljust(2, '_')
            ch2 = recid_str[2:4].ljust(2, '_')
            tail = recid_str[4:].ljust(1, '_')
            
            # Use .ptif extension for non-PDF image files
            base_name = os.path.splitext(filename)[0]
            return f"{ch1}/{ch2}/{tail}/{base_name}.ptif"
    
    def get_pdf_info(self, record_id, filename):
        """Get PDF info from Cantaloupe."""
        if not self._is_pdf(filename):
            logger.error(f"File {filename} is not a PDF")
            return None
        
        # Get the file path
        file_path = self._get_file_path(record_id, filename)
        
        # Encode the path with %2F for slashes as required by Cantaloupe
        encoded_path = file_path.replace("/", "%2F")
        
        # Construct the Cantaloupe info.json URL
        info_url = f"{self.server_url}{self.base_path}/{encoded_path}/info.json"
        
        logger.info(f"Requesting PDF info from: {info_url}")
        
        # Request the info.json from Cantaloupe
        try:
            response = requests.get(info_url, timeout=10)
            if response.status_code == 200:
                info = response.json()
                logger.info(f"Successfully retrieved info.json")
                return info
            else:
                logger.error(f"Failed to get info.json: HTTP {response.status_code}")
                logger.error(f"Response: {response.text[:200]}...")
                return None
        except Exception as e:
            logger.error(f"Error retrieving info.json: {str(e)}")
            return None
    
    def generate_pdf_manifest(self, record_id, filename, base_url, label=None):
        """Generate a IIIF manifest for a PDF file."""
        # Get the PDF info from Cantaloupe
        pdf_info = self.get_pdf_info(record_id, filename)
        if not pdf_info:
            logger.error(f"Unable to generate manifest: could not get PDF info for {filename}")
            return None
        
        # Default values
        default_width = pdf_info.get('width', 2000)
        default_height = pdf_info.get('height', 3000)
        id_prefix = f"{base_url}/api/iiif/record:{record_id}"
        label = label or f"{os.path.splitext(filename)[0]} (PDF)"
        
        # Get number of pages
        num_pages = 0
        if 'sizes' in pdf_info:
            num_pages = len(pdf_info.get('sizes', []))
        elif 'tiles' in pdf_info:
            num_pages = len(pdf_info.get('tiles', []))
        
        logger.info(f"PDF has {num_pages} pages according to Cantaloupe info.json")
        
        # Basic manifest structure
        manifest = {
            "@context": "http://iiif.io/api/presentation/2/context.json",
            "@id": f"{id_prefix}/manifest",
            "@type": "sc:Manifest",
            "label": label,
            "sequences": [
                {
                    "@id": f"{id_prefix}/sequence/default",
                    "@type": "sc:Sequence",
                    "label": "Default sequence",
                    "canvases": []
                }
            ],
            "related": {
                "@id": f"{base_url}/api/records/{record_id}/files/{filename}/content",
                "format": "application/pdf",
                "label": "Download full PDF"
            }
        }
        
        # Create a canvas for each page
        file_path = self._get_file_path(record_id, filename)
        encoded_path = file_path.replace("/", "%2F")
        
        for page_num in range(1, num_pages + 1):
            page_width = default_width
            page_height = default_height
            
            # Create canvas for this page
            canvas = {
                "@id": f"{id_prefix}/canvas/p{page_num:03d}",
                "@type": "sc:Canvas",
                "label": f"p. {page_num:03d}",
                "width": page_width,
                "height": page_height,
                "images": [
                    {
                        "@type": "oa:Annotation",
                        "motivation": "sc:painting",
                        "resource": {
                            "@id": f"{self.server_url}{self.base_path}/{encoded_path}/full/max/0/default.jpg?page={page_num}",
                            "@type": "dctypes:Image",
                            "format": "image/jpeg",
                            "width": page_width,
                            "height": page_height,
                            "service": {
                                "@context": "http://iiif.io/api/image/2/context.json",
                                "@id": f"{self.server_url}{self.base_path}/{encoded_path}?page={page_num}",
                                "profile": "http://iiif.io/api/image/2/level2.json"
                            }
                        },
                        "on": f"{id_prefix}/canvas/p{page_num:03d}"
                    }
                ]
            }
            
            # Add canvas to sequence
            manifest["sequences"][0]["canvases"].append(canvas)
        
        logger.info(f"Generated manifest with {len(manifest['sequences'][0]['canvases'])} canvases")
        return manifest

def check_actual_manifest(record_id, base_url):
    """Check the real manifest from the API."""
    manifest_url = f"{base_url}/api/iiif/record:{record_id}/manifest"
    
    logger.info(f"Checking actual manifest from: {manifest_url}")
    
    try:
        response = requests.get(manifest_url, timeout=10)
        if response.status_code == 200:
            manifest = response.json()
            logger.info(f"Successfully retrieved manifest")
            
            # Check for canvases
            canvases = manifest.get('sequences', [{}])[0].get('canvases', [])
            logger.info(f"Manifest has {len(canvases)} canvases")
            
            # Check if the canvases have images
            empty_canvases = 0
            for canvas in canvases:
                if not canvas.get('images', []):
                    empty_canvases += 1
            
            if empty_canvases > 0:
                logger.warning(f"Found {empty_canvases} canvases with no images")
            
            return manifest
        else:
            logger.error(f"Failed to get manifest: HTTP {response.status_code}")
            logger.error(f"Response: {response.text[:200]}...")
            return None
    except Exception as e:
        logger.error(f"Error retrieving manifest: {str(e)}")
        return None

def main():
    """Main function to test PDF manifest generation."""
    parser = argparse.ArgumentParser(description="Test PDF manifest generation")
    parser.add_argument("--record", "-r", required=True, help="Record ID")
    parser.add_argument("--filename", "-f", required=True, help="PDF filename")
    parser.add_argument("--base-url", "-b", default="http://localhost:5000", help="Base URL for the API")
    parser.add_argument("--cantaloupe-url", "-c", default=None, help="Cantaloupe server URL (optional)")
    parser.add_argument("--output", "-o", default=None, help="Output file for manifest JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Print header
    print("\n==== Testing PDF Manifest Generation ====\n")
    print(f"Record ID: {args.record}")
    print(f"Filename: {args.filename}")
    print(f"Base URL: {args.base_url}")
    print(f"Cantaloupe URL: {args.cantaloupe_url or 'default'}")
    
    # Create proxy instance
    proxy = CantaloupeTestProxy(server_url=args.cantaloupe_url)
    
    # Step 1: Check if we can get PDF info from Cantaloupe
    print("\n1. Checking PDF info from Cantaloupe...")
    pdf_info = proxy.get_pdf_info(args.record, args.filename)
    
    if pdf_info:
        print("✅ Successfully retrieved PDF info")
        print(f"- Width: {pdf_info.get('width', 'unknown')}")
        print(f"- Height: {pdf_info.get('height', 'unknown')}")
        
        sizes = pdf_info.get('sizes', [])
        tiles = pdf_info.get('tiles', [])
        print(f"- Sizes: {len(sizes)}")
        print(f"- Tiles: {len(tiles)}")
        
        # Determine number of pages
        num_pages = 0
        if tiles:
            num_pages = len(tiles)
        elif sizes:
            num_pages = len(sizes)
            
        print(f"- Estimated pages: {num_pages}")
    else:
        print("❌ Failed to retrieve PDF info")
        sys.exit(1)
    
    # Step 2: Generate test manifest
    print("\n2. Generating test manifest...")
    manifest = proxy.generate_pdf_manifest(
        args.record,
        args.filename,
        args.base_url
    )
    
    if manifest:
        canvases = manifest.get('sequences', [{}])[0].get('canvases', [])
        print(f"✅ Successfully generated manifest with {len(canvases)} canvases")
        
        # Save manifest if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(manifest, f, indent=2)
            print(f"Saved manifest to {args.output}")
    else:
        print("❌ Failed to generate manifest")
        sys.exit(1)
    
    # Step 3: Check the actual manifest from the API
    print("\n3. Checking actual manifest from API...")
    actual_manifest = check_actual_manifest(args.record, args.base_url)
    
    if actual_manifest:
        actual_canvases = actual_manifest.get('sequences', [{}])[0].get('canvases', [])
        print(f"✅ Successfully retrieved actual manifest with {len(actual_canvases)} canvases")
        
        # Compare with our test manifest
        if len(canvases) != len(actual_canvases):
            print(f"⚠️ Canvas count differs: {len(canvases)} (test) vs {len(actual_canvases)} (actual)")
        
        # Check if the actual canvases have images
        empty_canvases = 0
        for canvas in actual_canvases:
            if not canvas.get('images', []):
                empty_canvases += 1
        
        if empty_canvases > 0:
            print(f"⚠️ Actual manifest has {empty_canvases} canvases with no images")
        
        # Save actual manifest if output file specified
        if args.output:
            actual_output = f"actual_{args.output}"
            with open(actual_output, 'w') as f:
                json.dump(actual_manifest, f, indent=2)
            print(f"Saved actual manifest to {actual_output}")
    else:
        print("❌ Failed to retrieve actual manifest")
    
    # Step 4: Display conclusions
    print("\n4. Conclusions:")
    
    if manifest and actual_manifest:
        # Check if actual manifest might be using a different generator
        test_images = manifest['sequences'][0]['canvases'][0].get('images', [])
        actual_images = actual_manifest['sequences'][0]['canvases'][0].get('images', []) if actual_canvases else []
        
        using_custom = (
            len(test_images) > 0 and 
            len(actual_images) > 0 and
            test_images[0].get('resource', {}).get('@id') == 
            actual_images[0].get('resource', {}).get('@id')
        )
        
        if using_custom:
            print("✅ The site appears to be using your custom PDF manifest generator")
        else:
            print("❌ The site is NOT using your custom PDF manifest generator")
            print("\nPossible issues:")
            print("1. The custom ZenodoIIIFResource is not properly registered")
            print("2. The RDM_IIIF_PDF_SUPPORT setting is not True in production")
            print("3. The Cantaloupe proxy integration is misconfigured")
            print("\nSuggested fixes:")
            print("1. Verify that the ZenodoRDM extension is properly registering your custom IIIF resource")
            print("2. Check all settings in invenio.cfg match your development environment")
            print("3. Make sure the Cantaloupe server is accessible and properly configured")
    
    print("\nTest completed.")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python
"""
Test the generation of a PDF manifest through the API.
This script tests if the PDF manifest can be generated using the API.
"""

import os
import sys
import json
import requests
import subprocess
import argparse
from urllib.parse import quote

# Try to import Invenio modules
try:
    from flask import current_app
    from invenio_app.factory import create_app
    from invenio_iiif.utils import iiif_image_key, get_image_opener
    from invenio_rdm_records.resources.serializers.iiif import generate_pdf_manifest
    HAS_INVENIO = True
except ImportError:
    HAS_INVENIO = False

def load_app_context():
    """Load the Flask app context."""
    if not HAS_INVENIO:
        print("Invenio modules not available. Running in API mode only.")
        return None
    
    print("Loading Invenio app context...")
    app = create_app()
    return app

def test_cantaloupe_access(record_id, filename):
    """Test if Cantaloupe can access the PDF file."""
    print(f"\nTesting if Cantaloupe can access the PDF file for record {record_id}...")
    
    # Construct the URL patterns to try
    url_patterns = [
        f"http://localhost:8182/iiif/2/records%2F{record_id}%2F{filename}/info.json",
        f"http://localhost:8182/iiif/2/private%2F{record_id}%2F{filename}/info.json",
        f"http://localhost:8182/iiif/2/{record_id}%2F{filename}/info.json"
    ]
    
    success = False
    working_url = None
    
    for url in url_patterns:
        print(f"Trying URL: {url}")
        try:
            response = requests.get(url)
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                success = True
                working_url = url
                print("Success! Cantaloupe can access the file.")
                try:
                    info = response.json()
                    print(f"File dimensions: {info.get('width')}x{info.get('height')}")
                    print(f"Available sizes: {len(info.get('sizes', []))}")
                except:
                    print(f"Response not JSON: {response.text[:200]}...")
                break
            else:
                print(f"Error: {response.text[:200]}...")
        except Exception as e:
            print(f"Error accessing URL: {str(e)}")
    
    if not success:
        print("\nCantaloupe cannot access the PDF file. Make sure it exists in the correct location.")
        return None
    
    return working_url

def test_manifest_generation_api(record_id, filename, api_url=None):
    """Test the generation of a PDF manifest through the API."""
    print(f"\nTesting PDF manifest generation through the API for record {record_id}...")
    
    # Default to localhost if no API URL provided
    if api_url is None:
        api_url = "http://localhost:5000"
    
    # Construct the manifest URL
    manifest_url = f"{api_url}/api/records/{record_id}/iiif/manifest"
    print(f"Requesting manifest from: {manifest_url}")
    
    # Add Accept header for IIIF
    headers = {
        "Accept": "application/ld+json;profile=\"http://iiif.io/api/presentation/3/context.json\""
    }
    
    try:
        response = requests.get(manifest_url, headers=headers)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("Success! Manifest generated successfully.")
            manifest = response.json()
            
            # Check if manifest has items/canvases
            if "items" in manifest:
                print(f"Manifest contains {len(manifest['items'])} canvases.")
                
                # Check if the PDF is included in the manifest
                for i, canvas in enumerate(manifest["items"]):
                    print(f"\nCanvas {i+1}:")
                    print(f"ID: {canvas.get('id', 'N/A')}")
                    print(f"Label: {json.dumps(canvas.get('label', {}))}")
                    
                    # Check annotations for PDF content
                    if "annotations" in canvas:
                        for anno_page in canvas["annotations"]:
                            for anno in anno_page.get("items", []):
                                body = anno.get("body", {})
                                if body.get("format") == "application/pdf":
                                    print(f"✓ PDF resource found in annotation: {body.get('id', 'N/A')}")
                return manifest
            else:
                print("Warning: Manifest does not contain any canvases.")
        else:
            print(f"Error generating manifest: {response.text[:200]}...")
    except Exception as e:
        print(f"Error requesting manifest: {str(e)}")
    
    return None

def test_manifest_generation_code(record_id, filename):
    """Test the generation of a PDF manifest using the Invenio code directly."""
    if not HAS_INVENIO:
        print("\nCannot test manifest generation via code - Invenio modules not available.")
        return None
    
    print(f"\nTesting PDF manifest generation using the Invenio code for record {record_id}...")
    
    try:
        with app.app_context():
            # Convert record ID to str to match the expected format
            record_id_str = str(record_id)
            
            # Create a file object with necessary attributes
            file_obj = {
                "key": filename,
                "record_id": record_id_str,
                "file_id": "dummy-file-id",  # We don't need the real file ID
                "mimetype": "application/pdf",
                "size": 12345,  # Dummy size
            }
            
            # Generate the manifest
            manifest = generate_pdf_manifest(file_obj, record_id_str)
            
            # If the manifest was generated successfully
            if manifest:
                print("Success! Manifest generated successfully via code.")
                print(f"Manifest type: {type(manifest)}")
                
                # Convert to JSON for better display
                if hasattr(manifest, "json"):
                    manifest_json = manifest.json
                    print(f"Manifest contains {len(manifest_json.get('items', []))} canvases.")
                    return manifest_json
                else:
                    print(f"Manifest structure: {str(manifest)[:200]}...")
                    return manifest
            else:
                print("Error: Manifest generation returned None.")
    except Exception as e:
        print(f"Error generating manifest via code: {str(e)}")
    
    return None

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test the generation of a PDF manifest")
    parser.add_argument("--record", "-r", required=True, help="Record ID to check")
    parser.add_argument("--filename", "-f", default="history00871.pdf", help="Filename to use for testing")
    parser.add_argument("--api-url", "-u", default="http://localhost:5000", help="API URL")
    
    args = parser.parse_args()
    
    # Load Invenio app context if available
    global app
    app = load_app_context()
    
    # Test if Cantaloupe can access the file
    working_url = test_cantaloupe_access(args.record, args.filename)
    
    if working_url:
        # Test manifest generation via API
        manifest_api = test_manifest_generation_api(args.record, args.filename, args.api_url)
        
        # Test manifest generation via code if Invenio is available
        if HAS_INVENIO and app:
            manifest_code = test_manifest_generation_code(args.record, args.filename)
    else:
        print("\nTest skipped because Cantaloupe cannot access the file.")

if __name__ == "__main__":
    main() 
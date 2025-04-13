#!/usr/bin/env python
# This script tests a IIIF manifest for a record
# Usage:
#   cd /path/to/zenodo-rdm
#   pipenv run python scripts/AlA/test_manifest.py RECORD_ID

import os
import sys
import json
import requests
from pprint import pprint
from urllib.parse import urljoin

def test_manifest(record_id, base_url=None):
    """Fetch and test the IIIF manifest for a record."""
    if not base_url:
        # Try to get base URL from environment or use default
        from flask import current_app
        try:
            # Try to initialize app context if available
            try:
                from invenio_app.factory import create_app
                app = create_app()
                with app.app_context():
                    base_url = current_app.config.get('SITE_UI_URL', 'https://127.0.0.1:5000')
            except ImportError:
                # Fallback to environment variable or default
                base_url = os.environ.get('SITE_UI_URL', 'https://127.0.0.1:5000')
        except Exception:
            base_url = 'https://127.0.0.1:5000'
    
    # Construct the manifest URL
    manifest_url = f"{base_url}/api/iiif/record:{record_id}/manifest"
    print(f"Testing manifest URL: {manifest_url}")
    
    # Fetch the manifest
    try:
        # Disable SSL verification for local testing
        response = requests.get(manifest_url, verify=False)
        
        if response.status_code == 200:
            manifest = response.json()
            print("\n✅ Successfully fetched manifest")
            print(f"Status code: {response.status_code}")
            print(f"Content type: {response.headers.get('Content-Type', 'Not specified')}")
            print(f"Response size: {len(response.content)} bytes")
            
            # Check manifest structure
            print("\nManifest validation:")
            
            # Check essential IIIF properties
            required_props = ['@context', '@id', '@type', 'label']
            for prop in required_props:
                if prop in manifest:
                    print(f"✓ Found required property: {prop}")
                else:
                    print(f"✗ Missing required property: {prop}")
            
            # Check if it's a proper IIIF manifest
            if manifest.get('@type') == 'sc:Manifest':
                print("✓ Correct manifest type: sc:Manifest")
            else:
                print(f"✗ Incorrect manifest type: {manifest.get('@type', 'Missing')}")
            
            # Check if there are canvases for the PDF pages
            sequences = manifest.get('sequences', [])
            if sequences:
                seq = sequences[0]
                canvases = seq.get('canvases', [])
                print(f"✓ Found {len(canvases)} canvases (PDF pages)")
                
                # Check the first canvas
                if canvases:
                    canvas = canvases[0]
                    print("\nFirst canvas details:")
                    print(f"- Label: {canvas.get('label', 'Missing')}")
                    print(f"- Width: {canvas.get('width', 'Missing')}")
                    print(f"- Height: {canvas.get('height', 'Missing')}")
                    
                    # Check for image resources
                    images = canvas.get('images', [])
                    if images:
                        img = images[0]
                        resource = img.get('resource', {})
                        service = resource.get('service', {})
                        
                        print("\nImage service details:")
                        print(f"- ID: {service.get('@id', 'Missing')}")
                        print(f"- Profile: {service.get('profile', 'Missing')}")
                    else:
                        print("✗ No images found in the first canvas")
            else:
                print("✗ No sequences or canvases found in the manifest")
                
            # Output the full manifest for inspection
            print("\nFull manifest content:")
            pprint(manifest, indent=2, depth=3, compact=True)
            
            return True
        else:
            print(f"❌ Failed to fetch manifest. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Network error fetching manifest: {e}")
        return False
    except ValueError as e:
        print(f"❌ Error parsing JSON response: {e}")
        print(f"Response text: {response.text}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_cantaloupe_info(record_id, filename=None, base_url=None):
    """Test direct access to Cantaloupe info.json for the PDF file."""
    if not base_url:
        base_url = os.environ.get('RDM_IIIF_SERVER_URL', 'http://localhost:8182')
    
    if not filename:
        # Try to determine filename using the record API
        try:
            from invenio_app.factory import create_app
            from invenio_records.api import Record
            from invenio_pidstore.models import PersistentIdentifier
            
            app = create_app()
            with app.app_context():
                try:
                    # Get record by PID
                    pid = PersistentIdentifier.get('recid', record_id)
                    record = Record.get_record(pid.object_uuid)
                    
                    # Extract file info
                    if 'bucket' in record and '_files' in record:
                        for key in record['_files']:
                            if key.lower().endswith('.pdf'):
                                filename = key
                                break
                except Exception as e:
                    print(f"Error accessing record data: {e}")
        except ImportError:
            print("Could not import Invenio modules to detect filename")
    
    if not filename:
        filename = f"test_pdf.pdf"  # Default fallback
        print(f"Using default filename: {filename}")
    else:
        print(f"Using filename: {filename}")
    
    # Construct Cantaloupe info.json URL
    # Format: http://localhost:8182/iiif/2/<identifier>/info.json
    identifier = f"{record_id}%2F{filename}"  # URL-encode the slash
    info_url = f"{base_url}/iiif/2/{identifier}/info.json"
    
    print(f"\nTesting Cantaloupe info URL: {info_url}")
    
    # Fetch info.json
    try:
        response = requests.get(info_url, verify=False)
        
        if response.status_code == 200:
            info = response.json()
            print("\n✅ Successfully fetched info.json from Cantaloupe")
            print(f"Status code: {response.status_code}")
            
            # Check basic info properties
            for prop in ['@context', '@id', 'protocol', 'width', 'height']:
                if prop in info:
                    print(f"✓ Found info property: {prop}")
                    if prop in ['width', 'height']:
                        print(f"  Value: {info[prop]}")
                else:
                    print(f"✗ Missing info property: {prop}")
            
            # Output full info for inspection
            print("\nFull info.json content:")
            pprint(info)
            
            return True
        else:
            print(f"❌ Failed to fetch info.json. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Network error fetching info.json: {e}")
        return False
    except ValueError as e:
        print(f"❌ Error parsing JSON response: {e}")
        if 'response' in locals():
            print(f"Response text: {response.text}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main function when run as a script."""
    if len(sys.argv) < 2:
        print("Usage: pipenv run python scripts/AlA/test_manifest.py RECORD_ID [FILENAME]")
        return
    
    # Get record ID from command line arguments
    record_id = sys.argv[1]
    
    # Get optional filename
    filename = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Test the manifest
    print("\n=== Testing IIIF Manifest ===\n")
    test_manifest(record_id)
    
    # Test Cantaloupe info.json
    print("\n=== Testing Cantaloupe Info JSON ===\n")
    test_cantaloupe_info(record_id, filename)

if __name__ == "__main__":
    main() 
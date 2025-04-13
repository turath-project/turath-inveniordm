#!/usr/bin/env python3
"""
Script to check IIIF functionality for a record, with special focus on PDF support.
"""
import sys
import requests
import json
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for local testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} RECORD_ID")
    sys.exit(1)

RECORD_ID = sys.argv[1]

print(f"Checking IIIF functionality for record {RECORD_ID}...")

def check_pdf_support(manifest):
    """Check if the manifest indicates PDF support.
    
    PDF support is detected if:
    1. There is a PDF service in the manifest
    2. There are canvases in the sequences
    3. There is a related object with PDF format
    """
    has_pdf_service = False
    has_canvases = False
    has_pdf_related = False
    
    # Check for PDF service
    if "sequences" in manifest:
        for sequence in manifest["sequences"]:
            if "canvases" in sequence and len(sequence["canvases"]) > 0:
                has_canvases = True
                for canvas in sequence["canvases"]:
                    if "images" in canvas:
                        for image in canvas["images"]:
                            if "resource" in image and "service" in image["resource"]:
                                service = image["resource"]["service"]
                                if isinstance(service, dict) and "service" in service:
                                    has_pdf_service = True
    
    # Check for related PDF link
    if "related" in manifest and isinstance(manifest["related"], dict):
        if manifest["related"].get("format") == "application/pdf":
            has_pdf_related = True
    
    return has_pdf_service or (has_canvases and has_pdf_related)

# Check manifest
try:
    manifest_url = f"https://127.0.0.1:5000/api/iiif/record:{RECORD_ID}/manifest"
    print(f"Checking manifest at: {manifest_url}")
    
    response = requests.get(manifest_url, verify=False)
    
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    manifest = response.json()
    
    # Check basic manifest properties
    print(f"Manifest title: {manifest.get('label', 'Unknown')}")
    
    # Check for PDF support
    has_pdf = check_pdf_support(manifest)
    print(f"PDF support detected: {'Yes' if has_pdf else 'No'}")
    
    # Check sequences and canvases
    sequences = manifest.get('sequences', [])
    if not sequences:
        print("Warning: Manifest has no sequences")
        sys.exit(1)
    
    sequence = sequences[0]
    canvases = sequence.get('canvases', [])
    print(f"Found {len(canvases)} pages in manifest")
    
    # Check each canvas and its image
    for i, canvas in enumerate(canvases):
        canvas_id = canvas.get('@id', 'Unknown')
        label = canvas.get('label', 'Unknown')
        images = canvas.get('images', [])
        
        print(f"\nPage {i+1}: {label}")
        print(f"  ID: {canvas_id}")
        
        if not images:
            print(f"  Warning: Canvas has no images")
            continue
        
        for j, image in enumerate(images):
            resource = image.get('resource', {})
            service = resource.get('service', {})
            image_service_url = service.get('@id', 'Unknown')
            
            print(f"  Image {j+1} service: {image_service_url}")
            
            # Test image info.json
            info_url = f"{image_service_url}/info.json"
            info_response = requests.get(info_url, verify=False)
            
            if info_response.status_code != 200:
                print(f"  Warning: Could not access image info at {info_url}")
                print(f"  Status: {info_response.status_code}")
            else:
                info = info_response.json()
                print(f"  Image info accessible: ✓")
                print(f"  Dimensions: {info.get('width')}x{info.get('height')}")
                print(f"  Profile: {info.get('profile', [''])[0]}")
            
            # Test thumbnail access
            thumb_url = f"{image_service_url}/full/200,/0/default.jpg"
            thumb_response = requests.get(thumb_url, verify=False, stream=True)
            
            if thumb_response.status_code != 200:
                print(f"  Warning: Could not access thumbnail at {thumb_url}")
                print(f"  Status: {thumb_response.status_code}")
            else:
                content_length = int(thumb_response.headers.get('Content-Length', 0))
                print(f"  Thumbnail accessible: ✓ ({content_length} bytes)")
    
except Exception as e:
    print(f"Error checking IIIF functionality: {e}")
    sys.exit(1) 
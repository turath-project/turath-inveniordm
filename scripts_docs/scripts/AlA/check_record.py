#!/usr/bin/env python3
"""
Simple script to check record files.
"""
import sys
import requests
import json
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for local testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

RECORD_ID = "202"  # Default record ID
if len(sys.argv) > 1:
    RECORD_ID = sys.argv[1]

print(f"Checking record {RECORD_ID}...")

try:
    # Get record data
    url = f"https://127.0.0.1:5000/api/records/{RECORD_ID}"
    response = requests.get(url, verify=False)
    
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    data = response.json()
    
    # Print basic record info
    print(f"Title: {data.get('metadata', {}).get('title', 'Unknown')}")
    
    # Print files
    files = data.get('files', [])
    print(f"\nFound {len(files)} files:")
    
    image_files = []
    for file in files:
        key = file.get('key', '')
        size = file.get('size', 0)
        print(f"- {key} ({size} bytes)")
        
        if key.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
            image_files.append(key)
    
    # Summarize image files
    print(f"\nFound {len(image_files)} image files that could be converted to PTIF:")
    for img in image_files:
        print(f"- {img}")
    
    # Instructions for next steps
    if image_files:
        print("\nNext steps:")
        print(f"1. Create directory: mkdir -p data/images/private/{RECORD_ID}")
        print(f"2. Create PTIF files for each image")
        print(f"3. Test IIIF access: curl http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/private/{RECORD_ID}/FILENAME.ptif/info.json")
    
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1) 
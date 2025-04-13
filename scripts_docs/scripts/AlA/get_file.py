#!/usr/bin/env python3
"""
Script to download a file from a Zenodo-RDM record.
"""
import sys
import requests
import os
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for local testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} RECORD_ID FILENAME [OUTPUT_DIR]")
    sys.exit(1)

RECORD_ID = sys.argv[1]
FILENAME = sys.argv[2]
OUTPUT_DIR = sys.argv[3] if len(sys.argv) > 3 else "."

print(f"Downloading file {FILENAME} from record {RECORD_ID}...")

try:
    # Get file download link
    url = f"https://127.0.0.1:5000/api/records/{RECORD_ID}/files/{FILENAME}/content"
    
    # Download the file with stream=True to handle large files
    response = requests.get(url, verify=False, stream=True)
    
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Save the file
    output_path = os.path.join(OUTPUT_DIR, FILENAME)
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"Successfully downloaded to {output_path}")
    print(f"File size: {os.path.getsize(output_path)} bytes")
    
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1) 
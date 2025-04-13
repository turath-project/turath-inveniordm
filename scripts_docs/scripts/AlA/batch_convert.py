#!/usr/bin/env python3
"""
Batch script to convert all images in a Zenodo-RDM record to PTIF format for IIIF support.
"""

import os
import sys
import requests
import json
import subprocess
import shutil
import time
from urllib3.exceptions import InsecureRequestWarning

# Import our single file conversion script
from convert_to_ptif import convert_to_ptif, copy_to_iipserver

# Disable SSL warnings for local testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def get_record_files(record_id):
    """Get all files from a record."""
    print(f"Getting files for record {record_id}...")
    
    try:
        # Get record data
        url = f"https://127.0.0.1:5000/api/records/{record_id}"
        response = requests.get(url, verify=False)
        
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            print(response.text)
            return None
        
        data = response.json()
        
        # Extract all image files
        files = data.get('files', [])
        image_files = []
        
        for file in files:
            key = file.get('key', '')
            size = file.get('size', 0)
            
            if key.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
                image_files.append({
                    'key': key,
                    'size': size
                })
        
        print(f"Found {len(image_files)} image files")
        return image_files
    
    except Exception as e:
        print(f"Error getting record files: {e}")
        return None

def download_file(record_id, filename, output_dir):
    """Download a file from a record."""
    print(f"Downloading {filename}...")
    
    try:
        # Get file download link
        url = f"https://127.0.0.1:5000/api/records/{record_id}/files/{filename}/content"
        
        # Download the file with stream=True to handle large files
        response = requests.get(url, verify=False, stream=True)
        
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            print(response.text)
            return None
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save the file
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Downloaded to {output_path}")
        return output_path
    
    except Exception as e:
        print(f"Error downloading file: {e}")
        return None

def verify_iiif_manifest(record_id):
    """Check if the IIIF manifest for this record exists and is valid."""
    manifest_url = f"https://127.0.0.1:5000/api/iiif/record/{record_id}/manifest"
    
    try:
        headers = {"Accept": "application/json"}
        response = requests.get(manifest_url, headers=headers, verify=False)
        
        if response.status_code != 200:
            print(f"❌ IIIF manifest not accessible: HTTP {response.status_code}")
            return False
        
        manifest = response.json()
        
        # Check for sequences and canvases
        sequences = manifest.get('sequences', [])
        if not sequences:
            print("❌ Manifest does not contain any sequences")
            return False
        
        sequence = sequences[0]
        canvases = sequence.get('canvases', [])
        if not canvases:
            print("❌ Sequence does not contain any canvases")
            return False
        
        print(f"✅ IIIF manifest accessible with {len(canvases)} images")
        return True
    
    except Exception as e:
        print(f"Error checking IIIF manifest: {e}")
        return False

def batch_convert(record_id):
    """Convert all images in a record to PTIF format."""
    # Get files from the record
    image_files = get_record_files(record_id)
    if not image_files:
        print("No image files found or error occurred.")
        return False
    
    # Create a temporary directory for downloaded files
    temp_dir = f"temp_record_{record_id}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Process each image file
        success_count = 0
        failed_count = 0
        
        for idx, file_info in enumerate(image_files):
            filename = file_info['key']
            print(f"\n[{idx+1}/{len(image_files)}] Processing {filename}...")
            
            # Download the file
            download_path = download_file(record_id, filename, temp_dir)
            if not download_path:
                print(f"❌ Failed to download {filename}")
                failed_count += 1
                continue
            
            # Convert to PTIF
            ptif_path = f"{os.path.splitext(download_path)[0]}.ptif"
            if not convert_to_ptif(download_path, ptif_path):
                print(f"❌ Failed to convert {filename} to PTIF")
                failed_count += 1
                continue
            
            # Copy to IIPServer
            base_name = os.path.splitext(os.path.basename(filename))[0]
            ptif_filename = copy_to_iipserver(ptif_path, record_id)
            if not ptif_filename:
                print(f"❌ Failed to copy {filename} to IIPServer")
                failed_count += 1
                continue
            
            # Success
            success_count += 1
        
        # Summarize results
        print(f"\nConversion complete: {success_count} successful, {failed_count} failed")
        
        # Verify the IIIF manifest is now accessible
        print("\nChecking IIIF manifest...")
        verify_iiif_manifest(record_id)
        
        print("\nTo test IIIF functionality, open the following URL in your browser:")
        print(f"https://127.0.0.1:5000/records/{record_id}")
        
        return success_count > 0
    
    finally:
        # Clean up
        print(f"\nCleaning up temporary directory {temp_dir}...")
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} RECORD_ID")
        sys.exit(1)
    
    record_id = sys.argv[1]
    if batch_convert(record_id):
        print(f"\n✅ Successfully processed record {record_id}")
        sys.exit(0)
    else:
        print(f"\n❌ Failed to process record {record_id}")
        sys.exit(1) 
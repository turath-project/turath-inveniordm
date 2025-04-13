#!/usr/bin/env python3
"""
Script to check if PDF IIIF manifest generation is working for a record.
This script verifies:
1. If the record exists and has PDF files
2. If the manifest can be retrieved
3. If Cantaloupe can serve the PDF pages
4. If the file paths are correctly set up
"""
import os
import sys
import json
import requests
import time
from urllib3.exceptions import InsecureRequestWarning
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Disable SSL warnings for local testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def check_record_exists(record_id, api_token=None):
    """Check if a record exists and return its data."""
    headers = {}
    if api_token:
        headers['Authorization'] = f'Bearer {api_token}'
    
    url = f"https://127.0.0.1:5000/api/records/{record_id}"
    logger.info(f"Checking record at {url}")
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get record: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error checking record: {e}")
        return None

def find_pdf_files(record_data):
    """Find PDF files in a record."""
    if not record_data:
        return []
    
    pdf_files = []
    
    # Handle different response formats
    files_data = None
    
    # Format 1: record_data["files"]["entries"]
    if isinstance(record_data, dict) and "files" in record_data:
        if isinstance(record_data["files"], dict) and "entries" in record_data["files"]:
            files_data = record_data["files"]["entries"]
        elif isinstance(record_data["files"], list):
            files_data = record_data["files"]
    
    # Format 2: record_data["metadata"]["_files"]
    elif isinstance(record_data, dict) and "metadata" in record_data:
        if "_files" in record_data["metadata"]:
            files_data = record_data["metadata"]["_files"]
    
    # Format 3: record_data is a list of files directly
    elif isinstance(record_data, list):
        files_data = record_data
    
    # If no files found, return empty list
    if not files_data:
        return []
    
    # Extract PDF files
    for file_entry in files_data:
        if isinstance(file_entry, dict) and "key" in file_entry:
            if file_entry["key"].lower().endswith(".pdf"):
                pdf_files.append(file_entry)
        elif isinstance(file_entry, dict) and "filename" in file_entry:
            if file_entry["filename"].lower().endswith(".pdf"):
                # Convert to expected format
                pdf_files.append({
                    "key": file_entry["filename"],
                    "size": file_entry.get("size", 0)
                })
    
    return pdf_files

def check_iiif_manifest(record_id, api_token=None):
    """Check if IIIF manifest is available for a record."""
    headers = {}
    if api_token:
        headers['Authorization'] = f'Bearer {api_token}'
    
    url = f"https://127.0.0.1:5000/api/records/{record_id}/iiif/manifest.json"
    logger.info(f"Checking IIIF manifest at {url}")
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get manifest: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error checking manifest: {e}")
        return None

def check_cantaloupe_access(record_id, filename):
    """Check if Cantaloupe can access the PDF file."""
    # First, try the standard path format
    file_path = f"records/{record_id}/{filename}"
    encoded_path = file_path.replace("/", "%2F")
    
    # Try to get info.json
    url = f"http://localhost:8182/iiif/2/{encoded_path}/info.json"
    logger.info(f"Checking Cantaloupe access at {url}")
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            logger.info("✅ Cantaloupe can access the PDF file")
            return response.json()
        else:
            logger.error(f"Failed to access PDF via Cantaloupe: {response.status_code}")
            
            # Try alternative path formats
            alternative_paths = [
                f"private/{record_id}/{filename}",
                f"{record_id}/{filename}"
            ]
            
            for alt_path in alternative_paths:
                encoded_alt = alt_path.replace("/", "%2F")
                alt_url = f"http://localhost:8182/iiif/2/{encoded_alt}/info.json"
                logger.info(f"Trying alternative path: {alt_url}")
                
                try:
                    alt_response = requests.get(alt_url)
                    if alt_response.status_code == 200:
                        logger.info(f"✅ Cantaloupe can access the PDF via alternative path: {alt_path}")
                        return alt_response.json()
                except Exception:
                    pass
            
            return None
    except Exception as e:
        logger.error(f"Error checking Cantaloupe access: {e}")
        return None

def check_file_locations(record_id, filename):
    """Check if the file exists in the expected locations."""
    # Check in data/records/{record_id}/{filename}
    record_path = os.path.join("data", "records", record_id, filename)
    
    results = {
        "record_path_exists": os.path.exists(record_path),
        "record_path": record_path
    }
    
    if results["record_path_exists"]:
        logger.info(f"✅ File exists at {record_path}")
        results["record_path_size"] = os.path.getsize(record_path)
    else:
        logger.warning(f"❌ File not found at {record_path}")
    
    # Check Docker container for Cantaloupe
    try:
        docker_cmd = f"docker compose exec cantaloupe ls -la /opt/cantaloupe/images/records/{record_id}/{filename}"
        logger.info(f"Checking in Docker container: {docker_cmd}")
        process = subprocess.run(docker_cmd, shell=True, capture_output=True, text=True)
        
        results["docker_output"] = process.stdout
        results["docker_error"] = process.stderr
        results["docker_exists"] = process.returncode == 0
        
        if results["docker_exists"]:
            logger.info(f"✅ File found in Docker container")
        else:
            logger.warning(f"❌ File not found in Docker container: {process.stderr}")
    except Exception as e:
        logger.error(f"Error checking Docker container: {e}")
        results["docker_error"] = str(e)
    
    return results

def check_iiif_config():
    """Check if IIIF PDF support is enabled in configuration."""
    try:
        from flask import current_app
        from invenio_app.factory import create_app
        
        app = create_app()
        with app.app_context():
            iiif_enabled = current_app.config.get("RDM_IIIF_ENABLED", False)
            pdf_support = current_app.config.get("RDM_IIIF_PDF_SUPPORT", False)
            manifest_formats = current_app.config.get("RDM_IIIF_MANIFEST_FORMATS", [])
            
            logger.info(f"IIIF enabled: {iiif_enabled}")
            logger.info(f"PDF support enabled: {pdf_support}")
            logger.info(f"Manifest formats: {manifest_formats}")
            
            return {
                "iiif_enabled": iiif_enabled,
                "pdf_support": pdf_support,
                "pdf_in_formats": "pdf" in manifest_formats
            }
    except Exception as e:
        logger.error(f"Error checking config: {e}")
        return {
            "error": str(e)
        }

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} RECORD_ID [API_TOKEN]")
        sys.exit(1)
    
    record_id = sys.argv[1]
    api_token = sys.argv[2] if len(sys.argv) > 2 else os.getenv('API_TOKEN')
    
    print("\n===== Checking PDF IIIF Support =====\n")
    
    # Step 1: Check configuration
    print("\n=== Checking Configuration ===")
    config = check_iiif_config()
    if not config.get("iiif_enabled") or not config.get("pdf_support") or not config.get("pdf_in_formats"):
        print("❌ IIIF PDF support not properly configured!")
        sys.exit(1)
    
    # Step 2: Check if record exists and has PDF files
    print("\n=== Checking Record and PDF Files ===")
    record_data = check_record_exists(record_id, api_token)
    if not record_data:
        print(f"❌ Record {record_id} not found!")
        sys.exit(1)
    
    pdf_files = find_pdf_files(record_data)
    if not pdf_files:
        print(f"❌ No PDF files found in record {record_id}!")
        sys.exit(1)
    
    print(f"✅ Found {len(pdf_files)} PDF files in record {record_id}")
    for pdf in pdf_files:
        print(f"  - {pdf.get('key')} ({pdf.get('size')} bytes)")
    
    # Step 3: Check IIIF manifest
    print("\n=== Checking IIIF Manifest ===")
    manifest = check_iiif_manifest(record_id, api_token)
    if not manifest:
        print(f"❌ Failed to get IIIF manifest for record {record_id}!")
        sys.exit(1)
    
    # Check if manifest has canvases (pages)
    canvases = manifest.get("sequences", [{}])[0].get("canvases", [])
    if not canvases:
        print(f"❌ No canvases (pages) found in manifest!")
        sys.exit(1)
    
    print(f"✅ Found manifest with {len(canvases)} canvases (pages)")
    
    # Step 4: Check Cantaloupe access for each PDF
    print("\n=== Checking Cantaloupe Access ===")
    cantaloupe_successful = False
    for pdf in pdf_files:
        filename = pdf.get("key")
        pdf_info = check_cantaloupe_access(record_id, filename)
        if pdf_info:
            cantaloupe_successful = True
            print(f"✅ Cantaloupe can access PDF: {filename}")
            print(f"  - Pages: {len(pdf_info.get('sizes', []))}")
            print(f"  - Size: {pdf_info.get('width')}x{pdf_info.get('height')}")
        else:
            print(f"❌ Cantaloupe cannot access PDF: {filename}")
    
    if not cantaloupe_successful:
        # Step 5: Check file locations (only if Cantaloupe access failed)
        print("\n=== Checking File Locations ===")
        for pdf in pdf_files:
            filename = pdf.get("key")
            location_info = check_file_locations(record_id, filename)
            print(f"File path status for {filename}:")
            for key, value in location_info.items():
                if key not in ["docker_output", "docker_error"]:
                    print(f"  - {key}: {value}")
    
    # Step 6: Summary and recommendations
    print("\n=== Summary ===")
    if cantaloupe_successful:
        print("✅ PDF IIIF support appears to be working properly!")
        print("Access the manifest at:")
        print(f"  https://127.0.0.1:5000/api/records/{record_id}/iiif/manifest.json")
        print("Test the viewer at:")
        print(f"  https://127.0.0.1:5000/records/{record_id}")
    else:
        print("❌ Issues with PDF IIIF support detected.")
        print("\nRecommendations:")
        print("1. Ensure the Cantaloupe container is running:")
        print("   docker compose up -d cantaloupe")
        print("2. Make sure files exist in the expected locations:")
        print(f"   data/records/{record_id}/<filename>.pdf")
        print("3. Verify volume mappings in docker-compose.yml:")
        print("   ./data/records:/opt/cantaloupe/images/records")
        print("4. Check Cantaloupe logs for errors:")
        print("   docker compose logs cantaloupe")

if __name__ == "__main__":
    main() 
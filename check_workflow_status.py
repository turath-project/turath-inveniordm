#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check Workflow Status Script

This script checks the current status of:
1. The InvenioRDM record upload
2. The Cantaloupe PDF copy
3. The IIIF manifest
"""

import os
import sys
import json
import requests
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('workflow-checker')

# Constants
API_URL = "https://localhost:5000/api"
CANTALOUPE_URL = "https://localhost:8182/iiif/3"
CANTALOUPE_DIR = "./data/cantaloupe/images"
TOKEN = "GjjZoySCrOlEv1ce0eqqiRq8kMfZk0H29fY4oEQM1x1Kwftn7sOi9jwU6aNuAa2V6cfdfDmj2jhB1svzb5wms7El7gyn02Ocb5jj"

def check_record_status():
    """Check for the most recently created record"""
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        # Get the list of records
        response = requests.get(
            f"{API_URL}/records",
            headers=headers,
            verify=False
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get records. Status code: {response.status_code}")
            return None
        
        records = response.json().get('hits', {}).get('hits', [])
        
        if not records:
            logger.error("No records found")
            return None
        
        # Get the most recent record (first in the list)
        latest_record = records[0]
        record_id = latest_record.get('id')
        
        logger.info(f"Found latest record: {record_id}")
        logger.info(f"Title: {latest_record.get('metadata', {}).get('title')}")
        
        # Check for custom fields with IIIF manifest
        custom_fields = latest_record.get('metadata', {}).get('custom_fields', {})
        if 'iiif' in custom_fields and 'manifest' in custom_fields['iiif']:
            manifest_url = custom_fields['iiif']['manifest']
            logger.info(f"IIIF manifest URL: {manifest_url}")
        else:
            logger.warning("No IIIF manifest URL found in custom fields")
        
        # Check for files
        files_endpoint = f"{API_URL}/records/{record_id}/files"
        files_response = requests.get(
            files_endpoint,
            headers=headers,
            verify=False
        )
        
        if files_response.status_code != 200:
            logger.error(f"Failed to get files. Status code: {files_response.status_code}")
        else:
            files = files_response.json().get('entries', [])
            logger.info(f"Files in record: {len(files)}")
            
            for file in files:
                logger.info(f"File: {file.get('key')} ({file.get('size')} bytes)")
        
        return record_id
    
    except Exception as e:
        logger.error(f"Error checking record status: {str(e)}")
        return None

def check_cantaloupe_access(record_id):
    """Check if Cantaloupe can access the PDF"""
    if not record_id:
        logger.error("No record ID provided for Cantaloupe check")
        return False
    
    # Look for PDF in Cantaloupe directory
    cantaloupe_path = Path(CANTALOUPE_DIR) / "private" / record_id
    
    if not cantaloupe_path.exists():
        logger.error(f"Cantaloupe directory not found: {cantaloupe_path}")
        return False
    
    pdf_files = list(cantaloupe_path.glob("*.pdf"))
    
    if not pdf_files:
        logger.error(f"No PDF files found in {cantaloupe_path}")
        return False
    
    # Found PDF file
    pdf_file = pdf_files[0]
    logger.info(f"Found PDF in Cantaloupe directory: {pdf_file}")
    
    # Check Cantaloupe access via info.json
    identifier = f"private%2F{record_id}%2F{pdf_file.name}"
    info_url = f"{CANTALOUPE_URL}/{identifier}/info.json"
    
    try:
        logger.info(f"Testing Cantaloupe access: {info_url}")
        response = requests.get(info_url, verify=False, timeout=10)
        
        if response.status_code == 200:
            logger.info("✓ Successfully verified Cantaloupe access")
            return True
        else:
            logger.warning(f"⚠ Cantaloupe access test returned status {response.status_code}")
            return False
    except Exception as e:
        logger.warning(f"⚠ Cantaloupe access test failed: {str(e)}")
        return False

def check_manifest(record_id):
    """Check if the manifest is valid and points to the correct Cantaloupe URL"""
    if not record_id:
        logger.error("No record ID provided for manifest check")
        return False
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        # Look for manifest.json in record files
        files_endpoint = f"{API_URL}/records/{record_id}/files"
        files_response = requests.get(
            files_endpoint,
            headers=headers,
            verify=False
        )
        
        if files_response.status_code != 200:
            logger.error(f"Failed to get files. Status code: {files_response.status_code}")
            return False
        
        files = files_response.json().get('entries', [])
        manifest_file = None
        
        for file in files:
            if file.get('key') == 'manifest.json':
                manifest_file = file
                break
        
        if not manifest_file:
            logger.error("No manifest.json file found in record")
            return False
        
        # Download the manifest
        download_url = f"{API_URL}/records/{record_id}/files/manifest.json/content"
        download_response = requests.get(
            download_url,
            headers=headers,
            verify=False
        )
        
        if download_response.status_code != 200:
            logger.error(f"Failed to download manifest. Status code: {download_response.status_code}")
            return False
        
        manifest = download_response.json()
        
        # Check manifest content
        logger.info(f"Manifest @id: {manifest.get('@id')}")
        logger.info(f"Manifest label: {manifest.get('label')}")
        
        # Check for sequences and canvases
        sequences = manifest.get('sequences', [])
        if not sequences:
            logger.error("No sequences found in manifest")
            return False
        
        canvases = sequences[0].get('canvases', [])
        logger.info(f"Found {len(canvases)} canvases in manifest")
        
        # Check first canvas
        if canvases:
            first_canvas = canvases[0]
            logger.info(f"First canvas label: {first_canvas.get('label')}")
            
            images = first_canvas.get('images', [])
            if images:
                resource = images[0].get('resource', {})
                image_url = resource.get('@id')
                logger.info(f"First image URL: {image_url}")
                
                # Check if image URL points to Cantaloupe
                if CANTALOUPE_URL in image_url:
                    logger.info("✓ Image URL correctly points to Cantaloupe")
                    return True
                else:
                    logger.warning(f"⚠ Image URL does not point to Cantaloupe: {image_url}")
                    return False
        
        return False
    
    except Exception as e:
        logger.error(f"Error checking manifest: {str(e)}")
        return False

def main():
    """Main function"""
    logger.info("Checking workflow status...")
    
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Step 1: Check record status
    record_id = check_record_status()
    
    if not record_id:
        logger.error("Workflow verification failed at record check")
        return 1
    
    # Step 2: Check Cantaloupe access
    cantaloupe_ok = check_cantaloupe_access(record_id)
    
    if not cantaloupe_ok:
        logger.error("Workflow verification failed at Cantaloupe check")
        return 1
    
    # Step 3: Check manifest
    manifest_ok = check_manifest(record_id)
    
    if not manifest_ok:
        logger.error("Workflow verification failed at manifest check")
        return 1
    
    logger.info("✓ Workflow verification completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
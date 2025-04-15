#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Workflow Integration Script for Book Upload and IIIF Manifest Generation

This script:
1. Uploads a PDF book to InvenioRDM
2. Copies the PDF to Cantaloupe's directory structure
3. Generates a IIIF manifest pointing to Cantaloupe
4. Updates the InvenioRDM record with the manifest

Usage:
    python workflow_integration.py --book-dir /path/to/book \
        --api-url https://inveniordm.example.com/api \
        --token YOUR_API_TOKEN \
        --cantaloupe-url https://cantaloupe.example.com/iiif/3
"""

import os
import sys
import json
import time
import logging
import argparse
import subprocess
from pathlib import Path
import requests
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('workflow-integration')

# Default configuration
DEFAULT_CANTALOUPE_DIR = "/opt/cantaloupe/images"
DEFAULT_CANTALOUPE_URL = "https://localhost:8182"
DEFAULT_API_URL = "https://localhost:5000/api"

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Book Upload and IIIF Manifest Generation Workflow")
    
    # Required arguments
    parser.add_argument('--book-dir', '-b', required=True, help='Directory containing the book files')
    parser.add_argument('--token', required=True, help='InvenioRDM API token')
    
    # Optional arguments
    parser.add_argument('--api-url', default=DEFAULT_API_URL, 
                       help=f'InvenioRDM API URL (default: {DEFAULT_API_URL})')
    parser.add_argument('--cantaloupe-dir', default=DEFAULT_CANTALOUPE_DIR,
                       help=f'Cantaloupe data directory (default: {DEFAULT_CANTALOUPE_DIR})')
    parser.add_argument('--cantaloupe-url', default=DEFAULT_CANTALOUPE_URL,
                       help=f'Cantaloupe server URL (default: {DEFAULT_CANTALOUPE_URL})')
    parser.add_argument('--verify-ssl', action='store_true', help='Verify SSL certificates')
    parser.add_argument('--no-publish', action='store_true', help='Keep the record as a draft')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    return parser.parse_args()

def upload_book(book_dir, api_url, token, verify_ssl=False, publish=True):
    """
    Upload a book to InvenioRDM using the upload_book.py script.
    
    Args:
        book_dir: Directory containing the book files
        api_url: InvenioRDM API URL
        token: API token
        verify_ssl: Whether to verify SSL certificates
        publish: Whether to publish the record
    
    Returns:
        Tuple of (success, record_id)
    """
    logger.info(f"Uploading book from {book_dir} to InvenioRDM")
    
    # Prepare command
    cmd = [
        "python", "scripts/upload_book.py",
        "--book-dir", book_dir,
        "--api-url", api_url,
        "--token", token
    ]
    
    if not verify_ssl:
        cmd.append("--no-verify-ssl")
    
    if not publish:
        cmd.append("--draft")
    
    # Run the command
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Extract record ID from output
        output = result.stdout
        record_id = None
        
        # Parse output to find record ID
        # Expected format: "Created record with ID: abc-123-xyz"
        for line in output.splitlines():
            if "Created record with ID" in line:
                record_id = line.split("ID:")[-1].strip()
                break
        
        if record_id:
            logger.info(f"Successfully uploaded book with record ID: {record_id}")
            return True, record_id
        else:
            logger.error("Record ID not found in output")
            return False, None
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Error uploading book: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error: {e.stderr}")
        return False, None

def copy_pdf_to_cantaloupe(record_id, book_dir, cantaloupe_dir, cantaloupe_url, verify_ssl=False):
    """
    Copy the PDF file to Cantaloupe's directory structure.
    
    Args:
        record_id: InvenioRDM record ID
        book_dir: Book directory
        cantaloupe_dir: Cantaloupe data directory
        cantaloupe_url: Cantaloupe server URL
        verify_ssl: Whether to verify SSL certificates
    
    Returns:
        Tuple of (success, pdf_filename)
    """
    logger.info(f"Copying PDF to Cantaloupe for record {record_id}")
    
    # Find the PDF file
    pdf_files = list(Path(book_dir).glob("*.pdf"))
    if not pdf_files:
        logger.error(f"No PDF file found in {book_dir}")
        return False, None
    
    # Use the first PDF file
    pdf_path = str(pdf_files[0])
    pdf_filename = os.path.basename(pdf_path)
    
    # Create target directory
    target_dir = os.path.join(cantaloupe_dir, "private", record_id)
    target_path = os.path.join(target_dir, pdf_filename)
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)
        logger.info(f"Created directory: {target_dir}")
        
        # Copy the file
        shutil.copy2(pdf_path, target_path)
        logger.info(f"Copied PDF from {pdf_path} to {target_path}")
        
        # Test Cantaloupe access if needed
        if cantaloupe_url:
            identifier = f"private%2F{record_id}%2F{pdf_filename}"
            info_url = f"{cantaloupe_url}/{identifier}/info.json"
            
            try:
                time.sleep(2)  # Give Cantaloupe time to recognize the file
                logger.info(f"Testing Cantaloupe access: {info_url}")
                response = requests.get(info_url, verify=verify_ssl, timeout=10)
                
                if response.status_code == 200:
                    logger.info("✓ Successfully verified Cantaloupe access")
                else:
                    logger.warning(f"⚠ Cantaloupe access test returned status {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠ Cantaloupe access test failed: {str(e)}")
        
        return True, pdf_filename
        
    except Exception as e:
        logger.error(f"Error copying PDF to Cantaloupe: {str(e)}")
        return False, None

def generate_manifest(book_dir, record_id, pdf_filename, cantaloupe_url, manifest_server):
    """
    Generate a IIIF manifest for the book.
    
    Args:
        book_dir: Book directory
        record_id: InvenioRDM record ID
        pdf_filename: PDF filename
        cantaloupe_url: Cantaloupe server URL
        manifest_server: Manifest server base URL
    
    Returns:
        Tuple of (success, manifest_path)
    """
    logger.info(f"Generating IIIF manifest for record {record_id}")
    
    # First run the standard manifest generation
    manifest_cmd = [
        "python", "scripts/generate_manifest.py",
        "--book-dir", book_dir,
        "--iiif-server", cantaloupe_url,
        "--manifest-server", manifest_server,
        "--auto-scale",
        "--force"
    ]
    
    try:
        subprocess.run(manifest_cmd, capture_output=True, text=True, check=True)
        
        # Path to the generated manifest
        manifest_path = os.path.join(book_dir, "manifest.json")
        
        # Now update the manifest with the proper Cantaloupe identifier
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # Construct the proper identifier
        identifier = f"private/{record_id}/{pdf_filename}"
        encoded_identifier = identifier.replace("/", "%2F")
        
        # Update image URLs in the manifest
        for sequence in manifest.get('sequences', []):
            for canvas in sequence.get('canvases', []):
                page_num = 1
                
                # Extract page number from the canvas ID if possible
                canvas_id = canvas.get('@id', '')
                if canvas_id:
                    canvas_parts = canvas_id.split('/')
                    if canvas_parts:
                        page_id = canvas_parts[-1]
                        if page_id.startswith('p'):
                            try:
                                page_num = int(page_id[1:])
                            except ValueError:
                                pass
                
                # Update image URLs for each page
                for image in canvas.get('images', []):
                    if 'resource' in image:
                        # Update the image URL to point to Cantaloupe with the correct record ID
                        image['resource']['@id'] = f"{cantaloupe_url}/{encoded_identifier}/full/full/0/default.jpg?page={page_num}"
                        
                        # If there's a service, update it too
                        if 'service' in image['resource']:
                            image['resource']['service']['@id'] = f"{cantaloupe_url}/{encoded_identifier}?page={page_num}"
        
        # Write the updated manifest
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Created and updated manifest at {manifest_path}")
        return True, manifest_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error generating manifest: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error: {e.stderr}")
        return False, None
    except Exception as e:
        logger.error(f"Error updating manifest: {str(e)}")
        return False, None

def update_record_with_manifest(record_id, manifest_path, api_url, token, verify_ssl=False):
    """
    Upload the manifest to the InvenioRDM record and set the IIIF custom field.
    
    Args:
        record_id: InvenioRDM record ID
        manifest_path: Path to the manifest file
        api_url: InvenioRDM API URL
        token: API token
        verify_ssl: Whether to verify SSL certificates
    
    Returns:
        Boolean indicating success
    """
    logger.info(f"Updating record {record_id} with manifest")
    
    # Headers for API requests
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 1. First upload the manifest file
    try:
        # Get the draft record files endpoint
        files_endpoint = f"{api_url}/records/{record_id}/draft/files"
        
        # Initialize file upload
        filename = os.path.basename(manifest_path)
        init_data = {"key": filename}
        
        # Start the file upload process
        init_resp = requests.post(
            files_endpoint,
            headers=headers,
            json=[init_data],
            verify=verify_ssl
        )
        
        if init_resp.status_code != 201:
            logger.error(f"Failed to initialize file upload: {init_resp.text}")
            return False
        
        # Upload the file content
        with open(manifest_path, 'rb') as f:
            upload_resp = requests.put(
                f"{files_endpoint}/{filename}/content",
                headers={"Authorization": f"Bearer {token}"},
                data=f,
                verify=verify_ssl
            )
            
            if upload_resp.status_code != 200:
                logger.error(f"Failed to upload file content: {upload_resp.text}")
                return False
        
        # Commit the file upload
        commit_resp = requests.post(
            f"{files_endpoint}/{filename}/commit",
            headers=headers,
            verify=verify_ssl
        )
        
        if commit_resp.status_code != 200:
            logger.error(f"Failed to commit file upload: {commit_resp.text}")
            return False
        
        logger.info(f"Successfully uploaded manifest file to record {record_id}")
        
        # 2. Now update the record metadata to set the IIIF manifest field
        record_endpoint = f"{api_url}/records/{record_id}/draft"
        
        # Get the current record
        record_resp = requests.get(
            record_endpoint,
            headers=headers,
            verify=verify_ssl
        )
        
        if record_resp.status_code != 200:
            logger.error(f"Failed to get record: {record_resp.text}")
            return False
        
        record_data = record_resp.json()
        
        # Construct the manifest URL
        host = api_url.split('/api')[0]
        manifest_url = f"{host}/api/records/{record_id}/files/{filename}"
        
        # Update the record metadata with IIIF manifest URL
        if 'metadata' not in record_data:
            record_data['metadata'] = {}
            
        if 'custom_fields' not in record_data['metadata']:
            record_data['metadata']['custom_fields'] = {}
            
        # Set the IIIF manifest field
        record_data['metadata']['custom_fields']['iiif'] = {
            'manifest': manifest_url
        }
        
        # Update the record
        update_resp = requests.put(
            record_endpoint,
            headers=headers,
            json=record_data,
            verify=verify_ssl
        )
        
        if update_resp.status_code != 200:
            logger.error(f"Failed to update record metadata: {update_resp.text}")
            return False
            
        logger.info(f"Successfully updated record with IIIF manifest URL: {manifest_url}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating record with manifest: {str(e)}")
        return False

def main():
    """Main workflow function."""
    args = parse_arguments()
    
    # Adjust logging level if verbose
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Step 1: Upload book to InvenioRDM
    upload_success, record_id = upload_book(
        args.book_dir,
        args.api_url,
        args.token,
        args.verify_ssl,
        not args.no_publish
    )
    
    if not upload_success:
        logger.error("Book upload failed, exiting workflow")
        return 1
    
    # Step 2: Copy PDF to Cantaloupe
    copy_success, pdf_filename = copy_pdf_to_cantaloupe(
        record_id,
        args.book_dir,
        args.cantaloupe_dir,
        args.cantaloupe_url,
        args.verify_ssl
    )
    
    if not copy_success:
        logger.error("Failed to copy PDF to Cantaloupe, exiting workflow")
        return 1
    
    # Step 3: Generate IIIF manifest
    manifest_server = args.api_url.split('/api')[0]
    manifest_success, manifest_path = generate_manifest(
        args.book_dir,
        record_id,
        pdf_filename,
        args.cantaloupe_url,
        manifest_server
    )
    
    if not manifest_success:
        logger.error("Failed to generate manifest, exiting workflow")
        return 1
    
    # Step 4: Update record with manifest
    update_success = update_record_with_manifest(
        record_id,
        manifest_path,
        args.api_url,
        args.token,
        args.verify_ssl
    )
    
    if not update_success:
        logger.error("Failed to update record with manifest, exiting workflow")
        return 1
    
    # Workflow completed successfully
    logger.info("✓ Workflow completed successfully!")
    record_url = f"{args.api_url.split('/api')[0]}/records/{record_id}"
    
    print(f"""
Workflow Complete
----------------
Record ID: {record_id}
PDF: {pdf_filename}
Manifest: {os.path.basename(manifest_path)}

Record URL: {record_url}

To view in IIIF viewer, visit the record page and use the IIIF viewer button.
""")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
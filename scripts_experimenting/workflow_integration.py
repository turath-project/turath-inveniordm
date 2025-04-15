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
DEFAULT_CANTALOUPE_URL = "https://localhost:8183/iiif/3"
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
    parser.add_argument('--no-verify-ssl', action='store_true', help='Don\'t verify SSL certificates')
    parser.add_argument('--no-publish', action='store_true', help='Keep the record as a draft')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--metadata-file', help='Path to custom metadata JSON file')
    parser.add_argument('--no-hocr-images', action='store_true', help='Skip uploading HOCR and image files')
    
    args = parser.parse_args()
    
    # Handle SSL verification conflict
    if args.verify_ssl and args.no_verify_ssl:
        parser.error("--verify-ssl and --no-verify-ssl cannot be used together")
        
    # Set verify_ssl based on the flags
    if not hasattr(args, 'verify_ssl') or args.no_verify_ssl:
        args.verify_ssl = False
    
    return args

def upload_book(book_dir, api_url, token, verify_ssl=False, publish=True, metadata_file=None, no_hocr_images=False):
    """
    Upload a book to InvenioRDM using the upload_book.py script.
    
    Args:
        book_dir: Directory containing the book files
        api_url: InvenioRDM API URL
        token: API token
        verify_ssl: Whether to verify SSL certificates
        publish: Whether to publish the record
        metadata_file: Optional path to metadata file
        no_hocr_images: Skip uploading HOCR and image files
    
    Returns:
        Tuple of (success, record_id)
    """
    logger.info(f"Uploading book from {book_dir} to InvenioRDM")
    
    # Check if the book directory exists
    if not os.path.exists(book_dir):
        logger.error(f"Book directory does not exist: {book_dir}")
        return False, None
        
    # Check if the upload_book.py script exists
    script_path = "scripts/upload_book.py"
    if not os.path.exists(script_path):
        logger.error(f"Upload script not found: {script_path}")
        # Try looking in the current directory
        script_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "scripts/upload_book.py")
        if not os.path.exists(script_path):
            logger.error(f"Upload script not found at alternate location: {script_path}")
            return False, None
        else:
            logger.info(f"Found upload script at: {script_path}")
    
    # Prepare command
    cmd = [
        "python", script_path,
        "--book-dir", book_dir,
        "--api-url", api_url,
        "--token", token
    ]
    
    if not verify_ssl:
        cmd.append("--no-verify-ssl")
    
    if not publish:
        cmd.append("--draft")
        
    if no_hocr_images:
        cmd.append("--no-hocr-images")
    
    # If metadata file is provided, add it to the command
    if metadata_file and os.path.exists(metadata_file):
        cmd.extend(["--metadata-file", metadata_file])
        logger.info(f"Using metadata file: {metadata_file}")
    else:
        # Try to use default metadata file in the parent directory of book_dir
        default_metadata = os.path.join(os.path.dirname(book_dir), "metadata.json")
        if os.path.exists(default_metadata):
            cmd.extend(["--metadata-file", default_metadata])
            logger.info(f"Using default metadata file: {default_metadata}")
        else:
            logger.warning(f"No metadata file found. This may cause validation errors.")
    
    logger.info(f"Running command: {' '.join(cmd)}")
    
    # Try to verify API connectivity before running the command
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        headers = {"Authorization": f"Bearer {token}"}
        logger.info(f"Testing API connectivity to {api_url}")
        response = requests.get(f"{api_url}/records", headers=headers, verify=verify_ssl, timeout=10)
        
        if response.status_code == 200:
            logger.info("API connectivity test successful")
        else:
            logger.warning(f"API connectivity test failed with status code: {response.status_code}")
            logger.warning("Proceeding with upload attempt anyway...")
    except Exception as e:
        logger.warning(f"API connectivity test failed: {str(e)}")
        logger.warning("Proceeding with upload attempt anyway...")
    
    # Run the command with a timeout
    try:
        # Run the command with a timeout of 600 seconds (10 minutes)
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600)
        
        # Extract record ID from output
        output = result.stdout
        record_id = None
        
        # Parse output to find record ID
        for line in output.splitlines():
            if "Created record with ID" in line:
                record_id = line.split("ID:")[-1].strip()
                break
            if "Record ID:" in line:
                record_id = line.split("ID:")[-1].strip()
                break
            # Check for lines with just the ID printed directly
            if line.strip() and all(c.isalnum() or c in '-_' for c in line.strip()) and len(line.strip()) > 5:
                logger.debug(f"Found potential record ID in line: {line.strip()}")
                record_id = line.strip()
                break
        
        # If we didn't find the ID in stdout, try stderr as well
        if not record_id and result.stderr:
            for line in result.stderr.splitlines():
                if "Created draft record with ID:" in line:
                    record_id = line.split("ID:")[-1].strip()
                    break
                if "Record ID:" in line:
                    record_id = line.split("ID:")[-1].strip()
                    break
        
        # Still no ID, look for p1tqk-j8y47 pattern (alphanumeric-alphanumeric)
        if not record_id:
            id_pattern = r'\b([a-z0-9]{5})-([a-z0-9]{5})\b'
            import re
            for line in output.splitlines() + (result.stderr.splitlines() if result.stderr else []):
                match = re.search(id_pattern, line)
                if match:
                    record_id = match.group(0)
                    logger.info(f"Found record ID using pattern matching: {record_id}")
                    break
        
        if record_id:
            logger.info(f"Successfully uploaded book with record ID: {record_id}")
            return True, record_id
        else:
            logger.error("Record ID not found in output")
            logger.debug(f"Full stdout: {output}")
            logger.debug(f"Full stderr: {result.stderr}")
            return False, None
            
    except subprocess.TimeoutExpired:
        logger.error("Command timed out after 600 seconds")
        return False, None
    except subprocess.CalledProcessError as e:
        logger.error(f"Error uploading book: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error: {e.stderr}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
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
            # Replace localhost with 127.0.0.1 if present
            cantaloupe_url = cantaloupe_url.replace("localhost", "127.0.0.1")
            
            identifier = f"private%2F{record_id}%2F{pdf_filename}"
            info_url = f"{cantaloupe_url}/{identifier}/info.json"
            
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
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
    
    # Replace localhost with 127.0.0.1 if present
    cantaloupe_url = cantaloupe_url.replace("localhost", "127.0.0.1")
    manifest_server = manifest_server.replace("localhost", "127.0.0.1")
    
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
    
    # Replace localhost with 127.0.0.1 if present
    api_url = api_url.replace("localhost", "127.0.0.1")
    
    # Headers for API requests
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Disable SSL warnings if not verifying
    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # First check if the record is a draft or published
    try:
        # Try to get the draft version
        draft_endpoint = f"{api_url}/records/{record_id}/draft"
        draft_resp = requests.get(
            draft_endpoint,
            headers=headers,
            verify=verify_ssl
        )
        
        if draft_resp.status_code == 200:
            # Record is a draft
            logger.info(f"Record {record_id} is a draft")
            is_draft = True
        elif draft_resp.status_code == 404:
            # Draft not found, check if it's published
            published_endpoint = f"{api_url}/records/{record_id}"
            published_resp = requests.get(
                published_endpoint,
                headers=headers,
                verify=verify_ssl
            )
            
            if published_resp.status_code == 200:
                # Record is published
                logger.info(f"Record {record_id} is published")
                is_draft = False
            else:
                logger.error(f"Failed to find record {record_id}: {published_resp.text}")
                return False
        else:
            logger.error(f"Failed to check draft status: {draft_resp.text}")
            return False
        
        # If record is published, create a new draft
        if not is_draft:
            logger.info(f"Creating a new draft from published record {record_id}")
            create_draft_endpoint = f"{api_url}/records/{record_id}/draft"
            create_draft_resp = requests.post(
                create_draft_endpoint,
                headers=headers,
                verify=verify_ssl
            )
            
            if create_draft_resp.status_code != 201:
                logger.error(f"Failed to create draft from published record: {create_draft_resp.text}")
                return False
            
            logger.info(f"Successfully created draft from published record {record_id}")
            is_draft = True
    
        # Set filename
        filename = os.path.basename(manifest_path)
        
        # Check if the manifest file already exists and if bucket is locked
        files_list_endpoint = f"{api_url}/records/{record_id}/draft/files"
        files_resp = requests.get(
            files_list_endpoint,
            headers=headers,
            verify=verify_ssl
        )
        
        file_exists = False
        bucket_locked = False
        
        if files_resp.status_code == 200:
            files = files_resp.json().get('entries', [])
            for file in files:
                if file.get('key') == filename:
                    file_exists = True
                    logger.info(f"File {filename} already exists in the record")
                    break
        
        # Try to delete existing file if it exists
        if file_exists:
            delete_endpoint = f"{api_url}/records/{record_id}/draft/files/{filename}"
            delete_resp = requests.delete(
                delete_endpoint,
                headers=headers,
                verify=verify_ssl
            )
            
            if delete_resp.status_code == 403 and "Bucket is locked" in delete_resp.text:
                logger.warning("Bucket is locked for modifications, cannot delete or upload file")
                bucket_locked = True
            elif delete_resp.status_code != 204:
                logger.warning(f"Failed to delete existing file: {delete_resp.text}")
                # Continue anyway
            else:
                logger.info(f"Successfully deleted existing manifest file")
                file_exists = False
        
        # If bucket is not locked and file doesn't exist (or was deleted), upload the new manifest
        if not bucket_locked and not file_exists:
            # 1. Upload the manifest file
            files_endpoint = f"{api_url}/records/{record_id}/draft/files"
            
            # Initialize file upload
            init_data = {"key": filename}
            
            # Start the file upload process
            init_resp = requests.post(
                files_endpoint,
                headers=headers,
                json=[init_data],
                verify=verify_ssl
            )
            
            if init_resp.status_code != 201:
                if "File with key manifest.json already exists" in init_resp.text:
                    logger.warning(f"File exists and cannot be replaced")
                    bucket_locked = True
                else:
                    logger.error(f"Failed to initialize file upload: {init_resp.text}")
                    return False
            
            # Only continue with upload if initialization was successful
            if not bucket_locked:
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
        host = host.replace("localhost", "127.0.0.1")
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
        
        # 3. Publish the draft if it was originally published
        if not is_draft:
            logger.info(f"Re-publishing record {record_id}")
            publish_endpoint = f"{api_url}/records/{record_id}/draft/actions/publish"
            publish_resp = requests.post(
                publish_endpoint,
                headers=headers,
                verify=verify_ssl
            )
            
            if publish_resp.status_code != 202:
                logger.error(f"Failed to re-publish record: {publish_resp.text}")
                return False
                
            logger.info(f"Successfully re-published record {record_id}")
        
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
        
    # Replace localhost with 127.0.0.1 in all URLs
    args.api_url = args.api_url.replace("localhost", "127.0.0.1")
    args.cantaloupe_url = args.cantaloupe_url.replace("localhost", "127.0.0.1")
    
    # Step 1: Upload book to InvenioRDM
    upload_success, record_id = upload_book(
        args.book_dir,
        args.api_url,
        args.token,
        args.verify_ssl,
        not args.no_publish,
        args.metadata_file,
        args.no_hocr_images
    )
    
    if not upload_success:
        logger.error("Book upload failed, exiting workflow")
        return 1
        
    logger.info(f"✓ Book uploaded successfully with record ID: {record_id}")
    
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
        
    logger.info(f"✓ PDF {pdf_filename} copied to Cantaloupe successfully")
    
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
        
    logger.info(f"✓ Manifest generated successfully at {manifest_path}")
    
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
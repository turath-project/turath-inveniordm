#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Create a test record with IIIF manifest uploaded as a file.
"""

import os
import sys
import json
import logging
import argparse
import requests
import time
import urllib3
import re

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('create_test_record')

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Create a test record with IIIF manifest as a file")
    parser.add_argument('--api-url', required=True, help='InvenioRDM API URL (e.g., https://127.0.0.1:5000/api)')
    parser.add_argument('--token', required=True, help='API token for InvenioRDM')
    parser.add_argument('--manifest-file', required=True, help='Path to the IIIF manifest JSON file')
    parser.add_argument('--verify-ssl', action='store_true', help='Verify SSL certificates')
    parser.add_argument('--publish', action='store_true', help='Publish the record after creation')
    parser.add_argument('--retries', type=int, default=3, help='Number of connection retries')
    return parser.parse_args()

def validate_metadata(metadata):
    """Validate metadata before submitting."""
    # Make a deep copy to avoid modifying the original
    cleaned = json.loads(json.dumps(metadata))
    
    # Ensure all required fields exist
    if "metadata" not in cleaned:
        cleaned["metadata"] = {}
    
    # Required fields for publication
    required_fields = [
        "title", "publication_date", "creators", "resource_type", "languages"
    ]
    
    for field in required_fields:
        if field not in cleaned.get("metadata", {}):
            if field == "creators":
                # Add default creator
                cleaned["metadata"]["creators"] = [{
                    "person_or_org": {
                        "family_name": "Test",
                        "given_name": "User",
                        "type": "personal"
                    },
                    "role": "author"
                }]
            elif field == "title":
                cleaned["metadata"]["title"] = "IIIF Test Record"
            elif field == "publication_date":
                cleaned["metadata"]["publication_date"] = "2023-04-14"
            elif field == "resource_type":
                cleaned["metadata"]["resource_type"] = {"id": "publication-book"}
            elif field == "languages":
                cleaned["metadata"]["languages"] = [{"id": "eng"}]
    
    # Make sure publication date is in the correct format
    pub_date = cleaned["metadata"].get("publication_date", "2023-04-14")
    if re.match(r'^\d{4}$', pub_date):  # YYYY
        cleaned["metadata"]["publication_date"] = f"{pub_date}-01-01"
    elif re.match(r'^\d{4}-\d{2}$', pub_date):  # YYYY-MM
        cleaned["metadata"]["publication_date"] = f"{pub_date}-01"
    
    # Ensure identifiers exist
    if "identifiers" not in cleaned["metadata"]:
        cleaned["metadata"]["identifiers"] = [
            {
                "identifier": "test-iiif-manifest",
                "scheme": "other"
            }
        ]
    
    # Ensure description exists
    if "description" not in cleaned["metadata"]:
        cleaned["metadata"]["description"] = "Test record for IIIF integration testing with manifest file"
    
    # Make sure access rights are defined
    if "access" not in cleaned:
        cleaned["access"] = {
            "record": "public",
            "files": "public"
        }
    
    # Enable files
    if "files" not in cleaned:
        cleaned["files"] = {
            "enabled": True
        }
    
    return cleaned

def create_test_record_with_manifest(api_url, token, manifest_file, verify_ssl=False, publish=False, retries=3):
    """Create a test record with IIIF manifest file."""
    # Set up API headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Prepare metadata
    metadata = {
        "metadata": {
            "title": "IIIF Test Record with Manifest File",
            "publication_date": "2023-04-14",
            "resource_type": {"id": "publication-book"},
            "creators": [
                {
                    "person_or_org": {
                        "family_name": "Test",
                        "given_name": "User",
                        "type": "personal"
                    },
                    "role": "author"
                }
            ],
            "languages": [{"id": "eng"}],
            "description": "Test record for IIIF integration testing with manifest file",
            "identifiers": [
                {
                    "identifier": "test-iiif-manifest",
                    "scheme": "other"
                }
            ]
        },
        "access": {
            "record": "public",
            "files": "public"
        },
        "files": {
            "enabled": True
        }
    }
    
    # Validate metadata
    metadata = validate_metadata(metadata)
    
    # Create the record with retries
    logger.info(f"Creating draft record with title: {metadata['metadata']['title']}")
    endpoint = f"{api_url}/records"
    
    record_id = None
    
    for attempt in range(retries):
        try:
            response = requests.post(
                endpoint,
                json=metadata,
                headers=headers,
                verify=verify_ssl,
                timeout=30
            )
            
            if response.status_code != 201:
                error_msg = f"Failed to create record. Status code: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('message', '')}"
                    logger.debug(f"Full error: {json.dumps(error_data, indent=2)}")
                except:
                    error_msg += f" - {response.text}"
                
                logger.error(error_msg)
                
                if attempt < retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds... (Attempt {attempt+1}/{retries})")
                    time.sleep(wait_time)
                    continue
                return None
            
            record_data = response.json()
            record_id = record_data.get("id")
            
            logger.info(f"Created draft record with ID: {record_id}")
            break
            
        except Exception as e:
            logger.error(f"Error creating record: {str(e)}")
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds... (Attempt {attempt+1}/{retries})")
                time.sleep(wait_time)
            else:
                return None
    
    if not record_id:
        return None
    
    # Upload manifest file
    logger.info(f"Uploading manifest file to record: {record_id}")
    
    # Step 1: Initialize file upload
    files_endpoint = f"{api_url}/records/{record_id}/draft/files"
    manifest_filename = os.path.basename(manifest_file)
    
    init_data = [{"key": manifest_filename}]
    
    for attempt in range(retries):
        try:
            init_response = requests.post(
                files_endpoint,
                json=init_data,
                headers=headers,
                verify=verify_ssl,
                timeout=30
            )
            
            if init_response.status_code != 201:
                error_msg = f"Failed to initialize file upload. Status code: {init_response.status_code}"
                try:
                    error_data = init_response.json()
                    error_msg += f" - {error_data.get('message', '')}"
                except:
                    error_msg += f" - {init_response.text}"
                
                logger.error(error_msg)
                
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds... (Attempt {attempt+1}/{retries})")
                    time.sleep(wait_time)
                    continue
                return record_id
            
            logger.info(f"Initialized file upload: {manifest_filename}")
            break
            
        except Exception as e:
            logger.error(f"Error initializing file upload: {str(e)}")
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds... (Attempt {attempt+1}/{retries})")
                time.sleep(wait_time)
            else:
                return record_id

    # Step 2: Upload file content
    upload_endpoint = f"{api_url}/records/{record_id}/draft/files/{manifest_filename}/content"
    
    for attempt in range(retries):
        try:
            with open(manifest_file, 'rb') as f:
                upload_headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/octet-stream"
                }
                upload_response = requests.put(
                    upload_endpoint,
                    data=f,
                    headers=upload_headers,
                    verify=verify_ssl,
                    timeout=60
                )
            
            if upload_response.status_code != 200:
                error_msg = f"Failed to upload file content. Status code: {upload_response.status_code}"
                try:
                    error_data = upload_response.json()
                    error_msg += f" - {error_data.get('message', '')}"
                except:
                    error_msg += f" - {upload_response.text}"
                
                logger.error(error_msg)
                
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds... (Attempt {attempt+1}/{retries})")
                    time.sleep(wait_time)
                    continue
                return record_id
            
            logger.info(f"Uploaded file content: {manifest_filename}")
            break
            
        except Exception as e:
            logger.error(f"Error uploading file content: {str(e)}")
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds... (Attempt {attempt+1}/{retries})")
                time.sleep(wait_time)
            else:
                return record_id
    
    # Step 3: Commit file upload
    commit_endpoint = f"{api_url}/records/{record_id}/draft/files/{manifest_filename}/commit"
    
    for attempt in range(retries):
        try:
            commit_response = requests.post(
                commit_endpoint,
                headers=headers,
                verify=verify_ssl,
                timeout=30
            )
            
            if commit_response.status_code != 200:
                error_msg = f"Failed to commit file. Status code: {commit_response.status_code}"
                try:
                    error_data = commit_response.json()
                    error_msg += f" - {error_data.get('message', '')}"
                except:
                    error_msg += f" - {commit_response.text}"
                
                logger.error(error_msg)
                
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds... (Attempt {attempt+1}/{retries})")
                    time.sleep(wait_time)
                    continue
                return record_id
            
            logger.info(f"Committed file: {manifest_filename}")
            break
            
        except Exception as e:
            logger.error(f"Error committing file: {str(e)}")
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds... (Attempt {attempt+1}/{retries})")
                time.sleep(wait_time)
            else:
                return record_id
    
    # Step 4: Update record metadata to point to the manifest file
    api_base = api_url.rsplit('/api', 1)[0]
    manifest_file_url = f"{api_base}/records/{record_id}/files/{manifest_filename}"
    
    logger.info(f"Updating record metadata with manifest file URL: {manifest_file_url}")
    update_endpoint = f"{api_url}/records/{record_id}/draft"
    
    # Get current record data first to preserve all metadata
    get_record_endpoint = f"{api_url}/records/{record_id}/draft"
    record_data = {}
    
    try:
        get_response = requests.get(
            get_record_endpoint,
            headers=headers,
            verify=verify_ssl,
            timeout=30
        )
        
        if get_response.status_code == 200:
            record_data = get_response.json()
            logger.info(f"Retrieved current record data")
        else:
            logger.warning(f"Failed to get current record data. Will update only manifest URL.")
    except Exception as e:
        logger.warning(f"Error retrieving record data: {str(e)}")
    
    # Prepare update data
    if record_data:
        update_data = record_data
        if "custom_fields" not in update_data:
            update_data["custom_fields"] = {}
        update_data["custom_fields"]["turath:iiif_manifest"] = manifest_file_url
    else:
        update_data = {
            "custom_fields": {
                "turath:iiif_manifest": manifest_file_url
            }
        }
    
    # Ensure all required fields are included
    update_data = validate_metadata(update_data)
    
    for attempt in range(retries):
        try:
            update_response = requests.put(
                update_endpoint,
                json=update_data,
                headers=headers,
                verify=verify_ssl,
                timeout=30
            )
            
            if update_response.status_code != 200:
                error_msg = f"Failed to update record metadata. Status code: {update_response.status_code}"
                try:
                    error_data = update_response.json()
                    error_msg += f" - {error_data.get('message', '')}"
                except:
                    error_msg += f" - {update_response.text}"
                
                logger.error(error_msg)
                
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds... (Attempt {attempt+1}/{retries})")
                    time.sleep(wait_time)
                    continue
                return record_id
            
            logger.info(f"Updated record metadata with manifest file URL")
            break
            
        except Exception as e:
            logger.error(f"Error updating record metadata: {str(e)}")
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds... (Attempt {attempt+1}/{retries})")
                time.sleep(wait_time)
            else:
                return record_id
    
    # Step 5: Publish record if requested
    if publish:
        logger.info(f"Publishing record: {record_id}")
        publish_endpoint = f"{api_url}/records/{record_id}/draft/actions/publish"
        
        for pub_attempt in range(retries):
            try:
                publish_response = requests.post(
                    publish_endpoint,
                    headers=headers,
                    verify=verify_ssl,
                    timeout=30
                )
                
                if publish_response.status_code != 202:
                    error_msg = f"Failed to publish record. Status code: {publish_response.status_code}"
                    try:
                        error_data = publish_response.json()
                        error_msg += f" - {error_data.get('message', '')}"
                        logger.debug(f"Full error: {json.dumps(error_data, indent=2)}")
                        
                        # Extract validation errors if available
                        if 'errors' in error_data:
                            for error in error_data['errors']:
                                field = error.get('field', 'unknown field')
                                messages = error.get('messages', [])
                                logger.error(f"Validation error in {field}: {', '.join(messages)}")
                    except:
                        error_msg += f" - {publish_response.text}"
                    
                    logger.error(error_msg)
                    
                    if pub_attempt < retries - 1:
                        wait_time = 2 ** pub_attempt
                        logger.info(f"Retrying publication in {wait_time} seconds... (Attempt {pub_attempt+1}/{retries})")
                        time.sleep(wait_time)
                        continue
                    
                    logger.info(f"Record created as draft with ID: {record_id}")
                    return record_id
                
                logger.info(f"Successfully published record: {record_id}")
                break
                
            except Exception as e:
                logger.error(f"Error publishing record: {str(e)}")
                if pub_attempt < retries - 1:
                    wait_time = 2 ** pub_attempt
                    logger.info(f"Retrying publication in {wait_time} seconds... (Attempt {pub_attempt+1}/{retries})")
                    time.sleep(wait_time)
                else:
                    logger.info(f"Record created as draft with ID: {record_id}")
                    return record_id
    
    return record_id

def main():
    """Main function."""
    args = parse_arguments()
    
    # Make sure API URL uses HTTPS
    api_url = args.api_url
    if api_url.startswith("http://"):
        api_url = "https://" + api_url[7:]
        logger.info(f"Converted API URL to HTTPS: {api_url}")
    
    record_id = create_test_record_with_manifest(
        api_url=api_url,
        token=args.token,
        manifest_file=args.manifest_file,
        verify_ssl=args.verify_ssl,
        publish=args.publish,
        retries=args.retries
    )
    
    if record_id:
        logger.info(f"Test record created successfully with ID: {record_id}")
        api_base = api_url.rsplit('/api', 1)[0]
        logger.info(f"You can view it at: {api_base}/records/{record_id}")
        return 0
    else:
        logger.error("Failed to create test record")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Book importer script for Turath InvenioRDM.

This script handles importing books from the `books` directory into InvenioRDM,
properly organizing files and creating records with IIIF manifests.
"""
print ("This is only working with INVENIO_API_TOKEN authentication in .env ")
import os
import sys
import json
import shutil
import argparse
import requests
from pathlib import Path
from pprint import pprint
import datetime
import dotenv
import glob
import time
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

# Load environment variables from .env file
dotenv.load_dotenv()

# Import configuration
from config import (
    API_BASE_URL, 
    API_TOKEN as DEFAULT_API_TOKEN,
    IIIF_SERVER_URL,
    IIIF_STORAGE_PATH
)

# Will be set via command line argument, with default from config
API_TOKEN = DEFAULT_API_TOKEN


def setup_argparse():
    """Setup argument parser."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="Import books to InvenioRDM with IIIF support")
    parser.add_argument("book_dirs", nargs='+', help="Directories containing book files to import")
    parser.add_argument("--storage-path", default=IIIF_STORAGE_PATH,
                        help=f"Path to storage directory (default: {IIIF_STORAGE_PATH})")
    parser.add_argument("--server-url", default=IIIF_SERVER_URL,
                        help=f"URL of the IIIF server (default: {IIIF_SERVER_URL})")
    parser.add_argument("--token", default=os.environ.get("INVENIO_API_TOKEN"),
                        help="InvenioRDM API token (can also be set via INVENIO_API_TOKEN env var)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only display what would be done without actually importing")
    parser.add_argument("--username", default=os.environ.get("INVENIO_USERNAME"),
                        help="Username for basic authentication (can also be set via INVENIO_USERNAME env var)")
    parser.add_argument("--password", default=os.environ.get("INVENIO_PASSWORD"),
                        help="Password for basic authentication (can also be set via INVENIO_PASSWORD env var)")
    parser.add_argument("--skip-files", action="store_true", 
                        help="Skip uploading files to the record")
    return parser.parse_args()


def validate_book_directory(book_dir):
    """Validate that a book directory has all required components."""
    # Check that the directory exists
    if not os.path.isdir(book_dir):
        print(f"Error: {book_dir} is not a directory")
        return False
    
    # Check for manifest file
    manifest_path = os.path.join(book_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        print(f"Error: {book_dir} does not have a manifest.json file")
        return False
    
    # Check for pages directory 
    pages_dir = os.path.join(book_dir, "pages")
    if not os.path.isdir(pages_dir):
        print(f"Error: {book_dir} does not have a pages directory")
        return False
    
    # Validate that pages directory has image files
    has_images = False
    for file in os.listdir(pages_dir):
        if file.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
            has_images = True
            break
    
    if not has_images:
        print(f"Warning: {pages_dir} does not contain any image files")
    
    # All checks passed
    return True


def copy_to_storage(book_dir, storage_path, book_id):
    """Copy book files to permanent storage location."""
    # Create target directory
    target_dir = os.path.join(storage_path, book_id)
    os.makedirs(target_dir, exist_ok=True)
    
    # Copy manifest file
    manifest_path = os.path.join(book_dir, "manifest.json")
    if os.path.exists(manifest_path):
        shutil.copy2(manifest_path, os.path.join(target_dir, "manifest.json"))
    
    # Copy pages directory
    source_pages = os.path.join(book_dir, "pages")
    target_pages = os.path.join(target_dir, "pages")
    if os.path.exists(source_pages):
        os.makedirs(target_pages, exist_ok=True)
        for file in os.listdir(source_pages):
            source_file = os.path.join(source_pages, file)
            if os.path.isfile(source_file):
                shutil.copy2(source_file, os.path.join(target_pages, file))
    
    # Copy HOCR directory if it exists
    source_hocr = os.path.join(book_dir, "hocr")
    target_hocr = os.path.join(target_dir, "hocr")
    if os.path.exists(source_hocr):
        os.makedirs(target_hocr, exist_ok=True)
        for file in os.listdir(source_hocr):
            source_file = os.path.join(source_hocr, file)
            if os.path.isfile(source_file):
                shutil.copy2(source_file, os.path.join(target_hocr, file))
    
    return target_dir


def extract_book_info(book_dir):
    """Extract book information from the directory name and manifest."""
    from pathlib import Path
    
    book_path = Path(book_dir)
    book_name = book_path.name
    
    # Try to get info from manifest
    manifest_path = book_path / "manifest.json"
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    title = manifest.get("label", book_name)
    
    # Look for metadata in the manifest
    metadata = {}
    if "metadata" in manifest:
        for item in manifest["metadata"]:
            if "label" in item and "value" in item:
                if item["label"] == "Author":
                    metadata["author"] = item["value"]
                elif item["label"] == "Publication Date":
                    metadata["publication_date"] = item["value"]
                elif item["label"] == "Description":
                    metadata["description"] = item["value"]
    
    # Create a book info dictionary
    book_info = {
        "title": title,
        "book_id": book_name.lower().replace(" ", "-"),
        **metadata
    }
    
    return book_info


def update_manifest(manifest_path, server_url, book_id):
    """Update the manifest to point to the correct IIIF server URLs."""
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    # Update image URLs
    if "sequences" in manifest:
        for sequence in manifest["sequences"]:
            if "canvases" in sequence:
                for canvas in sequence["canvases"]:
                    if "images" in canvas:
                        for image in canvas["images"]:
                            if "resource" in image:
                                # Update the image resource URL
                                old_url = image["resource"].get("@id", "")
                                image_name = old_url.split("/")[-1]
                                new_url = f"{server_url}/{book_id}/pages/{image_name}"
                                image["resource"]["@id"] = new_url
                                
                                # Update service URL if present
                                if "service" in image["resource"]:
                                    old_service = image["resource"]["service"].get("@id", "")
                                    new_service = f"{server_url}/{book_id}/pages"
                                    image["resource"]["service"]["@id"] = new_service
    
    # Update HOCR annotation URLs if present
    if "sequences" in manifest:
        for sequence in manifest["sequences"]:
            if "canvases" in sequence:
                for canvas in sequence["canvases"]:
                    if "otherContent" in canvas:
                        for content in canvas["otherContent"]:
                            old_content_url = content.get("@id", "")
                            # Extract the page ID or other relevant info
                            page_id = old_content_url.split("/")[-2]
                            new_content_url = f"{server_url}/{book_id}/annotations/{page_id}/line"
                            content["@id"] = new_content_url
    
    # Write updated manifest
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return manifest


def create_record(book_info, manifest_url=None, api_token=None, username=None, password=None):
    """Create a record in InvenioRDM."""
    metadata = prepare_metadata(book_info, manifest_url)
    
    # Print API base URL for debugging
    print(f"Using API base URL: {API_BASE_URL}")
    
    # Determine API endpoint for InvenioRDM v12.0.0
    if API_BASE_URL.endswith('/api'):
        api_endpoint = f"{API_BASE_URL}/records"  # Avoid duplicating 'api'
    else:
        api_endpoint = f"{API_BASE_URL}/api/records"  # Standard InvenioRDM records endpoint
    print(f"Creating record using API endpoint: {api_endpoint}")
    
    # Print metadata size and content type
    import json
    metadata_json = json.dumps(metadata)
    print(f"Metadata size: {len(metadata_json)} bytes")
    print(f"First 200 chars of metadata: {metadata_json[:200]}...")
    
    # Disable SSL verification for development environments
    verify_ssl = True
    if not API_BASE_URL.startswith("https://turath.io"):
        print("Notice: SSL verification disabled for development environment")
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        verify_ssl = False
    
    # Setup authentication
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    auth = None
    
    # Try token authentication first
    if api_token:
        headers['Authorization'] = f'Bearer {api_token}'
        print("Using token authentication")
    # Fall back to basic authentication if token not available
    elif username and password:
        auth = (username, password)
        print(f"Using basic authentication with username: {username}")
    else:
        print("Error: No authentication method provided. Either token or username/password is required.")
        return None
    
    try:
        print("\nSending request to create record...")
        print(f"Headers: {headers}")
        print(f"Using auth: {bool(auth)}")
        print(f"SSL verification: {verify_ssl}")
        
        response = requests.post(
            api_endpoint, 
            json=metadata,
            headers=headers,
            auth=auth,
            verify=verify_ssl,
            timeout=60
        )
        
        print(f"\nResponse status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        
        # Check if the request was successful
        if response.status_code == 201:
            print("Record created successfully!")
            record_data = response.json()
            record_id = record_data.get('id')
            print(f"Record ID: {record_id}")
            return record_id
        else:
            print(f"Failed to create record. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except requests.exceptions.SSLError as e:
        print(f"SSL Error: {str(e)}")
        print("Consider using the --insecure flag to disable SSL verification if this is a development environment.")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: {str(e)}")
        print("Check if the InvenioRDM server is running and accessible.")
        return None
    except requests.exceptions.Timeout as e:
        print(f"Timeout Error: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None


def prepare_metadata(book_info, manifest_url):
    """Prepare metadata for the record."""
    metadata = {
        "access": {
            "record": "public",
            "files": "public"
        },
        "files": {
            "enabled": True
        },
        "metadata": {
            "title": book_info["title"],
            "publication_date": book_info.get("publication_date", datetime.date.today().strftime("%Y-%m-%d")),
            "resource_type": {"id": "publication-book"},
            "creators": [
                {
                    "person_or_org": {
                        "name": book_info.get("author", "Unknown Author"),
                        "type": "personal"
                    }
                }
            ],
            "description": book_info.get("description", "Book imported with IIIF support")
        }
    }
    
    # Add IIIF manifest URL to custom fields if available
    if manifest_url:
        if "custom_fields" not in metadata:
            metadata["custom_fields"] = {}
        metadata["custom_fields"]["turath:iiif_manifest"] = manifest_url
    
    # Add extracted text from HOCR files if available
    if "extracted_text" in book_info:
        # Create a searchable text field in the description
        extracted_summary = "OCR Text Index:\n\n"
        
        # Create the full OCR text for the custom field
        full_text_parts = []
        structured_ocr = []
        
        for item in book_info["extracted_text"]:
            page_text = item["text"].strip()
            if not page_text:
                continue
                
            # Add to full text
            full_text_parts.append(page_text)
            
            # Add to summary with page info 
            if item["page"]:
                extracted_summary += f"Page {item['page']} ({item['file']}):\n"
            else:
                extracted_summary += f"File {item['file']}:\n"
            
            # Add a preview of the text (first 100 characters)
            text_preview = page_text[:150] + "..." if len(page_text) > 150 else page_text
            extracted_summary += f"{text_preview}\n\n"
            
            # Add to structured OCR data
            structured_ocr.append({
                "page": item["page"],
                "file": item["file"],
                "text": item["text"],
                # Include word-level data if needed for future use
                "words": item.get("words", [])
            })
        
        # Append text summary to the description
        if metadata["metadata"]["description"]:
            metadata["metadata"]["description"] += "\n\n" + extracted_summary
        else:
            metadata["metadata"]["description"] = extracted_summary
        
        # Store both full text and structured OCR data in custom fields
        if "custom_fields" not in metadata:
            metadata["custom_fields"] = {}
            
        # Full text (limited to avoid overly large records)
        metadata["custom_fields"]["turath:ocr_text"] = " ".join(full_text_parts)[:30000]
        
        # Store structured OCR data as JSON (but limit size to avoid issues)
        # This can be used for more advanced features in the future
        metadata["custom_fields"]["turath:ocr_structured"] = json.dumps(structured_ocr[:20], ensure_ascii=False)  # Limit to 20 pages
    
    return metadata


def extract_text_from_hocr(hocr_file_path):
    """Extract text content from an HOCR file using BeautifulSoup for complete extraction.
    
    Args:
        hocr_file_path: Path to the HOCR file
        
    Returns:
        dict: Dictionary containing the extracted text and metadata
    """
    try:
        # Read the HOCR file
        with open(hocr_file_path, 'r', encoding='utf-8') as f:
            hocr_content = f.read()
        
        # Parse with BeautifulSoup - much more robust than ElementTree for HOCR
        soup = BeautifulSoup(hocr_content, 'html.parser')
        
        # Extract filename and page number
        filename = os.path.basename(hocr_file_path)
        page_num = None
        match = re.match(r'(\d+)\.hocr', filename)
        if match:
            try:
                page_num = int(match.group(1))
            except ValueError:
                pass
        
        # Dictionary to store all extracted content
        extraction = {
            'text': '',
            'file': filename,
            'page': page_num,
            'words': [],
            'lines': [],
            'paragraphs': []
        }
        
        # Extract all text content at different levels
        # 1. Word level extraction (most granular)
        words = []
        for word in soup.find_all(class_='ocrx_word'):
            word_text = word.get_text().strip()
            if word_text:
                words.append(word_text)
                
                # Extract coordinates if available
                coords = {}
                if word.get('title'):
                    bbox_match = re.search(r'bbox (\d+) (\d+) (\d+) (\d+)', word.get('title'))
                    if bbox_match:
                        x1, y1, x2, y2 = map(int, bbox_match.groups())
                        coords = {
                            'x': x1, 
                            'y': y1, 
                            'width': x2 - x1, 
                            'height': y2 - y1
                        }
                
                extraction['words'].append({
                    'text': word_text,
                    'coords': coords
                })
        
        # 2. Line level extraction
        lines = []
        for line in soup.find_all(class_='ocr_line'):
            line_text = line.get_text().strip()
            if line_text:
                lines.append(line_text)
                extraction['lines'].append(line_text)
        
        # 3. Paragraph level extraction 
        paragraphs = []
        for para in soup.find_all(class_='ocr_par'):
            para_text = para.get_text().strip()
            if para_text:
                paragraphs.append(para_text)
                extraction['paragraphs'].append(para_text)
        
        # 4. Full page text (use paragraphs if available, otherwise lines)
        if paragraphs:
            extraction['text'] = '\n\n'.join(paragraphs)
        elif lines:
            extraction['text'] = '\n'.join(lines)
        else:
            extraction['text'] = ' '.join(words)
        
        return extraction
    
    except Exception as e:
        print(f"Error extracting text from HOCR file {hocr_file_path}: {str(e)}")
        return {
            'text': '',
            'file': os.path.basename(hocr_file_path),
            'page': None,
            'words': [],
            'lines': [],
            'paragraphs': []
        }


def extract_book_text(book_dir):
    """Extract text from all HOCR files in a book directory.
    
    Args:
        book_dir: Directory containing the book files
        
    Returns:
        list: List of dictionaries with extracted text and metadata
    """
    hocr_files = []
    for root, dirs, files in os.walk(book_dir):
        for file in files:
            if file.endswith('.hocr'):
                hocr_files.append(os.path.join(root, file))
    
    # Sort HOCR files by name to preserve page order
    hocr_files.sort()
    
    # Extract text from each HOCR file
    extracted_texts = []
    for hocr_file in hocr_files:
        extracted = extract_text_from_hocr(hocr_file)
        if extracted['text']:
            extracted_texts.append(extracted)
    
    # Sort by page number if available
    extracted_texts.sort(key=lambda x: (x['page'] if x['page'] is not None else float('inf')))
    
    return extracted_texts


def upload_files(record_id, book_dir, api_token, batch_size=10, username=None, password=None, max_retries=3):
    """Upload files to the record created in InvenioRDM.
    
    Args:
        record_id (str): ID of the record to upload files to.
        book_dir (str): Directory containing the files to upload.
        api_token (str): API token for authentication.
        batch_size (int): Number of files to upload in each batch.
        username (str): Username for basic authentication if token is not available.
        password (str): Password for basic authentication if token is not available.
        max_retries (int): Maximum number of retries for failed uploads.
        
    Returns:
        bool: True if all files were uploaded successfully, False otherwise.
    """
    # Get all files in the book directory
    all_files = []
    for ext in ['tif', 'hocr', 'alto.xml']:
        all_files.extend(glob.glob(os.path.join(book_dir, f'*.{ext}')))
        all_files.extend(glob.glob(os.path.join(book_dir, f'**/*.{ext}')))
    
    # Sort files by size (smallest first) to reduce likelihood of timeouts
    all_files.sort(key=os.path.getsize)
    
    # No need to limit files since InvenioRDM has been configured with a higher limit
    print(f"Found {len(all_files)} files to upload")
    
    uploaded_files = []
    file_count = len(all_files)
    
    # Disable SSL verification for development environments
    verify_ssl = True
    if not API_BASE_URL.startswith("https://turath.io"):
        print("Notice: SSL verification disabled for development environment")
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        verify_ssl = False
    
    # Determine authentication method
    auth = None
    headers = {'Accept': 'application/json'}
    
    if api_token:
        # Token authentication
        headers['Authorization'] = f'Bearer {api_token}'
    elif username and password:
        # Basic authentication
        auth = (username, password)
    else:
        print("No authentication method provided. Token or username/password is required.")
        return False
    
    api_base = API_BASE_URL
    if api_base.endswith('/api'):
        api_endpoint = f"{api_base}/records/{record_id}/draft/files"
    else:
        api_endpoint = f"{api_base}/api/records/{record_id}/draft/files"
    
    # Process files
    for file_path in all_files:
        file_name = os.path.basename(file_path)
        print(f"Processing file: {file_name}")
        
        # Retry logic for more resilient uploads
        for retry in range(max_retries):
            try:
                # Step 1: Initialize the file upload
                init_response = requests.post(
                    api_endpoint,
                    json=[{"key": file_name}],
                    headers=headers,
                    auth=auth,
                    verify=verify_ssl
                )
                
                if init_response.status_code != 201:
                    print(f"Failed to initialize file {file_name}. Status code: {init_response.status_code}")
                    print(f"Response: {init_response.text}")
                    
                    # If we hit the file limit, stop trying to upload more files
                    if "max amount per record" in init_response.text:
                        print(f"Reached file limit for this record. Uploaded {len(uploaded_files)}/{file_count} files.")
                        return len(uploaded_files) > 0
                    
                    # If this is not the last retry, try again
                    if retry < max_retries - 1:
                        print(f"Retrying initialization ({retry + 1}/{max_retries})...")
                        time.sleep(1)  # Small delay before retry
                        continue
                    break
                
                # Step 2: Upload the file content
                with open(file_path, 'rb') as file_content:
                    upload_response = requests.put(
                        f"{api_endpoint}/{file_name}/content",
                        data=file_content,
                        headers=headers,
                        auth=auth,
                        verify=verify_ssl
                    )
                
                if upload_response.status_code != 200:
                    print(f"Failed to upload content for {file_name}. Status code: {upload_response.status_code}")
                    print(f"Response: {upload_response.text}")
                    
                    # If this is not the last retry, try again
                    if retry < max_retries - 1:
                        print(f"Retrying upload ({retry + 1}/{max_retries})...")
                        time.sleep(1)  # Small delay before retry
                        continue
                    break
                
                # Step 3: Commit the file upload
                commit_response = requests.post(
                    f"{api_endpoint}/{file_name}/commit",
                    headers=headers,
                    auth=auth,
                    verify=verify_ssl
                )
                
                if commit_response.status_code != 200:
                    print(f"Failed to commit file {file_name}. Status code: {commit_response.status_code}")
                    print(f"Response: {commit_response.text}")
                    
                    # If this is not the last retry, try again
                    if retry < max_retries - 1:
                        print(f"Retrying commit ({retry + 1}/{max_retries})...")
                        time.sleep(1)  # Small delay before retry
                        continue
                    break
                
                print(f"Successfully uploaded and committed file: {file_name}")
                uploaded_files.append(file_name)
                break  # Break out of retry loop on success
                
            except requests.exceptions.SSLError as e:
                print(f"SSL Error: {str(e)}")
                if retry < max_retries - 1:
                    print(f"Retrying due to SSL error ({retry + 1}/{max_retries})...")
                    time.sleep(2)  # Longer delay for SSL errors
                    continue
            except Exception as e:
                print(f"Exception during upload of {file_name}: {str(e)}")
                if retry < max_retries - 1:
                    print(f"Retrying due to error ({retry + 1}/{max_retries})...")
                    time.sleep(1)
                    continue
                break
        
        # Add small delay between files to avoid overwhelming the server
        time.sleep(0.5)
    
    # Publish the record if all files were uploaded successfully
    if len(uploaded_files) == len(all_files):
        print(f"All {len(uploaded_files)} files uploaded successfully.")
        return True
    
    print(f"Uploaded {len(uploaded_files)}/{len(all_files)} files.")
    return len(uploaded_files) > 0


def collect_files_to_upload(book_dir):
    """
    Collect files from the book directory that should be uploaded to InvenioRDM.
    """
    files_to_upload = []
    
    # Add manifest
    manifest_path = os.path.join(book_dir, "manifest.json")
    if os.path.exists(manifest_path):
        files_to_upload.append(manifest_path)
    
    # Add pages directory contents
    pages_dir = os.path.join(book_dir, "pages")
    if os.path.exists(pages_dir) and os.path.isdir(pages_dir):
        for file_name in os.listdir(pages_dir):
            file_path = os.path.join(pages_dir, file_name)
            if os.path.isfile(file_path):
                files_to_upload.append(file_path)
    
    # Add HOCR files if they exist
    hocr_dir = os.path.join(book_dir, "hocr")
    if os.path.exists(hocr_dir) and os.path.isdir(hocr_dir):
        for file_name in os.listdir(hocr_dir):
            file_path = os.path.join(hocr_dir, file_name)
            if os.path.isfile(file_path):
                files_to_upload.append(file_path)
    
    return files_to_upload


def export_metadata(book_info, manifest_url):
    """
    Export record metadata to a JSON file for reference.
    """
    import json
    import os
    from datetime import datetime
    
    # Create metadata directory if it doesn't exist
    metadata_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metadata_files")
    os.makedirs(metadata_dir, exist_ok=True)
    
    # Prepare metadata according to InvenioRDM schema
    metadata = {
        "access": {
            "record": "public",
            "files": "public"
        },
        "files": {
            "enabled": True
        },
        "metadata": {
            "title": book_info["title"],
            "publication_date": book_info.get("publication_date", datetime.now().strftime("%Y-%m-%d")),
            "resource_type": {"id": "publication-book"},
            "creators": [
                {
                    "person_or_org": {
                        "name": book_info.get("author", "Unknown Author"),
                        "type": "personal"
                    }
                }
            ],
            "description": book_info.get("description", "Book imported with IIIF support")
        }
    }
    
    # Add IIIF manifest URL to custom fields if available
    metadata["custom_fields"] = {"turath:iiif_manifest": manifest_url}
    
    # Save metadata to file
    filename = os.path.join(metadata_dir, f"{book_info['book_id']}_metadata.json")
    with open(filename, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Metadata exported to: {filename}")
    return filename


def main():
    """Main entry point for the script."""
    args = setup_argparse()
    
    # Process each book directory
    for book_dir in args.book_dirs:
        print(f"\nProcessing book: {book_dir}")
        
        # Validate directory structure
        if not validate_book_directory(book_dir):
            print(f"Skipping invalid directory: {book_dir}")
            continue
        
        # Extract book information
        book_info = extract_book_info(book_dir)
        print("Book information:")
        pprint(book_info)
        
        # Copy files to storage if needed
        storage_dir = os.path.join(args.storage_path, book_info["book_id"])
        print("Copying files to storage...")
        
        if book_dir == storage_dir:
            print(f"Files are already in the storage location: {storage_dir}")
        else:
            copy_to_storage(book_dir, args.storage_path, book_info["book_id"])
        
        print(f"Files copied to {storage_dir}")
        
        # Generate manifest URL for the book
        manifest_url = f"{args.server_url}/{book_info['book_id']}/manifest.json"
        
        if args.dry_run:
            print(f"Would create record with IIIF manifest URL: {manifest_url}")
            continue
            
        # Check if we have authentication
        has_token = args.token is not None and args.token != ""
        has_basic_auth = (args.username is not None and args.username != "" and 
                         args.password is not None and args.password != "")
        
        if not has_token and not has_basic_auth:
            print("\nWarning: No authentication provided. Will run in dry-run mode.")
            print("To authenticate, either:")
            print("  1. Pass a token with --token parameter")
            print("  2. Set INVENIO_API_TOKEN environment variable")
            print("  3. For development: Use --username and --password")
            print(f"Would create record with IIIF manifest URL: {manifest_url}")
            continue
        
        print("Updating manifest...")
        update_manifest(os.path.join(storage_dir, "manifest.json"), args.server_url, book_info["book_id"])
        
        # Extract text from HOCR files
        print("Extracting text from HOCR files...")
        extracted_text = extract_book_text(storage_dir)
        if extracted_text:
            book_info["extracted_text"] = extracted_text
            print(f"Extracted text from {len(extracted_text)} HOCR files")
        else:
            print("No HOCR files found or no text could be extracted")
        
        # Create record in InvenioRDM
        print("Creating record in InvenioRDM...")
        if has_token:
            record_result = create_record(book_info, manifest_url, args.token)
        elif has_basic_auth:
            record_result = create_record(book_info, manifest_url, None, args.username, args.password)
        
        if record_result:
            # Upload files to the record if not skipping
            if not args.skip_files:
                print("Uploading files...")
                if has_token:
                    upload_success = upload_files(record_result, storage_dir, args.token)
                elif has_basic_auth:
                    upload_success = upload_files(record_result, storage_dir, None, username=args.username, password=args.password)
                if upload_success:
                    print("Files uploaded successfully")
                else:
                    print("Failed to upload some or all files")
            else:
                print("Skipping file uploads as requested")
        else:
            print(f"Failed to create record for {book_dir}")
            print("You may need to create the record manually through the web interface")
    
    print("\nImport process completed")


if __name__ == "__main__":
    main()
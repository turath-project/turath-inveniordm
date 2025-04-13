#!/usr/bin/env python3
"""
Script to upload a PDF file to a record for testing IIIF PDF support.
"""
import os
import sys
import requests
import time
import random
import string
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for local testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def generate_random_doi():
    """Generate a random DOI for testing."""
    # Generate a random 8-character string
    random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"10.5281/zenodo.{random_chars}"

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} RECORD_ID PDF_FILE")
    sys.exit(1)

RECORD_ID = sys.argv[1]
PDF_FILE = sys.argv[2]

if not os.path.exists(PDF_FILE):
    print(f"Error: PDF file {PDF_FILE} does not exist")
    sys.exit(1)

# Get an API token (you'll need to set this in your environment)
API_TOKEN = os.getenv('API_TOKEN')
if not API_TOKEN:
    print("Error: API_TOKEN environment variable not set")
    sys.exit(1)

# Create a new record
try:
    # Create a new record draft
    draft_url = "https://127.0.0.1:5000/api/records"
    headers = {
        'Authorization': f'Bearer {API_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Generate a random DOI
    random_doi = generate_random_doi()
    
    # Basic record metadata
    record_data = {
        "metadata": {
            "title": "Test PDF Record",
            "publication_date": "2025-04-07",
            "creators": [{
                "person_or_org": {
                    "family_name": "User",
                    "given_name": "Test",
                    "type": "personal"
                }
            }],
            "resource_type": {
                "id": "publication-article"
            },
            "publisher": "Zenodo",
            "doi": random_doi,
            "access_right": {
                "id": "open"
            },
            "license": {
                "id": "cc-by-4.0"
            }
        }
    }
    
    # Create new record
    response = requests.post(
        draft_url,
        headers=headers,
        json=record_data,
        verify=False
    )
    
    if response.status_code != 201:
        print(f"Error creating record: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    record = response.json()
    record_id = record['id']
    print(f"Created new record with ID: {record_id}")
    print(f"Generated DOI: {random_doi}")
    
    # Upload the PDF file
    files_url = f"https://127.0.0.1:5000/api/records/{record_id}/draft/files"
    files_headers = {
        'Authorization': f'Bearer {API_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Create file entry
    file_name = os.path.basename(PDF_FILE)
    response = requests.post(
        files_url,
        headers=files_headers,
        json=[{'key': file_name}],
        verify=False
    )
    if response.status_code != 201:
        print(f"Error creating file entry: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    # Upload file content
    upload_url = f"{files_url}/{file_name}/content"
    with open(PDF_FILE, 'rb') as f:
        response = requests.put(
            upload_url,
            headers={'Authorization': f'Bearer {API_TOKEN}'},
            data=f,
            verify=False
        )
    if response.status_code != 200:
        print(f"Error uploading file: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    # Commit the file
    commit_file_url = f"{files_url}/{file_name}/commit"
    response = requests.post(
        commit_file_url,
        headers=headers,
        verify=False
    )
    if response.status_code != 200:
        print(f"Error committing file: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    print("File committed successfully")
    
    # Wait a moment for the file to be processed
    time.sleep(2)
    
    # Commit the draft
    commit_url = f"https://127.0.0.1:5000/api/records/{record_id}/draft/actions/publish"
    response = requests.post(commit_url, headers=headers, verify=False)
    if response.status_code != 202:
        print(f"Error publishing record: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    print(f"Successfully uploaded PDF file {PDF_FILE} to new record {record_id}")
    print("You can now test the IIIF manifest with:")
    print(f"python3 check_iiif.py {record_id}")

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1) 
#!/usr/bin/env python3
"""
Script to upload a PDF file via API and generate a IIIF manifest.
"""
import os
import sys
import json
import tempfile
import getpass
import requests
import warnings
from urllib.parse import urljoin

def create_test_pdf():
    """Create a simple test PDF file."""
    pdf_content = """
%PDF-1.1
%¥±ë

1 0 obj
  << /Type /Catalog
     /Pages 2 0 R
  >>
endobj

2 0 obj
  << /Type /Pages
     /Kids [3 0 R]
     /Count 1
     /MediaBox [0 0 300 144]
  >>
endobj

3 0 obj
  <<  /Type /Page
      /Parent 2 0 R
      /Resources
       << /Font
           << /F1
               << /Type /Font
                  /Subtype /Type1
                  /BaseFont /Times-Roman
               >>
           >>
       >>
      /Contents 4 0 R
  >>
endobj

4 0 obj
  << /Length 55 >>
stream
  BT
    /F1 18 Tf
    0 0 Td
    (Hello, IIIF World!) Tj
  ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000018 00000 n 
0000000077 00000 n 
0000000178 00000 n 
0000000457 00000 n 
trailer
  <<  /Root 1 0 R
      /Size 5
  >>
startxref
565
%%EOF
"""
    
    # Create a temporary file
    fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    os.write(fd, pdf_content.encode('utf-8'))
    os.close(fd)
    
    print(f"Created test PDF at: {temp_path}")
    return temp_path

def get_auth_token(base_url):
    """
    Get authentication token from Invenio.
    
    Args:
        base_url: Base URL of the Invenio instance
        
    Returns:
        Authentication token if successful, None otherwise
    """
    # Try RDM_API_TOKEN environment variable first
    api_token = os.environ.get('RDM_API_TOKEN')
    if api_token:
        print("✅ Using RDM_API_TOKEN from environment")
        return api_token
        
    # Ensure base_url doesn't end with a slash
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    
    # Prompt for credentials if not provided
    email = input("Enter your email: ")
    password = getpass.getpass("Enter your password: ")
    
    # Get token
    token_url = f"{base_url}/api/accounts/login"
    data = {
        "email": email,
        "password": password
    }
    
    try:
        # Add verify=False for self-signed certs
        # Also suppress the InsecureRequestWarning
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = requests.post(token_url, json=data, verify=False)
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("token")
            if token:
                print("✅ Successfully obtained authentication token")
                return token
            else:
                print("❌ No token in response")
                print(response.text)
                return None
        else:
            print(f"❌ Failed to get token: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Error getting token: {e}")
        return None

def upload_pdf_via_api(pdf_path=None, base_url="http://localhost:5000", 
                       title="Test PDF Document"):
    """
    Upload a PDF file via the API and generate a IIIF manifest.
    
    Args:
        pdf_path: Path to the PDF file to upload. If None, a test PDF will be created.
        base_url: Base URL of the Invenio instance (default: http://localhost:5000)
        title: Title for the record
        
    Returns:
        Record ID if successful, None otherwise
    """
    print("\n=== Uploading PDF via API and generating IIIF manifest ===\n")
    
    # Create test PDF if no path provided
    is_temp_file = False
    if pdf_path is None:
        pdf_path = create_test_pdf()
        is_temp_file = True
    
    filename = os.path.basename(pdf_path)
    print(f"Using PDF file: {pdf_path} (filename: {filename})")
    
    # Check if file exists and is a PDF
    if not os.path.exists(pdf_path):
        print(f"Error: File does not exist: {pdf_path}")
        return None
    
    if not pdf_path.lower().endswith('.pdf'):
        print(f"Warning: File does not have a .pdf extension: {pdf_path}")
    
    try:
        # Make sure base_url doesn't end with a slash
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        
        # Get authentication token
        token = get_auth_token(base_url)
        if not token:
            print("❌ No API token found or provided. Cannot authenticate.")
            return None
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        # 1. Create draft record
        print("Creating draft record...")
        
        metadata = {
            "metadata": {
                "title": title,
                "description": "A test PDF document for IIIF manifest generation",
                "publication_date": "2023-01-01",
                "resource_type": {"id": "publication"},
                "creators": [{
                    "person_or_org": {
                        "name": "Test User",
                        "type": "personal"
                     }
                }]
            },
            "access": {
                "record": "public",
                "files": "public"
            }
        }
        
        draft_url = f"{base_url}/api/records"
        print(f"POST {draft_url}")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = requests.post(draft_url, json=metadata, headers=headers, verify=False)
        
        if response.status_code != 201:
            print(f"Error creating draft: {response.status_code}")
            print(response.text)
            return None
        
        draft_data = response.json()
        recid = draft_data["id"]
        print(f"Created draft record with ID: {recid}")
        
        # 2. Upload the file
        print(f"Uploading file: {filename}...")
        
        # Initialize files
        files_init_url = f"{base_url}/api/records/{recid}/draft/files"
        files_init_data = [{"key": filename}]
        
        print(f"POST {files_init_url}")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = requests.post(files_init_url, json=files_init_data, headers=headers, verify=False)
        if response.status_code != 201:
            print(f"Error initializing files: {response.status_code}")
            print(response.text)
            return None
        
        # Upload file content
        file_upload_url = f"{base_url}/api/records/{recid}/draft/files/{filename}/content"
        print(f"PUT {file_upload_url}")
        with open(pdf_path, 'rb') as file:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                response = requests.put(file_upload_url, data=file, headers=headers, verify=False)
        
        if response.status_code != 200:
            print(f"Error uploading file: {response.status_code}")
            print(response.text)
            return None
        
        # Commit the file
        file_commit_url = f"{base_url}/api/records/{recid}/draft/files/{filename}/commit"
        print(f"POST {file_commit_url}")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = requests.post(file_commit_url, headers=headers, verify=False)
        
        if response.status_code != 200:
            print(f"Error committing file: {response.status_code}")
            print(response.text)
            return None
        
        print(f"File uploaded successfully: {filename}")
        
        # 3. Publish the record
        print("Publishing record...")
        
        publish_url = f"{base_url}/api/records/{recid}/draft/actions/publish"
        print(f"POST {publish_url}")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = requests.post(publish_url, headers=headers, verify=False)
        
        if response.status_code != 202:
            print(f"Error publishing record: {response.status_code}")
            print(response.text)
            return None
        
        print(f"Record published with ID: {recid}")
        
        # 4. Check the IIIF manifest
        manifest_url = f"{base_url}/api/iiif/record:{recid}/manifest.json"
        print(f"\nChecking IIIF manifest at: {manifest_url}")
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = requests.get(manifest_url, verify=False)
        if response.status_code == 200:
            print("✅ IIIF manifest is available!")
            manifest_data = response.json()
            print(f"Manifest content (truncated):")
            print(json.dumps(manifest_data, indent=2)[:300] + "...")
        else:
            print(f"❌ IIIF manifest not available: {response.status_code}")
            print(response.text[:200] if response.text else "No response text")
            
            # Try again with different URL formats
            alt_manifest_urls = [
                f"{base_url}/api/iiif/record:{recid}/manifest",
                f"{base_url}/iiif/record:{recid}/manifest.json",
                f"{base_url}/iiif/record:{recid}/manifest",
                f"{base_url}/api/iiif/{recid}/manifest.json"
            ]
            
            for alt_url in alt_manifest_urls:
                print(f"\nTrying alternative URL: {alt_url}")
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    alt_response = requests.get(alt_url, verify=False)
                if alt_response.status_code == 200:
                    print("✅ IIIF manifest is available at this URL!")
                    manifest_data = alt_response.json()
                    print(f"Manifest content (truncated):")
                    print(json.dumps(manifest_data, indent=2)[:300] + "...")
                    manifest_url = alt_url
                    break
                else:
                    print(f"❌ Not available: {alt_response.status_code}")
        
        # 5. Also check the file itself via IIIF
        canteloupe_url = f"{base_url}/iiif/2/{recid}:{filename}/full/full/0/default.jpg"
        print(f"\nChecking PDF rendering via IIIF: {canteloupe_url}")
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = requests.get(canteloupe_url, verify=False)
        if response.status_code == 200:
            print("✅ PDF can be rendered via IIIF!")
            content_type = response.headers.get('Content-Type', '')
            print(f"Content-Type: {content_type}")
            print(f"Content length: {len(response.content)} bytes")
            
            # Save the rendered image for verification
            image_path = os.path.join(os.path.dirname(pdf_path), f"{os.path.splitext(filename)[0]}_rendered.jpg")
            with open(image_path, 'wb') as f:
                f.write(response.content)
            print(f"Saved rendered image to: {image_path}")
        else:
            print(f"❌ PDF cannot be rendered via IIIF: {response.status_code}")
            print(response.text[:200] if response.text else "No response text")
            
            # Try alternative URL
            alt_canteloupe_url = f"{base_url}/iiif/2/record:{recid}/files:{filename}/full/full/0/default.jpg"
            print(f"\nTrying alternative IIIF URL: {alt_canteloupe_url}")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                alt_response = requests.get(alt_canteloupe_url, verify=False)
            if alt_response.status_code == 200:
                print("✅ PDF can be rendered via IIIF with alternative URL!")
                content_type = alt_response.headers.get('Content-Type', '')
                print(f"Content-Type: {content_type}")
                print(f"Content length: {len(alt_response.content)} bytes")
                
                # Save the rendered image for verification
                image_path = os.path.join(os.path.dirname(pdf_path), f"{os.path.splitext(filename)[0]}_rendered.jpg")
                with open(image_path, 'wb') as f:
                    f.write(alt_response.content)
                print(f"Saved rendered image to: {image_path}")
            else:
                print(f"❌ PDF cannot be rendered via alternative IIIF URL: {alt_response.status_code}")
                print(alt_response.text[:200] if alt_response.text else "No response text")
        
        print(f"\n✅ Process completed. Record ID: {recid}")
        print(f"IIIF Manifest URL: {manifest_url}")
        print(f"Record URL: {base_url}/records/{recid}")
        
        return recid
    except Exception as e:
        print(f"Error in API request: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Clean up temporary file if created
        if is_temp_file and os.path.exists(pdf_path):
            print(f"Removing temporary PDF file: {pdf_path}")
            os.remove(pdf_path)

def main():
    # Check arguments
    base_url = "http://localhost:5000"
    pdf_path = None
    
    # Parse command line arguments
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == "--url" and i + 1 < len(sys.argv):
            base_url = sys.argv[i + 1]
            i += 2
        elif arg == "--pdf" and i + 1 < len(sys.argv):
            pdf_path = sys.argv[i + 1]
            i += 2
        elif arg.startswith("http"):
            base_url = arg
            i += 1
        elif os.path.exists(arg):
            pdf_path = arg
            i += 1
        else:
            print(f"Unknown argument: {arg}")
            i += 1
    
    # Validate PDF path if provided
    if pdf_path and not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        sys.exit(1)
    
    print(f"Using base URL: {base_url}")
    if pdf_path:
        print(f"Using PDF file: {pdf_path}")
    else:
        print("Will create a test PDF file")
    
    # Run the upload
    recid = upload_pdf_via_api(pdf_path, base_url)
    if recid:
        print("\nSuccess! You can now access the PDF file and its IIIF manifest.")
    else:
        print("\nFailed to upload PDF and generate manifest.")

if __name__ == "__main__":
    main() 
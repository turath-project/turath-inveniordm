#!/usr/bin/env python3
"""
Script to upload a PDF file and generate a IIIF manifest automatically.
"""
import os
import sys
import json
import uuid
import tempfile
import importlib
from pathlib import Path

REQUIRED_MODULES = [
    'flask',
    'invenio_app.factory',
    'invenio_db',
    'invenio_files_rest.models',
    'invenio_records_files.api',
    'invenio_records.api',
    'invenio_pidstore.models',
    'invenio_rdm_records.services',
]

def check_imports():
    """Check if required modules are available."""
    missing_modules = []
    
    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing_modules.append(module_name)
    
    if missing_modules:
        print("Error: The following required modules are not available:")
        for module in missing_modules:
            print(f"  - {module}")
        print("\nMake sure you're running this script in the correct Invenio-RDM environment.")
        return False
    
    # Try to import zenodo_rdm.iiif specifically
    try:
        importlib.import_module('zenodo_rdm.iiif')
    except ImportError:
        print("Warning: 'zenodo_rdm.iiif' module not found.")
        print("The IIIF manifest generation might not work as expected.")
    
    return True

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

def upload_pdf_via_api(pdf_path, title="Test PDF Document"):
    """
    Upload a PDF file via the API and generate a IIIF manifest.
    
    Args:
        pdf_path: Path to the PDF file to upload.
        title: Title for the record
    """
    from flask import current_app
    import requests
    
    print("\n=== Uploading PDF via API and generating IIIF manifest ===\n")
    
    # Get base URL from config
    base_url = current_app.config.get('SITE_UI_URL', 'http://localhost:5000')
    
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
    
    try:
        # 1. Create draft record
        print("Creating draft record...")
        
        metadata = {
            "metadata": {
                "title": title,
                "description": "A test PDF document for IIIF manifest generation",
                "publication_date": "2023-01-01",
                "resource_type": {"id": "publication"},
                "creators": [{"person_or_org": {"name": "Test User"}}]
            },
            "access": {
                "record": "public",
                "files": "public"
            }
        }
        
        draft_url = f"{base_url}/api/records"
        response = requests.post(draft_url, json=metadata)
        
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
        
        response = requests.post(files_init_url, json=files_init_data)
        if response.status_code != 201:
            print(f"Error initializing files: {response.status_code}")
            print(response.text)
            return None
        
        # Upload file content
        file_upload_url = f"{base_url}/api/records/{recid}/draft/files/{filename}/content"
        with open(pdf_path, 'rb') as file:
            response = requests.put(file_upload_url, data=file)
        
        if response.status_code != 200:
            print(f"Error uploading file: {response.status_code}")
            print(response.text)
            return None
        
        # Commit the file
        file_commit_url = f"{base_url}/api/records/{recid}/draft/files/{filename}/commit"
        response = requests.post(file_commit_url)
        
        if response.status_code != 200:
            print(f"Error committing file: {response.status_code}")
            print(response.text)
            return None
        
        print(f"File uploaded successfully: {filename}")
        
        # 3. Publish the record
        print("Publishing record...")
        
        publish_url = f"{base_url}/api/records/{recid}/draft/actions/publish"
        response = requests.post(publish_url)
        
        if response.status_code != 202:
            print(f"Error publishing record: {response.status_code}")
            print(response.text)
            return None
        
        print(f"Record published with ID: {recid}")
        
        # 4. Check the IIIF manifest
        manifest_url = f"{base_url}/api/iiif/record:{recid}/manifest.json"
        print(f"\nChecking IIIF manifest at: {manifest_url}")
        
        response = requests.get(manifest_url)
        if response.status_code == 200:
            print("✅ IIIF manifest is available!")
            manifest_data = response.json()
            print(f"Manifest content (truncated):")
            print(json.dumps(manifest_data, indent=2)[:300] + "...")
        else:
            print(f"❌ IIIF manifest not available: {response.status_code}")
            print(response.text)
        
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

def upload_pdf_direct(pdf_path=None, title="Test PDF Document"):
    """
    Upload a PDF file directly using the Invenio services.
    
    Args:
        pdf_path: Path to the PDF file to upload. If None, a test PDF will be created.
        title: Title for the record
    """
    # Import required modules
    from flask import current_app
    from invenio_app.factory import create_app
    from invenio_db import db
    from invenio_files_rest.models import ObjectVersion, FileInstance
    from invenio_records_files.api import RecordsBuckets
    from invenio_pidstore.models import PersistentIdentifier
    
    # Try to get the RDM record service from the app context
    try:
        record_service = current_app.extensions["invenio-rdm-records"].records_service
        file_service = current_app.extensions["invenio-rdm-records"].records_service.files
        
        # Create a simple identity
        from invenio_access.permissions import system_identity
        identity = system_identity
    except Exception as e:
        print(f"Error getting RDM services: {e}")
        print("Trying API approach instead.")
        return upload_pdf_via_api(pdf_path, title)
    
    # Try to import zenodo_rdm.iiif module
    try:
        from zenodo_rdm.iiif import generate_pdf_manifest
        has_iiif_module = True
    except ImportError:
        has_iiif_module = False
        print("Warning: 'zenodo_rdm.iiif' module not available. IIIF manifest generation may not work.")
    
    print("\n=== Uploading PDF and generating IIIF manifest ===\n")
    
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
    
    # Metadata for the record
    metadata = {
        "title": title,
        "description": "A test PDF document for IIIF manifest generation",
        "resource_type": {"type": "publication"},
        "creators": [{"name": "Test User"}],
        "publication_date": "2023-01-01",
        "access": {
            "record": "public",
            "files": "public"
        }
    }
    
    # Create a record using the RDM service
    try:
        print("Creating record using RDM service...")
        
        # Create a draft
        draft = record_service.create(identity, metadata)
        recid = draft["id"]
        print(f"Created draft record with ID: {recid}")
        
        # Upload the file
        print(f"Uploading file: {filename}...")
        with open(pdf_path, 'rb') as file:
            file_service.init_files(identity, draft.id, [{"key": filename}])
            file_service.set_file_content(
                identity, draft.id, filename, file
            )
            file_service.commit_file(identity, draft.id, filename)
        
        print(f"File uploaded successfully: {filename}")
        
        # Publish the record
        print("Publishing record...")
        record = record_service.publish(identity, draft.id)
        print(f"Record published with ID: {recid}")
        
        # Generate and check IIIF manifest
        print("\nChecking IIIF manifest generation...")
        
        # Get the base URL from the config
        base_url = current_app.config.get('SITE_UI_URL', 'http://localhost:5000')
        
        # Check IIIF configuration
        iiif_enabled = current_app.config.get('RDM_IIIF_ENABLED', False)
        iiif_pdf_support = current_app.config.get('RDM_IIIF_PDF_SUPPORT', False)
        iiif_formats = current_app.config.get('RDM_IIIF_MANIFEST_FORMATS', [])
        
        print("\nIIIF Configuration:")
        print(f"  RDM_IIIF_ENABLED: {iiif_enabled}")
        print(f"  RDM_IIIF_PDF_SUPPORT: {iiif_pdf_support}")
        print(f"  RDM_IIIF_MANIFEST_FORMATS: {iiif_formats}")
        
        if not iiif_enabled:
            print("  ⚠️ IIIF is not enabled in the configuration!")
        if not iiif_pdf_support:
            print("  ⚠️ PDF support for IIIF is not enabled!")
        if 'pdf' not in iiif_formats:
            print("  ⚠️ 'pdf' is not in the supported manifest formats!")
        
        # Manifest URL
        manifest_url = f"{base_url}/api/iiif/record:{recid}/manifest.json"
        print(f"\nIIIF Manifest should be available at: {manifest_url}")
        
        # Get bucket ID and file details
        bucket_id = record.get("files", {}).get("bucket")
        
        if bucket_id:
            obj = ObjectVersion.query.filter_by(
                bucket_id=bucket_id, key=filename
            ).first()
            
            if obj and obj.file_id:
                file_instance = FileInstance.query.filter_by(id=obj.file_id).first()
                if file_instance:
                    print(f"\nFile details:")
                    print(f"  File ID: {file_instance.id}")
                    print(f"  URI: {file_instance.uri}")
                    print(f"  Size: {file_instance.size} bytes")
                    
                    # Check if file exists on disk
                    if file_instance.uri.startswith('file://'):
                        file_path = file_instance.uri[7:]  # Remove 'file://' prefix
                    else:
                        file_path = file_instance.uri
                        
                    if os.path.exists(file_path):
                        print(f"  ✅ File exists at: {file_path}")
                    else:
                        print(f"  ❌ File does not exist at: {file_path}")
        
        # Check symlink in the records directory
        instance_path = current_app.instance_path
        record_dir_path = os.path.join(instance_path, "data", "records", recid)
        pdf_path_in_records = os.path.join(record_dir_path, filename)
        
        print("\nChecking for symlink:")
        if os.path.exists(record_dir_path):
            print(f"  ✅ Records directory exists: {record_dir_path}")
            if os.path.exists(pdf_path_in_records):
                if os.path.islink(pdf_path_in_records):
                    link_target = os.readlink(pdf_path_in_records)
                    print(f"  ✅ Symlink exists: {pdf_path_in_records} -> {link_target}")
                else:
                    print(f"  ✅ File exists (not a symlink): {pdf_path_in_records}")
            else:
                print(f"  ❌ File does not exist: {pdf_path_in_records}")
                print("  Creating symlink manually...")
                
                # Try to create symlink if doesn't exist
                try:
                    os.makedirs(os.path.dirname(pdf_path_in_records), exist_ok=True)
                    os.symlink(file_path, pdf_path_in_records)
                    if os.path.exists(pdf_path_in_records):
                        print(f"  ✅ Symlink created manually: {pdf_path_in_records} -> {file_path}")
                    else:
                        print(f"  ❌ Failed to create symlink")
                except Exception as e:
                    print(f"  ❌ Error creating symlink: {e}")
        else:
            print(f"  ❌ Records directory does not exist: {record_dir_path}")
            print("  Creating directory and symlink manually...")
            
            # Try to create directory and symlink
            try:
                os.makedirs(record_dir_path, exist_ok=True)
                os.symlink(file_path, pdf_path_in_records)
                if os.path.exists(pdf_path_in_records):
                    print(f"  ✅ Directory and symlink created manually: {pdf_path_in_records} -> {file_path}")
                else:
                    print(f"  ❌ Failed to create directory or symlink")
            except Exception as e:
                print(f"  ❌ Error creating directory or symlink: {e}")
        
        # If we have the zenodo_rdm.iiif module, try to generate a manifest directly
        if has_iiif_module:
            print("\nTrying to generate IIIF manifest directly:")
            try:
                manifest = generate_pdf_manifest(record_id=recid, file_key=filename)
                print("  ✅ Manifest generated successfully")
                print("  Manifest content (truncated):")
                print(f"  {json.dumps(manifest, indent=2)[:300]}...")
            except Exception as e:
                print(f"  ❌ Failed to generate manifest: {e}")
        
        print(f"\n✅ Process completed. Record ID: {recid}")
        print(f"IIIF Manifest URL: {manifest_url}")
        print(f"Record URL: {base_url}/records/{recid}")
        
        return recid
        
    except Exception as e:
        print(f"Error creating record: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Clean up temporary file if created
        if is_temp_file and os.path.exists(pdf_path):
            print(f"Removing temporary PDF file: {pdf_path}")
            os.remove(pdf_path)

def main():
    if not check_imports():
        sys.exit(1)
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        if not os.path.exists(pdf_path):
            print(f"Error: PDF file not found at {pdf_path}")
            sys.exit(1)
    else:
        pdf_path = None  # Will create a test PDF
        
    print("This script will try two methods to upload a PDF and generate a manifest:")
    print("1. Using Invenio services directly")
    print("2. Using the REST API if the direct method fails")
    
    # Import here to avoid early import errors
    try:
        from invenio_app.factory import create_app
        app = create_app()
        
        with app.app_context():
            recid = upload_pdf_direct(pdf_path)
            if recid:
                print("\nSuccess! You can now access the PDF file and its IIIF manifest.")
            else:
                print("\nFailed to upload PDF and generate manifest.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 
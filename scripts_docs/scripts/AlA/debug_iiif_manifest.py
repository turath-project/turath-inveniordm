#!/usr/bin/env python3
"""
Script to debug IIIF manifest generation for PDFs.
"""
import os
import sys
import json
import logging
import requests
from urllib.parse import urljoin
import traceback
from pathlib import Path
from flask import current_app

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Disable insecure request warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Add the parent directory to the path so we can import the app
sys.path.append(str(Path(__file__).parent.parent.parent))

def get_authenticated_session():
    """Get an authenticated session for API requests.
    
    Returns:
        A requests.Session object with authentication credentials
    """
    from flask import current_app
    import requests
    
    # Create a new session
    session = requests.Session()
    
    # Try to get configuration from Flask app
    try:
        server_url = current_app.config.get("SERVER_NAME")
        if not server_url:
            server_url = os.environ.get("INVENIO_SERVER_URL", "http://127.0.0.1:5000")
            
        # Check if we have admin credentials in environment
        admin_email = os.environ.get("ADMIN_EMAIL")
        admin_password = os.environ.get("ADMIN_PASSWORD")
        
        if admin_email and admin_password:
            print(f"🔐 Authenticating with admin credentials")
            login_url = f"https://{server_url}/api/accounts/login"
            if not server_url.startswith("http"):
                login_url = f"http://{server_url}/api/accounts/login"
                
            # Try to login
            login_data = {
                "email": admin_email,
                "password": admin_password
            }
            response = session.post(login_url, json=login_data)
            
            if response.status_code == 200:
                print("✅ Authentication successful")
            else:
                print(f"⚠️ Authentication failed: {response.status_code}")
                print(f"Response: {response.text[:200]}")
        else:
            print("ℹ️ No admin credentials found, using unauthenticated session")
    except Exception as e:
        print(f"⚠️ Error authenticating: {e}")
    
    return session

def test_manifest_urls(record_id, base_url="http://localhost:5000"):
    """Test various IIIF manifest URL patterns."""
    logger.info(f"Testing IIIF manifest URLs for record {record_id}")
    
    # Ensure base_url doesn't end with a slash
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    
    # Define all possible manifest URL patterns to test
    manifest_urls = [
        f"{base_url}/api/iiif/record:{record_id}/manifest.json",
        f"{base_url}/api/iiif/record:{record_id}/manifest",
        f"{base_url}/iiif/record:{record_id}/manifest.json",
        f"{base_url}/iiif/record:{record_id}/manifest",
        f"{base_url}/api/iiif/{record_id}/manifest.json",
        f"{base_url}/api/iiif/{record_id}/manifest",
        f"{base_url}/iiif/{record_id}/manifest.json",
        f"{base_url}/iiif/{record_id}/manifest",
        f"{base_url}/api/records/{record_id}/iiif/manifest.json",
        f"{base_url}/api/records/{record_id}/iiif/manifest",
        f"{base_url}/records/{record_id}/iiif/manifest.json",
        f"{base_url}/records/{record_id}/iiif/manifest"
    ]
    
    successful_urls = []
    
    print("\n=== Testing IIIF Manifest URLs ===")
    for url in manifest_urls:
        try:
            print(f"\nTrying URL: {url}")
            
            # Make request with SSL verification disabled (for local testing)
            response = requests.get(url, verify=False)
            
            print(f"Status code: {response.status_code}")
            if response.status_code == 200:
                print("✅ Success!")
                try:
                    manifest = response.json()
                    print(f"Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
                    # Print first few items of the manifest
                    if isinstance(manifest, dict):
                        print("Manifest structure:")
                        for key, value in list(manifest.items())[:5]:
                            if isinstance(value, (dict, list)) and len(str(value)) > 100:
                                print(f"  {key}: [complex object]")
                            else:
                                print(f"  {key}: {value}")
                    successful_urls.append(url)
                except json.JSONDecodeError:
                    print("❌ Response is not valid JSON")
                    print(f"Response content (first 100 chars): {response.text[:100]}...")
            else:
                print(f"❌ Failed with status code {response.status_code}")
                print(f"Response: {response.text[:200]}..." if len(response.text) > 200 else f"Response: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n=== Summary ===")
    if successful_urls:
        print(f"✅ Found {len(successful_urls)} working manifest URLs:")
        for url in successful_urls:
            print(f"  {url}")
    else:
        print("❌ No working manifest URLs found.")
    
    return successful_urls

def test_direct_manifest_generation(record_id):
    """Test generating the manifest directly using the Invenio API."""
    print("\n=== Testing Direct Manifest Generation ===")
    try:
        from flask import current_app
        from invenio_app.factory import create_app
        
        app = create_app()
        with app.app_context():
            try:
                # Try to import and use Zenodo's PDF manifest generator
                try:
                    from zenodo_rdm.iiif import generate_pdf_manifest
                    
                    print("Calling generate_pdf_manifest directly...")
                    record_service = current_app.extensions["invenio-rdm-records"].records_service
                    
                    # Try to get the record
                    from invenio_access.permissions import system_identity
                    record = record_service.read(system_identity, record_id)
                    
                    # Find PDF files in the record
                    pdf_files = []
                    if "files" in record and "entries" in record["files"]:
                        for file_entry in record["files"]["entries"]:
                            if file_entry.get("key", "").lower().endswith(".pdf"):
                                pdf_files.append(file_entry["key"])
                    
                    if not pdf_files:
                        print(f"❌ No PDF files found in record {record_id}")
                        return
                    
                    print(f"Found PDF files: {pdf_files}")
                    
                    # Generate manifest for each PDF
                    for pdf_file in pdf_files:
                        print(f"\nGenerating manifest for {pdf_file}...")
                        try:
                            manifest = generate_pdf_manifest(record_id=record_id, file_key=pdf_file)
                            print("✅ Successfully generated manifest!")
                            print("Manifest structure:")
                            for key, value in list(manifest.items())[:5]:
                                if isinstance(value, (dict, list)) and len(str(value)) > 100:
                                    print(f"  {key}: [complex object]")
                                else:
                                    print(f"  {key}: {value}")
                        except Exception as e:
                            print(f"❌ Error generating manifest for {pdf_file}: {e}")
                            traceback.print_exc()
                
                except ImportError:
                    print("❌ zenodo_rdm.iiif module not found. Trying alternative approach...")
                    
                    # Try to use the IIIF service directly
                    try:
                        from invenio_rdm_records.services import IIIFService
                        iiif_service = current_app.extensions.get("invenio-rdm-records").iiif_service
                        
                        print("Using IIIFService directly...")
                        from invenio_access.permissions import system_identity
                        
                        # Get record files to find PDFs
                        record_service = current_app.extensions["invenio-rdm-records"].records_service
                        record = record_service.read(system_identity, record_id)
                        
                        # Find PDF files in the record
                        pdf_files = []
                        if "files" in record and "entries" in record["files"]:
                            for file_entry in record["files"]["entries"]:
                                if file_entry.get("key", "").lower().endswith(".pdf"):
                                    pdf_files.append(file_entry["key"])
                        
                        if not pdf_files:
                            print(f"❌ No PDF files found in record {record_id}")
                            return
                        
                        print(f"Found PDF files: {pdf_files}")
                        
                        # Try to generate a manifest for each PDF file
                        for pdf_file in pdf_files:
                            print(f"\nGenerating manifest for {pdf_file}...")
                            try:
                                manifest = iiif_service.get_manifest(system_identity, record_id)
                                print("✅ Successfully generated manifest!")
                                print("Manifest structure:")
                                for key, value in list(manifest.items())[:5]:
                                    if isinstance(value, (dict, list)) and len(str(value)) > 100:
                                        print(f"  {key}: [complex object]")
                                    else:
                                        print(f"  {key}: {value}")
                            except Exception as e:
                                print(f"❌ Error generating manifest for {pdf_file}: {e}")
                                traceback.print_exc()
                    except ImportError:
                        print("❌ IIIFService not found. Cannot generate manifest directly.")
            except Exception as e:
                print(f"❌ Error initializing services: {e}")
                traceback.print_exc()
    except Exception as e:
        print(f"❌ Error creating Flask app: {e}")
        traceback.print_exc()

def check_cantaloupe_access(record_id, filename=None, cantaloupe_url="http://localhost:8182"):
    """Check if Cantaloupe can access the PDF file."""
    if cantaloupe_url.endswith('/'):
        cantaloupe_url = cantaloupe_url[:-1]
    
    print(f"\n=== Checking Cantaloupe Access for Record {record_id} ===")
    
    if filename is None:
        # Try to get the filename from the record
        try:
            import requests
            response = requests.get(f"http://localhost:5000/api/records/{record_id}", verify=False)
            if response.status_code == 200:
                record_data = response.json()
                files = record_data.get("files", {}).get("entries", [])
                pdf_files = [f["key"] for f in files if f["key"].lower().endswith(".pdf")]
                if pdf_files:
                    filename = pdf_files[0]
                    print(f"Found PDF file: {filename}")
                else:
                    print("❌ No PDF files found in record.")
                    return
            else:
                print(f"❌ Failed to get record: {response.status_code}")
                print(f"Response: {response.text[:200]}..." if len(response.text) > 200 else f"Response: {response.text}")
                return
        except Exception as e:
            print(f"❌ Error getting record: {e}")
            return
    
    # Test various URL formats for Cantaloupe
    cantaloupe_urls = [
        f"{cantaloupe_url}/iiif/2/records%2F{record_id}%2F{filename}/info.json",
        f"{cantaloupe_url}/iiif/2/{record_id}%3A{filename}/info.json",
        f"{cantaloupe_url}/iiif/2/record%3A{record_id}%2Ffiles%3A{filename}/info.json"
    ]
    
    for url in cantaloupe_urls:
        print(f"\nChecking Cantaloupe URL: {url}")
        try:
            response = requests.get(url, verify=False)
            status = response.status_code
            print(f"Status: {status}")
            
            if status == 200:
                print(f"✅ Success! Cantaloupe can access this file.")
                print(f"Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
                try:
                    data = response.json()
                    print("Response structure:")
                    for key, value in list(data.items())[:5]:
                        if isinstance(value, (dict, list)) and len(str(value)) > 100:
                            print(f"  {key}: [complex object]")
                        else:
                            print(f"  {key}: {value}")
                    
                    # Also check if we can get a page image
                    image_url = f"{url.replace('/info.json', '')}/full/full/0/default.jpg"
                    print(f"\nTrying to get a page image: {image_url}")
                    img_response = requests.get(image_url, verify=False)
                    if img_response.status_code == 200:
                        print(f"✅ Successfully retrieved page image ({len(img_response.content)} bytes)")
                        print(f"Content-Type: {img_response.headers.get('Content-Type', 'Not specified')}")
                    else:
                        print(f"❌ Failed to get page image: {img_response.status_code}")
                except json.JSONDecodeError:
                    print("❌ Response is not valid JSON")
                    print(f"Response: {response.text[:200]}..." if len(response.text) > 200 else f"Response: {response.text}")
            else:
                print(f"❌ Failed to access: {response.text[:200]}..." if len(response.text) > 200 else f"❌ Failed to access: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")

def check_resource_endpoints(record_id):
    """Check if the server has the expected IIIF resource endpoints."""
    print("\n=== Checking Resource Endpoints ===")
    
    # Let's examine the application's URL routes
    try:
        from flask import current_app
        from invenio_app.factory import create_app
        
        app = create_app()
        with app.app_context():
            print("Examining URL routes...")
            
            # Get all registered routes
            iiif_routes = []
            for rule in app.url_map.iter_rules():
                if 'iiif' in rule.rule.lower():
                    endpoint = rule.endpoint
                    methods = ', '.join(rule.methods)
                    iiif_routes.append((rule.rule, endpoint, methods))
            
            # Sort and print routes
            for rule, endpoint, methods in sorted(iiif_routes, key=lambda x: x[0]):
                print(f"Route: {rule}")
                print(f"  Endpoint: {endpoint}")
                print(f"  Methods: {methods}")
                print("")
            
            # Check if the right resources are registered - safer way to check
            print("\nIIIF Resources:")
            resource_ext = app.extensions.get('invenio-resources', {})
            if hasattr(resource_ext, 'resources'):
                iiif_resources = []
                for resource_name, resource in resource_ext.resources.items():
                    if 'iiif' in resource_name.lower():
                        iiif_resources.append((resource_name, resource))
                
                if iiif_resources:
                    for name, resource in iiif_resources:
                        print(f"Resource: {name}")
                        print(f"  Type: {type(resource).__name__}")
                        print("")
                else:
                    print("❌ No IIIF resources found in registered resources")
            else:
                print("❌ Resources attribute not found in invenio-resources extension")
                
            # Check specifically for IIIF-related services
            print("\nChecking IIIF services:")
            rdm_ext = app.extensions.get("invenio-rdm-records")
            if rdm_ext and hasattr(rdm_ext, "iiif_service"):
                iiif_service = rdm_ext.iiif_service
                print(f"✅ Found IIIF service: {type(iiif_service).__name__}")
            else:
                print("❌ No IIIF service found")
            
            # Check extension registration
            print("\nChecking extensions:")
            for ext_name, ext in app.extensions.items():
                if 'iiif' in ext_name.lower() or 'zenodo' in ext_name.lower() or 'rdm' in ext_name.lower():
                    print(f"Extension: {ext_name}")
                    print(f"  Type: {type(ext).__name__}")
                    print("")
                    
            # Check if the PDF application is registered with Cantaloupe
            print("\nChecking Cantaloupe configuration:")
            cantaloupe_config = {}
            for key, value in current_app.config.items():
                if 'CANTALOUPE' in key:
                    cantaloupe_config[key] = value
            
            if cantaloupe_config:
                print("Cantaloupe configuration found:")
                for key, value in cantaloupe_config.items():
                    print(f"  {key}: {value}")
            else:
                print("❌ No Cantaloupe configuration found")
                
            # Check IIIF configurations
            print("\nIIIF Configurations:")
            iiif_configs = {k: v for k, v in current_app.config.items() if 'IIIF' in k}
            for key, value in iiif_configs.items():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"❌ Error checking resource endpoints: {e}")
        traceback.print_exc()

def test_manifest_url(record_id, filename=None):
    """Test IIIF manifest generation for a record internally and via the API.
    
    Args:
        record_id: The ID of the record to test
        filename: Optional filename to test specific file manifest
    """
    # Get the record
    record = get_record(record_id)
    if not record:
        print(f"❌ Failed to get record with ID {record_id}")
        return
    
    print(f"✅ Found record: {record.id} ({record.data.get('metadata', {}).get('title', 'No title')})")
    
    # Test internal manifest generation first
    print("\n📄 Testing internal manifest generation...")
    try:
        from invenio_rdm_records.resources.iiif import generate_manifest
        internal_manifest = generate_manifest(str(record.id))
        print(f"✅ Internal manifest generation successful")
        print(f"Manifest: {json.dumps(internal_manifest, indent=2)[:200]}...")
        
        # If we have a PDF filename, also test PDF manifest generation
        if filename and filename.lower().endswith('.pdf'):
            print("\n📚 Testing internal PDF manifest generation...")
            try:
                # Import the custom PDF manifest generator function
                from zenodo_rdm.resources.iiif import generate_pdf_manifest
                
                # Get file information
                files = record.files
                file_entries = files.entries
                pdf_file = None
                
                for key, file_entry in file_entries.items():
                    if key == filename:
                        pdf_file = file_entry
                        break
                
                if pdf_file:
                    # Attempt to generate the PDF manifest
                    pdf_manifest = generate_pdf_manifest(record, pdf_file)
                    print(f"✅ Internal PDF manifest generation successful")
                    print(f"PDF Manifest: {json.dumps(pdf_manifest, indent=2)[:200]}...")
                else:
                    print(f"❌ PDF file '{filename}' not found in record")
            except Exception as e:
                print(f"❌ Internal PDF manifest generation failed: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Internal manifest generation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test external manifest URL via HTTP
    print("\n🌐 Testing external manifest URL via HTTP...")
    
    # Get authenticated session
    session = get_authenticated_session()
    
    # Construct the manifest URL
    server_url = os.environ.get("INVENIO_SERVER_URL", "http://127.0.0.1:5000")
    if filename:
        manifest_url = f"{server_url}/api/iiif/record/{record_id}/manifest/{filename}"
    else:
        manifest_url = f"{server_url}/api/iiif/record/{record_id}/manifest"
    
    print(f"📡 Requesting manifest URL: {manifest_url}")
    
    try:
        response = session.get(manifest_url)
        if response.status_code == 200:
            print(f"✅ External manifest URL request successful")
            try:
                manifest_json = response.json()
                print(f"Manifest: {json.dumps(manifest_json, indent=2)[:200]}...")
            except:
                print(f"Response not JSON. Content: {response.text[:200]}...")
        else:
            print(f"❌ External manifest URL request failed: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ External manifest URL request failed: {e}")
        import traceback
        traceback.print_exc()

def get_record(record_id):
    """Get record information by ID.
    
    Args:
        record_id: The ID of the record to retrieve
        
    Returns:
        Record information dict or None if not found
    """
    try:
        from invenio_rdm_records.proxies import current_rdm_records
        from invenio_records_resources.services.errors import PermissionDeniedError

        # Get the record service
        record_service = current_rdm_records.records_service
        
        try:
            # Try to get the record with system identity (admin access)
            from invenio_access.permissions import system_identity
            record = record_service.read(system_identity, record_id)
            print(f"✅ Record {record_id} retrieved with system identity")
            return record
        except Exception as e1:
            print(f"⚠️ Failed to retrieve record with system identity: {e1}")
            
            try:
                # Try with anonymous identity
                from flask_security import AnonymousUser
                from invenio_access.permissions import Identity
                anonymous = Identity(0)
                anonymous.provides.add(AnonymousUser)
                
                record = record_service.read(anonymous, record_id)
                print(f"✅ Record {record_id} retrieved with anonymous identity")
                return record
            except PermissionDeniedError:
                print(f"❌ Permission denied for record {record_id}")
            except Exception as e2:
                print(f"❌ Failed to retrieve record with anonymous identity: {e2}")
                
    except ImportError as e:
        print(f"❌ Failed to import required modules: {e}")
    except Exception as e:
        print(f"❌ Unexpected error retrieving record {record_id}: {e}")
        traceback.print_exc()
    
    return None

def main():
    record_id = "202"  # Default record ID
    cantaloupe_url = "http://localhost:8182"  # Default Cantaloupe URL
    base_url = "http://localhost:5000"  # Default base URL
    filename = None  # Optional filename
    
    # Parse command line arguments
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith('--'):
            if arg == '--record' and i + 1 < len(sys.argv):
                record_id = sys.argv[i + 1]
                i += 2
            elif arg == '--cantaloupe' and i + 1 < len(sys.argv):
                cantaloupe_url = sys.argv[i + 1]
                i += 2
            elif arg == '--url' and i + 1 < len(sys.argv):
                base_url = sys.argv[i + 1]
                i += 2
            elif arg == '--file' and i + 1 < len(sys.argv):
                filename = sys.argv[i + 1]
                i += 2
            else:
                print(f"Unknown argument: {arg}")
                i += 1
        else:
            # Assume it's a record ID if it's just a number
            if arg.isdigit():
                record_id = arg
            i += 1
    
    print(f"=== Debugging IIIF Manifest Generation for Record {record_id} ===\n")
    print(f"Base URL: {base_url}")
    print(f"Cantaloupe URL: {cantaloupe_url}")
    if filename:
        print(f"Filename: {filename}")
    
    # Check Cantaloupe access
    check_cantaloupe_access(record_id, filename, cantaloupe_url)
    
    # Check resource endpoints
    check_resource_endpoints(record_id)
    
    # Test manifest URLs
    test_manifest_urls(record_id, base_url)
    
    # Test direct manifest generation
    test_direct_manifest_generation(record_id)
    
    # Test manifest URL
    test_manifest_url(record_id, filename)
    
    print("\n=== Debugging Complete ===")

if __name__ == "__main__":
    main() 
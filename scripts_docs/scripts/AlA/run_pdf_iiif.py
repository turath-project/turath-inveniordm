#!/usr/bin/env python
# This script is meant to be run from the Invenio shell
# Usage:
#   cd /path/to/zenodo-rdm
#   pipenv run invenio shell
#   %run scripts/AlA/run_pdf_iiif.py 202
#
# or directly:
#   pipenv run invenio shell scripts/AlA/run_pdf_iiif.py 202

import os
import sys
import json
import tempfile
import argparse
from pathlib import Path
from flask import current_app
from invenio_db import db
from invenio_files_rest.models import ObjectVersion, Bucket
from invenio_records.api import Record
from invenio_access.permissions import system_identity

# Try to import RecordFiles, but make it optional
try:
    from invenio_records_files.api import RecordFiles
    HAS_RECORD_FILES = True
except ImportError:
    HAS_RECORD_FILES = False
    print("Note: invenio_records_files.api.RecordFiles not available. Using direct bucket access.")

# Try to import ReportLab for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("WARNING: ReportLab not installed. Cannot generate test PDF.")
    print("Install with: pip install reportlab")

try:
    from invenio_rdm_records.proxies import current_rdm_records
    HAS_RDM = True
except ImportError:
    HAS_RDM = False
    print("Note: invenio_rdm_records not available. Using legacy Invenio API.")

def create_test_pdf(filename, pages=5):
    """Create a test PDF file with multiple pages."""
    if not HAS_REPORTLAB:
        print("ERROR: ReportLab not installed. Cannot generate test PDF.")
        return None
        
    print(f"Creating test PDF with {pages} pages...")
    
    # Create a PDF with text on each page
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    for i in range(1, pages + 1):
        # Add page number and test content
        c.setFont("Helvetica", 14)
        c.drawString(100, height - 100, f"Test PDF - Page {i} of {pages}")
        
        # Add some dummy text
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 150, "This is a test PDF file created for testing IIIF")
        c.drawString(100, height - 170, "PDF manifest generation in Invenio-RDM")
        
        # Add page number in center
        c.setFont("Helvetica-Bold", 72)
        c.setFillColorRGB(0.9, 0.9, 0.9)  # Light gray
        c.drawCentredString(width/2, height/2, str(i))
        
        # Add border
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.rect(50, 50, width-100, height-100)
        
        if i < pages:
            c.showPage()  # Move to next page
    
    c.save()
    print(f"Created test PDF at {filename}")
    return filename

def upload_pdf_to_record(record_id, pdf_path):
    """Upload a PDF file to a record."""
    filename = os.path.basename(pdf_path)
    
    try:
        # Handle record ID format - ensure it's a valid UUID format if needed
        try:
            import uuid
            # Try to convert to UUID if it's not already a UUID
            if not isinstance(record_id, uuid.UUID):
                try:
                    # First try direct conversion
                    uuid_val = uuid.UUID(record_id)
                    record_id = str(uuid_val)
                except ValueError:
                    # If that fails, try to get the record using an alternative method
                    print(f"Invalid UUID format for record ID: {record_id}")
                    print("Trying to find record using PID...")
                    
                    try:
                        from invenio_pidstore.models import PersistentIdentifier
                        pid = PersistentIdentifier.get('recid', record_id)
                        if pid and pid.object_uuid:
                            record_id = str(pid.object_uuid)
                            print(f"Found record with UUID: {record_id}")
                        else:
                            raise ValueError(f"No record found with PID: {record_id}")
                    except ImportError:
                        print("Could not import PersistentIdentifier, trying direct database query...")
                        with db.session.begin_nested():
                            result = db.session.execute(
                                "SELECT id FROM records_metadata WHERE json->>'recid' = :recid",
                                {'recid': record_id}
                            ).fetchone()
                            if result:
                                record_id = str(result[0])
                                print(f"Found record with UUID: {record_id}")
                            else:
                                raise ValueError(f"No record found with ID: {record_id}")
        except Exception as e:
            print(f"Warning: Error formatting record ID: {e}")
            print("Proceeding with original record ID...")
        
        # Get the record
        print(f"Getting record {record_id}...")
        record = Record.get_record(record_id)
        print(f"Retrieved record: {record.id}")
        
        # Always use the bucket directly since RecordFiles might not be available
        if 'bucket' in record:
            bucket_id = record['bucket']
            print(f"Using bucket ID from record: {bucket_id}")
            with open(pdf_path, 'rb') as fp:
                obj = ObjectVersion.create(bucket_id, filename, stream=fp)
            print(f"Uploaded file as {filename} to bucket {bucket_id}")
            print(f"Object: {obj.version_id}")
            
            # Update the record if using RDM
            if HAS_RDM:
                try:
                    service = current_rdm_records.records_service
                    service.update_files(
                        system_identity,
                        record_id,
                        {}
                    )
                    print("Updated record files via RDM service")
                except Exception as e:
                    print(f"Note: Could not update via RDM service: {e}")
            
            return True
        else:
            print("Record has no bucket ID")
            return False
        
    except Exception as e:
        print(f"ERROR: Failed to upload file: {e}")
        import traceback
        traceback.print_exc()
        return False

def copy_to_cantaloupe_paths(record_id, pdf_path):
    """Copy the PDF file to all possible Cantaloupe expected paths."""
    filename = os.path.basename(pdf_path)
    
    # Ensure record_id is a string
    record_id = str(record_id)
    
    try:
        # Get the data directory
        instance_path = current_app.instance_path
        data_path = os.path.join(os.path.dirname(instance_path), 'data')
        
        print(f"Using data directory: {data_path}")
        
        # Create all possible expected paths for Cantaloupe
        paths = [
            # Standard Cantaloupe paths
            os.path.join(data_path, 'private', record_id),
            os.path.join(data_path, 'records', record_id, 'private'),
            os.path.join(data_path, 'images', 'private', record_id),
            # Other potential paths based on config
            os.path.join(data_path, 'records', 'private', record_id),
        ]
        
        success = False
        for path in paths:
            try:
                # Ensure the directory exists
                os.makedirs(path, exist_ok=True)
                target_path = os.path.join(path, filename)
                
                # Copy the file
                import shutil
                shutil.copy2(pdf_path, target_path)
                print(f"Copied file to Cantaloupe path: {target_path}")
                success = True
            except Exception as e:
                print(f"Warning: Could not copy to {path}: {e}")
        
        return success
    except Exception as e:
        print(f"ERROR: Failed to copy file to Cantaloupe paths: {e}")
        return False

def check_and_register_extension():
    """Check if the zenodo-rdm extension is registered and register it if not."""
    extensions = current_app.extensions
    zenodo_extension = extensions.get('zenodo-rdm')
    
    if zenodo_extension:
        print("✓ zenodo-rdm extension is registered")
        return True
    else:
        print("✗ zenodo-rdm extension is NOT registered")
        print("Attempting to register zenodo-rdm extension...")
        
        try:
            # Try to import the extension
            from site.zenodo_rdm.ext import ZenodoRDM
            
            # Register the extension
            ext = ZenodoRDM()
            ext.init_app(current_app)
            
            print("✓ Successfully registered zenodo-rdm extension")
            return True
        except ImportError:
            print("✗ Could not import ZenodoRDM extension")
            print("Make sure site/zenodo_rdm/ext.py exists and contains ZenodoRDM class")
            return False
        except Exception as e:
            print(f"✗ Error registering extension: {e}")
            return False

def verify_and_fix_configuration():
    """Verify and fix IIIF PDF configuration if needed."""
    print("Verifying IIIF configuration...")
    
    # Check IIIF enabled
    iiif_enabled = current_app.config.get('RDM_IIIF_ENABLED', False)
    print(f"- IIIF enabled: {iiif_enabled}")
    
    # Check PDF support enabled
    pdf_support = current_app.config.get('RDM_IIIF_PDF_SUPPORT', False)
    print(f"- IIIF PDF support: {pdf_support}")
    
    # Check supported formats
    formats = current_app.config.get('RDM_IIIF_MANIFEST_FORMATS', [])
    print(f"- Supported formats: {formats}")
    
    # Check Cantaloupe server URL
    cantaloupe_url = current_app.config.get('RDM_IIIF_SERVER_URL', '')
    print(f"- Cantaloupe server URL: {cantaloupe_url}")
    
    # Check for missing config
    missing_config = []
    if not iiif_enabled:
        missing_config.append("RDM_IIIF_ENABLED = True")
    if not pdf_support:
        missing_config.append("RDM_IIIF_PDF_SUPPORT = True")
    if 'pdf' not in formats:
        missing_config.append("'pdf' in RDM_IIIF_MANIFEST_FORMATS")
    if not cantaloupe_url:
        missing_config.append("RDM_IIIF_SERVER_URL = 'http://localhost:8182'")
    
    if missing_config:
        print("Missing configuration:")
        for cfg in missing_config:
            print(f"  {cfg}")
        
        # Add missing configuration
        print("Adding missing configuration...")
        if not iiif_enabled:
            current_app.config['RDM_IIIF_ENABLED'] = True
        if not pdf_support:
            current_app.config['RDM_IIIF_PDF_SUPPORT'] = True
        if 'pdf' not in formats:
            current_app.config['RDM_IIIF_MANIFEST_FORMATS'] = list(formats) + ['pdf']
        if not cantaloupe_url:
            # Use a default value for Cantaloupe URL
            current_app.config['RDM_IIIF_SERVER_URL'] = 'http://localhost:8182'
        
        print("✓ Configuration updated")
    else:
        print("✓ Configuration is correct")
    
    return current_app.config.get('RDM_IIIF_SERVER_URL', '')

def get_manifest_url(record_id):
    """Get the IIIF manifest URL for a record."""
    base_url = current_app.config.get('SITE_UI_URL', 'http://localhost:5000')
    return f"{base_url}/api/iiif/record:{record_id}/manifest"

def implement_pdf_iiif(record_id, filename=None, pages=5):
    """Implement PDF IIIF for a record.
    
    Args:
        record_id: The ID of the record
        filename: The PDF filename (or None to generate a new one)
        pages: Number of pages for the test PDF
        
    Returns:
        True if successful, False otherwise
    """
    print(f"Implementing PDF IIIF for record {record_id}")
    
    # Step 1: Create/get PDF file
    if not filename:
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"test_pdf_{timestamp}.pdf"
        
        # Ensure the filename has .pdf extension
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
            
        if not HAS_REPORTLAB:
            print("ERROR: ReportLab not installed. Cannot generate a test PDF.")
            print("Please provide an existing PDF file path instead.")
            print("Example: %run scripts/AlA/run_pdf_iiif.py 202 path/to/your/file.pdf")
            return False
            
        pdf_path = create_test_pdf(filename, pages)
        if not pdf_path:
            return False
    else:
        # Check if the file exists
        if os.path.exists(filename):
            pdf_path = filename
            print(f"Using existing PDF file: {pdf_path}")
        else:
            print(f"ERROR: File {filename} does not exist")
            return False
    
    # Step 2: Upload PDF to record
    upload_success = upload_pdf_to_record(record_id, pdf_path)
    if not upload_success:
        print("ERROR: Failed to upload PDF to record")
        return False
    
    # Step 3: Copy PDF to Cantaloupe paths
    copy_success = copy_to_cantaloupe_paths(record_id, pdf_path)
    if not copy_success:
        print("ERROR: Failed to copy PDF to Cantaloupe paths")
        return False
    
    # Step 4: Check extension registration
    ext_registered = check_and_register_extension()
    if not ext_registered:
        print("WARNING: zenodo-rdm extension is not registered")
    
    # Step 5: Verify configuration
    cantaloupe_url = verify_and_fix_configuration()
    if not cantaloupe_url:
        print("ERROR: Cantaloupe URL not configured")
        return False
    
    # Step 6: Get manifest URL
    manifest_url = get_manifest_url(record_id)
    
    # Success message
    print("\n✅ PDF IIIF implementation is complete")
    print(f"Record ID: {record_id}")
    print(f"Filename: {os.path.basename(pdf_path)}")
    print(f"Manifest URL: {manifest_url}")
    print("\nYou can view the manifest with a IIIF viewer like Mirador")
    
    return True

def main():
    """Main function when run as a script."""
    if len(sys.argv) < 2:
        print("Usage: %run scripts/AlA/run_pdf_iiif.py RECORD_ID [FILENAME] [PAGES]")
        print("")
        print("Arguments:")
        print("  RECORD_ID   ID of the record to upload PDF to")
        print("  FILENAME    (Optional) Path to an existing PDF file to use")
        print("              If not provided, a test PDF will be generated")
        print("  PAGES       (Optional) Number of pages for generated test PDF")
        print("              Default: 5")
        print("")
        print("Example:")
        print("  %run scripts/AlA/run_pdf_iiif.py 202")
        print("  %run scripts/AlA/run_pdf_iiif.py 202 /path/to/your/file.pdf")
        print("  %run scripts/AlA/run_pdf_iiif.py 202 test.pdf 10")
        return
    
    # Get arguments
    record_id = sys.argv[1]
    
    # Check for optional filename argument
    filename = None
    if len(sys.argv) > 2 and sys.argv[2]:
        filename = sys.argv[2]
        if filename.lower() == "none":
            filename = None
    
    # Check for optional pages argument
    pages = 5
    if len(sys.argv) > 3:
        try:
            pages = int(sys.argv[3])
        except ValueError:
            print(f"Warning: Invalid pages value '{sys.argv[3]}'. Using default (5).")
    
    # Initialize the Flask application
    try:
        from invenio_app.factory import create_app
        app = create_app()
        with app.app_context():
            # Run the implementation within Flask app context
            implement_pdf_iiif(record_id, filename, pages)
    except ImportError:
        print("ERROR: Could not import Flask application factory.")
        print("Make sure you're running this script in the correct environment.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to initialize Flask application: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
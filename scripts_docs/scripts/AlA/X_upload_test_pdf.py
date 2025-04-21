#!/usr/bin/env python
import os
import sys
import argparse
import tempfile
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

try:
    from invenio_app.factory import create_app
    from invenio_db import db
    from invenio_access.permissions import system_identity
    from invenio_files_rest.models import ObjectVersion
    from invenio_records_files.api import RecordFiles
    from invenio_records.api import Record
    from invenio_rdm_records.proxies import current_rdm_records
except ImportError:
    print("ERROR: Cannot import Invenio modules. Make sure you're running this script in the Invenio virtual environment.")
    sys.exit(1)


def create_test_pdf(pages=5, filename=None):
    """Create a test PDF file with the specified number of pages.
    
    Args:
        pages: Number of pages to create (default: 5)
        filename: Optional filename to save to, otherwise creates a temp file
        
    Returns:
        Path to the created PDF file
    """
    if filename:
        pdf_path = filename
    else:
        # Create a temporary file
        fd, pdf_path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)
    
    # Create a PDF with text on each page
    c = canvas.Canvas(pdf_path, pagesize=letter)
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
    print(f"Created test PDF at {pdf_path} with {pages} pages")
    return pdf_path


def upload_pdf_to_record(record_id, pdf_path, filename=None):
    """Upload a PDF file to a record.
    
    Args:
        record_id: The ID of the record to upload to
        pdf_path: Path to the PDF file to upload
        filename: Optional filename to use (default: use basename of pdf_path)
        
    Returns:
        True if successful, False otherwise
    """
    if not filename:
        filename = os.path.basename(pdf_path)
    
    # Ensure the filename has a .pdf extension
    if not filename.lower().endswith('.pdf'):
        filename += '.pdf'
    
    app = create_app()
    with app.app_context():
        try:
            # Get the record
            print(f"Getting record {record_id}...")
            record = Record.get_record(record_id)
            print(f"Retrieved record: {record.id}")
            
            # Check if record has files
            if not hasattr(record, 'files'):
                print("Record doesn't have files attribute")
                # Try to use the bucket directly
                if 'bucket' in record:
                    bucket_id = record['bucket']
                    print(f"Using bucket ID from record: {bucket_id}")
                    with open(pdf_path, 'rb') as fp:
                        obj = ObjectVersion.create(bucket_id, filename, stream=fp)
                    print(f"Uploaded file as {filename} to bucket {bucket_id}")
                    print(f"Object: {obj.version_id}")
                    return True
                else:
                    print("Record has no bucket ID")
                    return False
            
            # Upload the file to the record
            print(f"Uploading {filename} to record {record_id}...")
            with open(pdf_path, 'rb') as fp:
                record.files[filename] = fp
            record.files.flush()
            db.session.commit()
            print(f"Successfully uploaded {filename} to record {record_id}")
            
            # Update the record if using RDM
            try:
                # Try to use RDM Records service for updating
                service = current_rdm_records.records_service
                service.update_files(
                    system_identity,
                    record_id,
                    {}
                )
                print("Updated record files via RDM service")
            except Exception as e:
                print(f"Note: Could not update via RDM service: {e}")
                print("This is normal for legacy Invenio installations")
            
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to upload file: {e}")
            import traceback
            traceback.print_exc()
            return False


def copy_to_cantaloupe_path(record_id, pdf_path, filename=None):
    """Copy the PDF file to the Cantaloupe expected path.
    
    Args:
        record_id: The ID of the record
        pdf_path: Path to the PDF file
        filename: Optional filename to use (default: use basename of pdf_path)
        
    Returns:
        True if successful, False otherwise
    """
    if not filename:
        filename = os.path.basename(pdf_path)
    
    app = create_app()
    with app.app_context():
        try:
            # Get the data directory
            instance_path = app.instance_path
            data_path = os.path.join(os.path.dirname(instance_path), 'data')
            
            # Create the expected paths for Cantaloupe
            paths = [
                # Standard Cantaloupe paths
                os.path.join(data_path, 'private', record_id),
                os.path.join(data_path, 'records', record_id, 'private'),
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
            print(f"ERROR: Failed to copy file to Cantaloupe path: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='Upload a test PDF file to a record')
    parser.add_argument('--record', '-r', required=True, help='Record ID to upload to')
    parser.add_argument('--pages', '-p', type=int, default=5, help='Number of pages in the test PDF (default: 5)')
    parser.add_argument('--filename', '-f', help='Filename to use for the PDF (default: test_pdf_<timestamp>.pdf)')
    parser.add_argument('--copy-only', '-c', action='store_true', help='Only copy to Cantaloupe path, do not upload to record')
    parser.add_argument('--input-pdf', '-i', help='Path to an existing PDF file to use instead of generating one')
    
    args = parser.parse_args()
    
    # Set default filename if not provided
    if not args.filename:
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        args.filename = f"test_pdf_{timestamp}.pdf"
    
    # Use existing PDF or create a new one
    if args.input_pdf:
        pdf_path = args.input_pdf
        print(f"Using existing PDF: {pdf_path}")
    else:
        pdf_path = create_test_pdf(args.pages, args.filename)
    
    success = True
    
    # Upload to record if not copy-only
    if not args.copy_only:
        upload_success = upload_pdf_to_record(args.record, pdf_path, args.filename)
        if not upload_success:
            print("WARNING: Failed to upload PDF to record")
            success = False
    
    # Copy to Cantaloupe path
    copy_success = copy_to_cantaloupe_path(args.record, pdf_path, args.filename)
    if not copy_success:
        print("WARNING: Failed to copy PDF to Cantaloupe path")
        success = False
    
    # Clean up temporary file if we created one
    if not args.input_pdf and not os.path.samefile(pdf_path, args.filename):
        try:
            os.unlink(pdf_path)
            print(f"Removed temporary file: {pdf_path}")
        except Exception as e:
            print(f"Note: Failed to remove temporary file {pdf_path}: {e}")
    
    if success:
        print("\nSUCCESS: PDF is ready for testing IIIF manifest generation")
        print(f"Record ID: {args.record}")
        print(f"Filename: {args.filename}")
        print("\nNext steps:")
        print(f"1. Run the diagnostic tool: python scripts/AlA/diagnose_pdf_manifest.py --record {args.record} --file {args.filename}")
        print(f"2. Test debug script: python scripts/AlA/debug_iiif_manifest.py --record {args.record} --file {args.filename}")
    else:
        print("\nWARNING: Some operations failed. PDF may not be fully ready for testing.")
    
if __name__ == '__main__':
    main() 
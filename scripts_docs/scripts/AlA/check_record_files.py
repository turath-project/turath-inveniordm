#!/usr/bin/env python
"""Check record files in the system."""

import sys
import json
import traceback
from invenio_app.factory import create_app
from flask import current_app

def check_record(record_id):
    """Check record and its files."""
    app = create_app()
    
    with app.app_context():
        try:
            # Get the service from app extensions
            service = current_app.extensions['invenio-rdm-records'].records_service
            
            # Check service method signature
            print(f"Service type: {type(service)}")
            
            # Create an identity with system scope
            from invenio_access.permissions import system_identity
            
            # Try to read the record with system identity
            record = service.read(system_identity, record_id)
            
            print(f"Record ID: {record_id}")
            print(f"Record title: {record.data['metadata']['title']}")
            
            # Dump the files section to see the exact structure
            print("\nFiles section from record data:")
            files_section = record.data.get('files', {})
            print(json.dumps(files_section, indent=2))
                
            # Try to get file metadata through a direct database query
            try:
                from sqlalchemy import text
                from invenio_db import db
                
                # Query file info directly from the database
                sql = text("""
                    SELECT f.key, f.mimetype, f.size, f.checksum
                    FROM files_files f
                    JOIN files_object o ON f.id = o.file_id
                    JOIN rdm_records_records r ON r.bucket_id = o.bucket_id
                    WHERE r.id = :record_id
                """)
                
                result = db.session.execute(sql, {"record_id": record_id})
                
                print("\nFiles from database query:")
                for row in result:
                    file_key = row[0]
                    mimetype = row[1]
                    size = row[2]
                    checksum = row[3]
                    print(f"- {file_key} ({size} bytes, {mimetype})")
                    
                    if mimetype == 'application/pdf':
                        print(f"  This is a PDF file")
                        cantaloupe_path = f"private/{record_id}/{file_key}"
                        pdf_url = f"{current_app.config.get('RDM_IIIF_SERVER_URL', 'http://localhost:8182')}/iiif/2/{cantaloupe_path.replace('/', '%2F')}/info.json"
                        print(f"  Cantaloupe info URL: {pdf_url}")
                        
                        # Check if IIIF PDF support is enabled
                        iiif_formats = current_app.config.get('RDM_IIIF_MANIFEST_FORMATS', [])
                        pdf_support = current_app.config.get('RDM_IIIF_PDF_SUPPORT', False)
                        print(f"  IIIF PDF support enabled: {pdf_support}")
                        print(f"  PDF in IIIF formats: {'pdf' in iiif_formats}")
                        
                        # Check if the file actually exists in the expected location
                        import os
                        data_dir = current_app.instance_path
                        pdf_path = os.path.join(data_dir, "data", "records", record_id, "files", file_key)
                        print(f"  Local file exists: {os.path.exists(pdf_path)} ({pdf_path})")
                        
            except Exception as e:
                print(f"Error accessing file metadata from database: {str(e)}")
                traceback.print_exc()
                
        except Exception as e:
            print(f"Error accessing record {record_id}: {str(e)}")
            traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} RECORD_ID")
        sys.exit(1)
        
    record_id = sys.argv[1]
    check_record(record_id) 
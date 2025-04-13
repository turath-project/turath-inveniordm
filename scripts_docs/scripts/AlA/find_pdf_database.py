#!/usr/bin/env python3
"""
Script to search for PDF files in database records.
"""
import os
import sys
import json

try:
    from flask import current_app
    from invenio_app.factory import create_app
    from invenio_db import db
    from invenio_files_rest.models import ObjectVersion, FileInstance, Bucket
    from invenio_pidstore.models import PersistentIdentifier
    from invenio_records.models import RecordMetadata
    from sqlalchemy import or_
except ImportError:
    print("Error: This script requires the Invenio modules.")
    sys.exit(1)

def search_for_pdf_files():
    """Search specifically for PDF files."""
    print("\n=== Searching for PDF files in database records ===\n")
    
    # Search for PDF files
    obj_versions = ObjectVersion.query.filter(
        ObjectVersion.key.ilike('%.pdf')
    ).all()
    
    print(f"Found {len(obj_versions)} PDF files in database records:")
    
    for i, obj in enumerate(obj_versions, 1):
        print(f"\n{i}. File: {obj.key}")
        print(f"   Bucket ID: {obj.bucket_id}")
        
        # Get file info
        if obj.file_id:
            file_instance = FileInstance.query.filter_by(id=obj.file_id).first()
            if file_instance:
                print(f"   File ID: {file_instance.id}")
                print(f"   URI: {file_instance.uri}")
                print(f"   Size: {file_instance.size} bytes")
                
                # Check if file exists on disk
                if file_instance.uri.startswith('file://'):
                    file_path = file_instance.uri[7:]  # Remove 'file://' prefix
                    if os.path.exists(file_path):
                        print(f"   ✅ File exists at: {file_path}")
                    else:
                        print(f"   ❌ File does not exist at: {file_path}")
                else:
                    file_path = file_instance.uri
                    if os.path.exists(file_path):
                        print(f"   ✅ File exists at: {file_path}")
                    else:
                        print(f"   ❌ File does not exist at: {file_path}")
            else:
                print("   File instance not found!")
        else:
            print("   No file attached!")
        
        # Try to find record by bucket
        try:
            # Get record by bucket ID using a safer approach
            records = RecordMetadata.query.all()
            matching_records = []
            
            for record in records:
                try:
                    json_data = record.json
                    if 'files' in json_data and 'bucket' in json_data['files']:
                        if json_data['files']['bucket'] == obj.bucket_id:
                            matching_records.append(record)
                except Exception as e:
                    continue
            
            if matching_records:
                for record in matching_records:
                    record_id = record.id
                    
                    # Get record PID
                    pid = PersistentIdentifier.query.filter_by(
                        object_type='rec',
                        object_uuid=record_id
                    ).first()
                    
                    if pid:
                        print(f"   Record: {pid.pid_value} ({record_id})")
                        
                        # Check for expected symlink
                        symlink_path = f"data/records/{pid.pid_value}/{obj.key}"
                        abs_symlink_path = os.path.join(current_app.instance_path, symlink_path)
                        
                        if os.path.exists(abs_symlink_path):
                            if os.path.islink(abs_symlink_path):
                                link_target = os.readlink(abs_symlink_path)
                                print(f"   ✅ Symlink exists: {abs_symlink_path} -> {link_target}")
                            else:
                                print(f"   ✅ File exists (not a symlink): {abs_symlink_path}")
                        else:
                            print(f"   ❌ No file/symlink at: {abs_symlink_path}")
                        
                        # Check Cantaloupe expected path
                        cantaloupe_path = f"{pid.pid_value}/{obj.key}"
                        print(f"   Cantaloupe would look for: {cantaloupe_path}")
            else:
                print("   No record found for this bucket!")
        except Exception as e:
            print(f"   Error finding record: {e}")

def main():
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            search_for_pdf_files()
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main() 
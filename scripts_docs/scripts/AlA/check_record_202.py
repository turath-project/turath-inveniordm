#!/usr/bin/env python3
"""
Script to check record 202 and its PDF file.
"""
import os
import sys
import json
import uuid

try:
    from flask import current_app
    from invenio_app.factory import create_app
    from invenio_db import db
    from invenio_files_rest.models import ObjectVersion, FileInstance, Bucket
    from invenio_pidstore.models import PersistentIdentifier, PIDStatus
    from invenio_records.models import RecordMetadata
    from invenio_records_files.api import RecordsBuckets
    from sqlalchemy import inspect
except ImportError:
    print("Error: This script requires the Invenio modules.")
    sys.exit(1)

def check_record_202():
    """Check record 202 and its associated files."""
    print("\n=== Checking record 202 and its PDF file ===\n")
    
    # Get record 202
    pid = PersistentIdentifier.query.filter_by(
        pid_type='recid',
        pid_value='202'
    ).first()
    
    if not pid:
        print("Record 202 not found in PersistentIdentifier table!")
        return
    
    print(f"Found record 202 in PersistentIdentifier table:")
    print(f"  UUID: {pid.object_uuid}")
    print(f"  Status: {pid.status}")
    print(f"  Type: {pid.pid_type}")
    print(f"  Created: {pid.created}")
    print(f"  Updated: {pid.updated}")
    
    # Check if UUID is valid
    try:
        uuid_obj = uuid.UUID(str(pid.object_uuid))
        print(f"  UUID format is valid: {uuid_obj}")
    except ValueError:
        print(f"  ⚠️ UUID format is INVALID: {pid.object_uuid}")
    
    # Get record metadata directly with SQLAlchemy
    try:
        connection = db.engine.connect()
        result = connection.execute(f"SELECT * FROM records_metadata WHERE id = '{pid.object_uuid}'")
        record_row = result.fetchone()
        connection.close()
        
        if record_row:
            print("\nRecord found in records_metadata table:")
            for column, value in zip(result.keys(), record_row):
                if column == 'json':
                    json_data = value
                    print(f"  {column}: {json.dumps(value, indent=2)[:300]}...")
                else:
                    print(f"  {column}: {value}")
        else:
            print("\n⚠️ Record NOT found in records_metadata table!")
            
            # Check if table exists
            inspector = inspect(db.engine)
            if 'records_metadata' in inspector.get_table_names():
                print("  The records_metadata table exists, but no record with this UUID was found.")
            else:
                print("  ⚠️ The records_metadata table does not exist in the database!")
    except Exception as e:
        print(f"\nError querying records_metadata table: {e}")
    
    # Check for history00871.pdf in ObjectVersion
    print("\n=== Checking for history00871.pdf in ObjectVersion table ===")
    pdf_objects = ObjectVersion.query.filter(
        ObjectVersion.key == 'history00871.pdf'
    ).all()
    
    if pdf_objects:
        print(f"Found {len(pdf_objects)} objects with key 'history00871.pdf':")
        
        for i, obj in enumerate(pdf_objects, 1):
            print(f"\n{i}. Object with key 'history00871.pdf':")
            print(f"   Bucket ID: {obj.bucket_id}")
            print(f"   Version ID: {obj.version_id}")
            
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
                    else:
                        file_path = file_instance.uri
                        
                    if os.path.exists(file_path):
                        print(f"   ✅ File exists at: {file_path}")
                    else:
                        print(f"   ❌ File does not exist at: {file_path}")
                    
                    # Check for specific path
                    target_path = "/Users/alaabarazi/Projects/Turath/Coding/zenodo-rdm/.venv/var/instance/data/30/dc/0978-0634-40fb-9c30-782a5ccd68c6/data"
                    if file_path == target_path:
                        print(f"   ✓ Confirmed: This is the file at {target_path}")
                    else:
                        print(f"   File is at: {file_path}")
                        print(f"   Not at expected path: {target_path}")
                else:
                    print("   File instance not found!")
            else:
                print("   No file attached!")
            
            # Try to find associated record
            try:
                # Check RecordsBuckets table
                rb = RecordsBuckets.query.filter_by(bucket_id=obj.bucket_id).first()
                if rb:
                    print(f"   Found record {rb.record_id} in RecordsBuckets for this bucket")
                    
                    # Check if this record matches record 202
                    if str(rb.record_id) == str(pid.object_uuid):
                        print(f"   ✓ Confirmed: This bucket is associated with record 202")
                    else:
                        print(f"   ⚠️ This bucket is associated with a different record: {rb.record_id}")
                else:
                    print("   No record found in RecordsBuckets for this bucket")
            except Exception as e:
                print(f"   Error checking RecordsBuckets: {e}")
    else:
        print("No objects with key 'history00871.pdf' found in ObjectVersion table.")
    
    # Check symlinks in instance directory
    print("\n=== Checking for symlinks in instance directory ===")
    instance_path = current_app.instance_path
    print(f"Instance path: {instance_path}")
    
    record_dir_path = os.path.join(instance_path, "data", "records", "202")
    pdf_path = os.path.join(record_dir_path, "history00871.pdf")
    
    print(f"Checking for directory: {record_dir_path}")
    if os.path.exists(record_dir_path):
        print(f"✅ Directory exists: {record_dir_path}")
        
        # List contents
        dir_contents = os.listdir(record_dir_path)
        print(f"Directory contents: {dir_contents}")
    else:
        print(f"❌ Directory does not exist: {record_dir_path}")
    
    print(f"\nChecking for file: {pdf_path}")
    if os.path.exists(pdf_path):
        if os.path.islink(pdf_path):
            link_target = os.readlink(pdf_path)
            print(f"✅ Symlink exists: {pdf_path} -> {link_target}")
        else:
            print(f"✅ File exists (not a symlink): {pdf_path}")
    else:
        print(f"❌ File does not exist: {pdf_path}")

def main():
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            check_record_202()
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Script to find where files are stored in the database and filesystem.
"""
import os
import sys
import json
from datetime import datetime

try:
    from flask import current_app
    from invenio_app.factory import create_app
    from invenio_db import db
    from invenio_files_rest.models import ObjectVersion, FileInstance, Bucket
    from invenio_pidstore.models import PersistentIdentifier
    from invenio_records.models import RecordMetadata
    from sqlalchemy import func
except ImportError:
    print("Error: This script requires the Invenio modules.")
    sys.exit(1)

def find_files_for_record(record_id):
    """Find files associated with a record in the database."""
    print(f"\n=== Files for Record {record_id} ===\n")
    
    # Get the record's UUID from PID
    pid = PersistentIdentifier.query.filter_by(
        pid_type='recid', pid_value=record_id
    ).first()
    
    if not pid:
        print(f"Record with ID {record_id} not found!")
        return
    
    print(f"Record UUID: {pid.object_uuid}")
    
    # Get record from RecordMetadata
    record = RecordMetadata.query.filter_by(id=pid.object_uuid).first()
    if not record:
        print(f"Record metadata not found for UUID {pid.object_uuid}")
        return
    
    # Get JSON
    record_json = record.json
    print(f"Record JSON: {json.dumps(record_json, indent=2)[:1000]}...")
    
    # Get the bucket associated with the record
    bucket_id = None
    if 'files' in record_json:
        if 'bucket' in record_json['files']:
            bucket_id = record_json['files']['bucket']
    
    if not bucket_id:
        print("No bucket found for this record!")
        return
    
    print(f"Bucket ID: {bucket_id}")
    
    # Get files from the bucket
    object_versions = ObjectVersion.query.filter_by(bucket_id=bucket_id).all()
    print(f"Files in bucket: {len(object_versions)}")
    
    for obj in object_versions:
        print(f"\nFile: {obj.key}")
        print(f"  Version: {obj.version_id}")
        if obj.file_id:
            file_instance = FileInstance.query.filter_by(id=obj.file_id).first()
            if file_instance:
                print(f"  File ID: {file_instance.id}")
                print(f"  URI: {file_instance.uri}")
                print(f"  Size: {file_instance.size} bytes")
                print(f"  Checksum: {file_instance.checksum}")
                if file_instance.uri.startswith('file://'):
                    file_path = file_instance.uri[7:]  # Remove 'file://' prefix
                    if os.path.exists(file_path):
                        print(f"  ✅ File exists at: {file_path}")
                        print(f"    Size on disk: {os.path.getsize(file_path)} bytes")
                        mtime = os.path.getmtime(file_path)
                        print(f"    Last modified: {datetime.fromtimestamp(mtime)}")
                    else:
                        print(f"  ❌ File does not exist at: {file_path}")
            else:
                print("  File instance not found!")
        else:
            print("  No file attached!")

def find_symlinks_for_record(record_id):
    """Find symlinks that should point to the record's files."""
    print(f"\n=== Expected Symlinks for Record {record_id} ===\n")
    
    # Standard paths where symlinks might be
    symlink_paths = [
        f"data/records/{record_id}",
        f".venv/var/instance/data/records/{record_id}",
        f"var/instance/data/records/{record_id}"
    ]
    
    for path in symlink_paths:
        if os.path.exists(path):
            print(f"✅ Directory exists: {path}")
            # List files
            files = os.listdir(path)
            for file in files:
                file_path = os.path.join(path, file)
                if os.path.islink(file_path):
                    target = os.readlink(file_path)
                    print(f"  Symlink: {file} -> {target}")
                    if os.path.exists(file_path):
                        print(f"    ✅ Target exists")
                    else:
                        print(f"    ❌ Target does not exist")
                else:
                    print(f"  Regular file: {file} ({os.path.getsize(file_path)} bytes)")
        else:
            print(f"❌ Directory does not exist: {path}")

def check_record_files_extension():
    """Check if the record-files extension is enabled."""
    print("\n=== Record-Files Extension Status ===\n")
    
    try:
        # Check if the extension is registered
        extensions = current_app.extensions
        if 'invenio-records-files' in extensions:
            print("✅ invenio-records-files extension is registered")
        else:
            print("❌ invenio-records-files extension is NOT registered")
            
        # Check the storage factory configuration
        storage_factory = current_app.config.get('FILES_REST_STORAGE_FACTORY')
        print(f"Storage factory: {storage_factory}")
        
        # Check for custom file processors
        file_processors = current_app.config.get('RDM_RECORDS_FILE_METADATA_PROCESSORS', [])
        print(f"File processors: {file_processors}")
    except Exception as e:
        print(f"Error checking extensions: {e}")

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} RECORD_ID")
        sys.exit(1)
        
    record_id = sys.argv[1]
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        find_files_for_record(record_id)
        find_symlinks_for_record(record_id)
        check_record_files_extension()

if __name__ == "__main__":
    main() 
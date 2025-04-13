#!/usr/bin/env python3
"""
Script to search for TIF files in database records.
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

def search_for_file_pattern(pattern):
    """Search for files matching a pattern in all records."""
    print(f"\n=== Searching for files matching pattern: {pattern} ===\n")
    
    # Search object versions for matching keys
    obj_versions = ObjectVersion.query.filter(
        ObjectVersion.key.ilike(f'%{pattern}%')
    ).all()
    
    print(f"Found {len(obj_versions)} matching files:")
    
    for i, obj in enumerate(obj_versions, 1):
        print(f"\n{i}. File: {obj.key}")
        print(f"   Bucket ID: {obj.bucket_id}")
        print(f"   Version: {obj.version_id}")
        
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
                print("   File instance not found!")
        else:
            print("   No file attached!")
        
        # Try to find record by bucket
        try:
            # Using raw SQL to work around JSON query issues
            query = """
            SELECT rm.id, rm.json
            FROM records_metadata rm
            WHERE rm.json::text LIKE %s
            """
            params = (f'%"bucket": "{obj.bucket_id}"%',)
            result = db.session.execute(query, params).fetchall()
            
            if result:
                for row in result:
                    record_id = row[0]
                    record_json = row[1]
                    
                    # Get record PID
                    pid = PersistentIdentifier.query.filter_by(
                        object_type='rec',
                        object_uuid=record_id
                    ).first()
                    
                    if pid:
                        print(f"   Record: {pid.pid_value} ({record_id})")
                        
                        # Check for expected symlink
                        symlink_path = f"data/records/{pid.pid_value}/{obj.key}"
                        if os.path.exists(symlink_path):
                            if os.path.islink(symlink_path):
                                link_target = os.readlink(symlink_path)
                                print(f"   ✅ Symlink exists: {symlink_path} -> {link_target}")
                            else:
                                print(f"   ✅ File exists (not a symlink): {symlink_path}")
                        else:
                            print(f"   ❌ No file/symlink at: {symlink_path}")
            else:
                print("   No record found for this bucket!")
        except Exception as e:
            print(f"   Error finding record: {e}")
        

def search_for_tif_files():
    """Search specifically for TIF files."""
    print("\n=== Searching for TIF/TIFF files ===\n")
    
    # Search for TIF files
    obj_versions = ObjectVersion.query.filter(
        or_(
            ObjectVersion.key.ilike('%.tif'),
            ObjectVersion.key.ilike('%.tiff')
        )
    ).all()
    
    print(f"Found {len(obj_versions)} TIF/TIFF files:")
    
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
                print("   File instance not found!")
        else:
            print("   No file attached!")
        
        # Try to find record by bucket
        try:
            # Using raw SQL to work around JSON query issues
            query = """
            SELECT rm.id, rm.json
            FROM records_metadata rm
            WHERE rm.json::text LIKE %s
            """
            params = (f'%"bucket": "{obj.bucket_id}"%',)
            result = db.session.execute(query, params).fetchall()
            
            if result:
                for row in result:
                    record_id = row[0]
                    record_json = row[1]
                    
                    # Get record PID
                    pid = PersistentIdentifier.query.filter_by(
                        object_type='rec',
                        object_uuid=record_id
                    ).first()
                    
                    if pid:
                        print(f"   Record: {pid.pid_value} ({record_id})")
                        
                        # Check for expected symlink
                        symlink_path = f"data/records/{pid.pid_value}/{obj.key}"
                        if os.path.exists(symlink_path):
                            if os.path.islink(symlink_path):
                                link_target = os.readlink(symlink_path)
                                print(f"   ✅ Symlink exists: {symlink_path} -> {link_target}")
                            else:
                                print(f"   ✅ File exists (not a symlink): {symlink_path}")
                        else:
                            print(f"   ❌ No file/symlink at: {symlink_path}")
            else:
                print("   No record found for this bucket!")
        except Exception as e:
            print(f"   Error finding record: {e}")

def main():
    if len(sys.argv) > 1:
        pattern = sys.argv[1]
    else:
        pattern = None
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            if pattern:
                search_for_file_pattern(pattern)
            else:
                search_for_tif_files()
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main() 
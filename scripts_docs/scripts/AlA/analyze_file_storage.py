#!/usr/bin/env python
"""
Analyze File Storage in Invenio-RDM.
This script examines how files are stored in the system after upload.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from uuid import UUID

# Try to import Invenio modules
try:
    from flask import current_app
    from invenio_app.factory import create_app
    from invenio_db import db
    from invenio_files_rest.models import FileInstance, Location, ObjectVersion, Bucket
    from invenio_records_files.api import RecordFiles
    from invenio_records.api import Record
    from invenio_rdm_records.records.api import RDMRecord
    HAS_INVENIO = True
except ImportError:
    HAS_INVENIO = False

def load_app_context():
    """Load the Flask app context."""
    if not HAS_INVENIO:
        print("Invenio modules not available. Running in limited mode.")
        return None
    
    print("Loading Invenio app context...")
    app = create_app()
    return app

def check_database_file_structure():
    """Check the database file structure."""
    if not HAS_INVENIO:
        print("Cannot check database - Invenio modules not available.")
        return
    
    print("\n=== Database File Structure ===")
    
    try:
        # Check locations
        locations = Location.query.all()
        print(f"\nFile Storage Locations ({len(locations)}):")
        for loc in locations:
            print(f"  - ID: {loc.id}")
            print(f"    Name: {loc.name}")
            print(f"    URI: {loc.uri}")
            print(f"    Default: {loc.default}")
    
        # Check buckets
        buckets = Bucket.query.limit(5).all()
        bucket_count = Bucket.query.count()
        print(f"\nBuckets (showing 5 of {bucket_count}):")
        for bucket in buckets:
            print(f"  - ID: {bucket.id}")
            print(f"    Created: {bucket.created}")
            print(f"    Size: {bucket.size} bytes")
            print(f"    Quota size: {bucket.quota_size} bytes")
            print(f"    Location ID: {bucket.location_id}")
            
            # Get objects in this bucket
            objects = ObjectVersion.query.filter_by(bucket_id=bucket.id).limit(5).all()
            obj_count = ObjectVersion.query.filter_by(bucket_id=bucket.id).count()
            if obj_count > 0:
                print(f"    Objects (showing 5 of {obj_count}):")
                for obj in objects:
                    print(f"      - Key: {obj.key}")
                    print(f"        Version ID: {obj.version_id}")
                    print(f"        File ID: {obj.file_id}")
        
        # Check file instances
        file_instances = FileInstance.query.limit(5).all()
        file_count = FileInstance.query.count()
        print(f"\nFile Instances (showing 5 of {file_count}):")
        for fi in file_instances:
            print(f"  - ID: {fi.id}")
            print(f"    URI: {fi.uri}")
            print(f"    Size: {fi.size} bytes")
            print(f"    Checksum: {fi.checksum}")
            print(f"    Storage class: {fi.storage_class}")
            
            # If the URI points to a local file, check if it exists
            if fi.uri.startswith('file://'):
                file_path = fi.uri[7:]  # Remove 'file://' prefix
                if os.path.exists(file_path):
                    print(f"    File exists at: {file_path}")
                    print(f"    File size: {os.path.getsize(file_path)} bytes")
                    print(f"    Last modified: {time.ctime(os.path.getmtime(file_path))}")
                else:
                    print(f"    File does not exist at: {file_path}")
    
        # Get the relationship between records and files
        print("\nRecord-File Relationships:")
        records = RDMRecord.query.limit(5).all()
        for i, record in enumerate(records, 1):
            print(f"  Record {i}:")
            print(f"    ID: {record.id}")
            print(f"    PID: {getattr(record, 'pid', 'N/A')}")
            
            # Get files associated with this record
            try:
                files = record.files
                file_keys = list(files.keys)
                print(f"    Files: {len(file_keys)}")
                for key in file_keys[:5]:  # Limit to 5 files
                    obj = files[key]
                    file_instance = obj.file
                    print(f"      - Key: {key}")
                    print(f"        URI: {file_instance.uri}")
                    print(f"        Size: {file_instance.size} bytes")
                    print(f"        Checksum: {file_instance.checksum}")
                    print(f"        Storage class: {file_instance.storage_class}")
            except Exception as e:
                print(f"    Error getting files: {str(e)}")
    
    except Exception as e:
        print(f"Error querying database: {str(e)}")

def check_physical_file_locations():
    """Check the physical file locations on disk."""
    print("\n=== Physical File Locations ===")
    
    # Define possible locations
    data_locations = []
    
    # If Invenio is available, get instance path from app
    if HAS_INVENIO:
        try:
            with app.app_context():
                instance_path = current_app.instance_path
                data_locations.append(os.path.join(instance_path, 'data'))
                
                # Get location from database
                locations = Location.query.all()
                for loc in locations:
                    if loc.uri.startswith('file://'):
                        data_locations.append(loc.uri[7:])  # Remove 'file://' prefix
        except Exception as e:
            print(f"Error getting locations from app: {str(e)}")
    
    # Add common locations
    project_dir = os.getcwd()
    data_locations.extend([
        os.path.join(project_dir, 'data'),
        os.path.join(project_dir, '.venv', 'var', 'instance', 'data'),
        os.path.join(project_dir, 'var', 'instance', 'data'),
        os.path.join(project_dir, 'instance', 'data'),
    ])
    
    # Check each location
    for location in data_locations:
        if os.path.exists(location):
            print(f"\nExamining location: {location}")
            
            # Get directory size and file count
            total_size = 0
            file_count = 0
            for dirpath, dirnames, filenames in os.walk(location):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
                        file_count += 1
            
            print(f"  Directory size: {total_size / (1024*1024):.2f} MB")
            print(f"  Total files: {file_count}")
            
            # Check for specific directories
            subdirs = ['records', 'files', 'archive', 'default']
            for subdir in subdirs:
                subdir_path = os.path.join(location, subdir)
                if os.path.exists(subdir_path) and os.path.isdir(subdir_path):
                    print(f"\n  Found subdirectory: {subdir}")
                    
                    # List contents (limited to first 5 items)
                    contents = os.listdir(subdir_path)[:5]
                    print(f"    First {len(contents)} items: {contents}")
                    
                    # If it's 'records' directory, check its structure
                    if subdir == 'records':
                        record_dirs = [d for d in os.listdir(subdir_path) 
                                     if os.path.isdir(os.path.join(subdir_path, d))]
                        print(f"    Number of record directories: {len(record_dirs)}")
                        
                        # Check a sample record directory
                        if record_dirs:
                            sample_record = record_dirs[0]
                            sample_path = os.path.join(subdir_path, sample_record)
                            print(f"\n    Sample record directory: {sample_record}")
                            
                            # List files in the record directory
                            if os.path.exists(sample_path):
                                files = os.listdir(sample_path)
                                print(f"      Files: {files}")
                                
                                # Check each file
                                for file in files:
                                    file_path = os.path.join(sample_path, file)
                                    if os.path.isfile(file_path):
                                        print(f"      - {file}: {os.path.getsize(file_path)} bytes")
                                        
                                        # If it's a PDF and Cantaloupe is configured
                                        if file.lower().endswith('.pdf'):
                                            check_cantaloupe_access(sample_record, file)

def check_cantaloupe_access(record_id, filename):
    """Check if Cantaloupe can access the file."""
    print(f"\n  Checking Cantaloupe access for {filename} in record {record_id}...")
    
    try:
        import requests
        
        # Try different URL patterns
        url_patterns = [
            f"http://localhost:8182/iiif/2/records%2F{record_id}%2F{filename}/info.json",
            f"http://localhost:8182/iiif/2/private%2F{record_id}%2F{filename}/info.json",
            f"http://localhost:8182/iiif/2/{record_id}%2F{filename}/info.json"
        ]
        
        for url in url_patterns:
            try:
                response = requests.get(url, timeout=5)
                print(f"    URL: {url}")
                print(f"    Status: {response.status_code}")
                
                if response.status_code == 200:
                    print("    Success! Cantaloupe can access this file.")
                    return
            except requests.RequestException:
                print(f"    Failed to connect to {url}")
        
        print("    Cantaloupe cannot access this file.")
    except ImportError:
        print("    Cannot check Cantaloupe access - requests module not available.")

def examine_upload_flow():
    """Examine the upload flow to understand where files are stored."""
    print("\n=== Upload Flow Analysis ===")
    
    if not HAS_INVENIO:
        print("Cannot analyze upload flow - Invenio modules not available.")
        return
    
    try:
        with app.app_context():
            # Get configuration
            print("\nFile Storage Configuration:")
            print(f"  Instance path: {current_app.instance_path}")
            print(f"  Storage factory: {current_app.config.get('FILES_REST_STORAGE_FACTORY')}")
            print(f"  Storage class mapping: {current_app.config.get('FILES_REST_STORAGE_CLASS_MAPPING')}")
            
            # Check location paths
            locations = Location.query.all()
            print(f"\nDefined storage locations ({len(locations)}):")
            for loc in locations:
                print(f"  - {loc.name}: {loc.uri}")
                
                # Check if this location has a default path
                if loc.default:
                    print(f"    This is the default location.")
                    
                    # Get the URI path
                    if loc.uri.startswith('file://'):
                        path = loc.uri[7:]  # Remove 'file://' prefix
                        
                        # Check how the files are organized
                        if os.path.exists(path):
                            print(f"    Path exists at: {path}")
                            
                            # Check subdirectories
                            subdirs = os.listdir(path)
                            print(f"    Subdirectories: {subdirs}")
                            
                            # Look for UUID-based directories
                            uuid_dirs = []
                            for item in subdirs:
                                try:
                                    uuid_obj = UUID(item)
                                    uuid_dirs.append(item)
                                except ValueError:
                                    pass
                            
                            if uuid_dirs:
                                print(f"    Found {len(uuid_dirs)} UUID-based directories")
                                print(f"    Sample UUID dir: {uuid_dirs[0]}")
                                
                                # Check the structure of a UUID directory
                                sample_dir = os.path.join(path, uuid_dirs[0])
                                if os.path.isdir(sample_dir):
                                    contents = os.listdir(sample_dir)
                                    print(f"    Contents of {uuid_dirs[0]}: {contents}")
    except Exception as e:
        print(f"Error analyzing upload flow: {str(e)}")

def main():
    """Main function."""
    # Load Invenio app context if available
    global app
    app = load_app_context()
    
    # Check database structure
    if HAS_INVENIO and app:
        with app.app_context():
            check_database_file_structure()
    
    # Check physical file locations
    check_physical_file_locations()
    
    # Examine upload flow
    if HAS_INVENIO and app:
        examine_upload_flow()
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main() 
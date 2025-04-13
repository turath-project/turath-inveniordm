#!/usr/bin/env python
"""
Check for files in the virtual environment and database.
This script helps diagnose issues with PDF files in venv and database.
"""

import os
import sys
import json
import glob
import argparse
import subprocess
from pathlib import Path
import shutil
import time

# Add invenio app context
try:
    from flask import current_app
    from invenio_app.factory import create_app
    from invenio_db import db
    from invenio_files_rest.models import ObjectVersion, FileInstance
    from invenio_records_files.api import RecordFiles
    from invenio_records.api import Record
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
    with app.app_context():
        return app

def check_venv_for_files(record_id=None, filename=None):
    """Check for files in the virtual environment."""
    print("\nChecking virtual environment for files...")
    
    # Get virtual environment path
    venv_path = os.environ.get('VIRTUAL_ENV')
    if not venv_path:
        # Try to find pipenv virtual environment
        try:
            result = subprocess.run(['pipenv', '--venv'], 
                                   check=True, 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True)
            venv_path = result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            venv_path = None
    
    if not venv_path:
        print("Virtual environment not found.")
        return
    
    print(f"Virtual environment path: {venv_path}")
    
    # Check for instance directory
    instance_paths = [
        os.path.join(venv_path, 'var', 'instance'),
        os.path.join(venv_path, 'var', 'app', 'instance'),
        os.path.join(venv_path, 'instance'),
        os.path.join(os.path.dirname(venv_path), 'var', 'instance'),
        os.path.join(os.path.dirname(venv_path), 'instance'),
        os.path.join(os.path.dirname(os.path.dirname(venv_path)), 'var', 'instance'),
    ]
    
    instance_dir = None
    for path in instance_paths:
        if os.path.exists(path):
            instance_dir = path
            print(f"Found instance directory: {instance_dir}")
            break
    
    if not instance_dir:
        print("Instance directory not found in virtual environment.")
        return
    
    # Look for data directory
    data_dir = os.path.join(instance_dir, 'data')
    if os.path.exists(data_dir):
        print(f"Found data directory: {data_dir}")
        
        # Check records directory
        records_dir = os.path.join(data_dir, 'records')
        if os.path.exists(records_dir):
            print(f"Found records directory: {records_dir}")
            
            # If a specific record is requested
            if record_id:
                record_dir = os.path.join(records_dir, record_id)
                if os.path.exists(record_dir):
                    print(f"Found directory for record {record_id}: {record_dir}")
                    
                    # List files in record directory
                    files = os.listdir(record_dir)
                    print(f"Files in record directory: {files}")
                    
                    # If a specific filename is requested
                    if filename and filename in files:
                        file_path = os.path.join(record_dir, filename)
                        print(f"Found file: {file_path}")
                        
                        # Get file stats
                        file_stats = os.stat(file_path)
                        print(f"File size: {file_stats.st_size} bytes")
                        print(f"Last modified: {time.ctime(file_stats.st_mtime)}")
                        
                        # Try to copy the file to the Cantaloupe directories
                        copy_to_cantaloupe(record_id, filename, file_path)
                        
                        return file_path
                else:
                    print(f"No directory found for record {record_id}")
            else:
                # List all record directories
                record_dirs = os.listdir(records_dir)
                print(f"Found {len(record_dirs)} record directories")
                
                # If looking for a specific file
                if filename:
                    for record_dir_name in record_dirs:
                        record_dir_path = os.path.join(records_dir, record_dir_name)
                        if os.path.isdir(record_dir_path):
                            files = os.listdir(record_dir_path)
                            if filename in files:
                                file_path = os.path.join(record_dir_path, filename)
                                print(f"Found file in record {record_dir_name}: {file_path}")
                                
                                # Get file stats
                                file_stats = os.stat(file_path)
                                print(f"File size: {file_stats.st_size} bytes")
                                print(f"Last modified: {time.ctime(file_stats.st_mtime)}")
                                
                                # Try to copy the file to the Cantaloupe directories
                                copy_to_cantaloupe(record_dir_name, filename, file_path)
                                
                                return file_path
                
    # If we haven't found the file yet, do a broader search
    print("\nPerforming broader search for PDF files...")
    pdf_pattern = filename if filename else "*.pdf"
    
    # Search in instance directory
    for root, dirs, files in os.walk(instance_dir):
        for file in files:
            if file.endswith('.pdf') and (filename is None or file == filename):
                file_path = os.path.join(root, file)
                print(f"Found PDF file: {file_path}")
                
                # Get file stats
                file_stats = os.stat(file_path)
                print(f"File size: {file_stats.st_size} bytes")
                print(f"Last modified: {time.ctime(file_stats.st_mtime)}")
                
                # If this is the specific file we're looking for, copy it to Cantaloupe
                if filename and file == filename:
                    # Try to determine record ID from path
                    path_parts = file_path.split(os.sep)
                    records_index = -1
                    for i, part in enumerate(path_parts):
                        if part == 'records' and i < len(path_parts) - 1:
                            records_index = i
                            break
                    
                    if records_index >= 0 and records_index < len(path_parts) - 1:
                        record_id_from_path = path_parts[records_index + 1]
                        print(f"Determined record ID from path: {record_id_from_path}")
                        
                        # If record_id wasn't specified or matches the path-derived one
                        if record_id is None or record_id == record_id_from_path:
                            copy_to_cantaloupe(record_id_from_path, filename, file_path)
                    else:
                        # If we can't determine record ID from path, use the provided one
                        if record_id:
                            copy_to_cantaloupe(record_id, filename, file_path)
    
    return None

def check_database_for_files(record_id=None, filename=None):
    """Check the database for file information."""
    if not HAS_INVENIO:
        print("Cannot check database - Invenio modules not available.")
        return
    
    print("\nChecking database for file information...")
    
    try:
        # If a specific record is requested
        if record_id:
            print(f"Looking for record with ID: {record_id}")
            record = Record.get_record(record_id)
            print(f"Found record: {record.id}")
            
            # Check for files associated with this record
            record_files = RecordFiles(record)
            print(f"Files associated with record: {list(record_files.keys())}")
            
            # If a specific filename is requested
            if filename and filename in record_files:
                obj = record_files[filename]
                file_instance = obj.file
                print(f"Found file in database: {filename}")
                print(f"URI: {file_instance.uri}")
                print(f"Size: {file_instance.size} bytes")
                print(f"Checksum: {file_instance.checksum}")
                
                # If the URI points to a file, try to copy it to Cantaloupe
                if file_instance.uri.startswith('file://'):
                    file_path = file_instance.uri[7:]  # Remove 'file://' prefix
                    if os.path.exists(file_path):
                        print(f"File exists at: {file_path}")
                        copy_to_cantaloupe(record_id, filename, file_path)
                    else:
                        print(f"File does not exist at: {file_path}")
                
                return file_instance
        else:
            # If no specific record, search all files
            print("Searching all files in database...")
            query = FileInstance.query
            if filename:
                query = query.filter(FileInstance.uri.contains(filename))
            
            for file_instance in query.limit(10).all():
                print(f"Found file: {file_instance.uri}")
                print(f"Size: {file_instance.size} bytes")
                print(f"Checksum: {file_instance.checksum}")
                
                # If the URI points to a file, try to copy it to Cantaloupe
                if file_instance.uri.startswith('file://'):
                    file_path = file_instance.uri[7:]  # Remove 'file://' prefix
                    if os.path.exists(file_path) and (filename is None or filename in file_path):
                        print(f"File exists at: {file_path}")
                        
                        # Try to determine record ID from the file associations
                        obj_versions = ObjectVersion.query.filter_by(file_id=file_instance.id).all()
                        for obj in obj_versions:
                            print(f"Associated with bucket: {obj.bucket_id}")
                            
                            # We'd need to trace from bucket to record, but this is complex
                            # So we'll just use a dummy record ID if not provided
                            record_id_to_use = record_id or "unknown"
                            copy_to_cantaloupe(record_id_to_use, os.path.basename(file_path), file_path)
                    else:
                        print(f"File does not exist at: {file_path}")
    
    except Exception as e:
        print(f"Error querying database: {str(e)}")
    
    return None

def copy_to_cantaloupe(record_id, filename, file_path):
    """Copy a file to the Cantaloupe directories."""
    print(f"\nCopying file to Cantaloupe for record {record_id}, file {filename}...")
    
    # Check if Docker is available
    try:
        result = subprocess.run(['docker', 'compose', 'ps', '-q', 'cantaloupe'], 
                               check=True, 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        cantaloupe_container = result.stdout.strip()
        
        if not cantaloupe_container:
            print("Cantaloupe container not running.")
            return False
        
        print(f"Found Cantaloupe container: {cantaloupe_container}")
        
        # Create target directories in Cantaloupe
        target_paths = [
            f"/opt/cantaloupe/images/records/{record_id}",
            f"/opt/cantaloupe/images/private/{record_id}"
        ]
        
        for target_dir in target_paths:
            print(f"Creating directory {target_dir} in Cantaloupe container...")
            subprocess.run(['docker', 'exec', cantaloupe_container, 'mkdir', '-p', target_dir], 
                          check=False,  # Don't fail if directory already exists
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
            
            # Copy file to Cantaloupe
            print(f"Copying file to Cantaloupe container at {target_dir}/{filename}...")
            subprocess.run(['docker', 'cp', file_path, f"{cantaloupe_container}:{target_dir}/{filename}"], 
                          check=True, 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
            
            # Set permissions to ensure Cantaloupe can read it
            subprocess.run(['docker', 'exec', cantaloupe_container, 'chmod', '644', f"{target_dir}/{filename}"], 
                          check=True, 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
            
            print(f"Copied file to Cantaloupe at {target_dir}/{filename}")
            
            # Test if Cantaloupe can access the file
            test_url = f"http://localhost:8182/iiif/2/{target_dir.split('/')[-2]}%2F{record_id}%2F{filename}/info.json"
            print(f"Testing Cantaloupe access at: {test_url}")
            
            # Give Cantaloupe a moment to process the file
            time.sleep(2)
            
            try:
                import requests
                response = requests.get(test_url)
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    print("Success! Cantaloupe can access the file.")
                    return True
                else:
                    print(f"Error: {response.text[:200]}...")
            except Exception as e:
                print(f"Error testing Cantaloupe access: {str(e)}")
        
        # If the above URLs didn't work, try a direct URL
        test_url = f"http://localhost:8182/iiif/2/{record_id}%2F{filename}/info.json"
        print(f"Testing direct Cantaloupe access at: {test_url}")
        
        try:
            import requests
            response = requests.get(test_url)
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                print("Success! Cantaloupe can access the file using direct path.")
                return True
            else:
                print(f"Error: {response.text[:200]}...")
        except Exception as e:
            print(f"Error testing Cantaloupe access: {str(e)}")
        
    except subprocess.SubprocessError as e:
        print(f"Error interacting with Docker: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
    
    return False

def check_project_for_files(record_id=None, filename=None):
    """Check for files in the project directories."""
    print("\nChecking project directories for files...")
    
    # Get the project directory (assuming we're in the project root)
    project_dir = os.getcwd()
    print(f"Project directory: {project_dir}")
    
    # Check common locations for files in Invenio projects
    project_data_paths = [
        os.path.join(project_dir, 'data'),
        os.path.join(project_dir, 'data', 'records'),
        os.path.join(project_dir, 'var', 'instance', 'data'),
        os.path.join(project_dir, 'var', 'data'),
        os.path.join(project_dir, 'instance', 'data'),
        os.path.join(project_dir, 'instance'),
    ]
    
    for path in project_data_paths:
        if os.path.exists(path):
            print(f"Found project data directory: {path}")
            
            # If looking for specific record
            if record_id:
                record_dir = os.path.join(path, 'records', record_id)
                if os.path.exists(record_dir):
                    print(f"Found directory for record {record_id}: {record_dir}")
                    
                    # List files in record directory
                    files = os.listdir(record_dir)
                    print(f"Files in record directory: {files}")
                    
                    # If a specific filename is requested
                    if filename and filename in files:
                        file_path = os.path.join(record_dir, filename)
                        print(f"Found file: {file_path}")
                        
                        # Get file stats
                        file_stats = os.stat(file_path)
                        print(f"File size: {file_stats.st_size} bytes")
                        print(f"Last modified: {time.ctime(file_stats.st_mtime)}")
                        
                        # Try to copy the file to the Cantaloupe directories
                        copy_to_cantaloupe(record_id, filename, file_path)
                        
                        return file_path
            
            # Search for PDFs in this directory
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.endswith('.pdf') and (filename is None or file == filename):
                            file_path = os.path.join(root, file)
                            print(f"Found PDF file: {file_path}")
                            
                            # Get file stats
                            file_stats = os.stat(file_path)
                            print(f"File size: {file_stats.st_size} bytes")
                            print(f"Last modified: {time.ctime(file_stats.st_mtime)}")
                            
                            # If this is the specific file we're looking for, copy it to Cantaloupe
                            if filename and file == filename:
                                # Try to determine record ID from path
                                path_parts = file_path.split(os.sep)
                                records_index = -1
                                for i, part in enumerate(path_parts):
                                    if part == 'records' and i < len(path_parts) - 1:
                                        records_index = i
                                        break
                                
                                if records_index >= 0 and records_index < len(path_parts) - 1:
                                    record_id_from_path = path_parts[records_index + 1]
                                    print(f"Determined record ID from path: {record_id_from_path}")
                                    
                                    # If record_id wasn't specified or matches the path-derived one
                                    if record_id is None or record_id == record_id_from_path:
                                        copy_to_cantaloupe(record_id_from_path, filename, file_path)
                                else:
                                    # If we can't determine record ID from path, use the provided one
                                    if record_id:
                                        copy_to_cantaloupe(record_id, filename, file_path)
    
    return None

def create_test_pdf(record_id):
    """Create a test PDF file for the specified record."""
    print(f"\nCreating a test PDF file for record {record_id}...")
    
    # Create a simple test PDF file
    pdf_content = """
%PDF-1.1
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
<< /Type /Page
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
(Zenodo RDM Test PDF File) Tj
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
<< /Root 1 0 R
   /Size 5
>>
startxref
565
%%EOF
"""
    
    # Create directories
    project_dir = os.getcwd()
    data_dir = os.path.join(project_dir, 'data')
    records_dir = os.path.join(data_dir, 'records')
    record_dir = os.path.join(records_dir, record_id)
    
    os.makedirs(record_dir, exist_ok=True)
    
    # Save the PDF file
    test_file = os.path.join(record_dir, "history00871.pdf")
    with open(test_file, "w") as f:
        f.write(pdf_content)
    
    print(f"Created test PDF at {test_file}")
    
    # Also create a version in the private directory
    private_dir = os.path.join(data_dir, 'images', 'private', record_id)
    os.makedirs(private_dir, exist_ok=True)
    
    private_file = os.path.join(private_dir, "history00871.pdf")
    with open(private_file, "w") as f:
        f.write(pdf_content)
    
    print(f"Created test PDF at {private_file}")
    
    # Copy to Cantaloupe
    copy_to_cantaloupe(record_id, "history00871.pdf", test_file)
    
    return test_file

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Check for files in the virtual environment and database")
    parser.add_argument("--record", "-r", help="Record ID to check")
    parser.add_argument("--filename", "-f", help="Filename to look for")
    parser.add_argument("--create-test", "-t", action="store_true", help="Create a test PDF file")
    
    args = parser.parse_args()
    
    # If requested to create a test file
    if args.create_test and args.record:
        create_test_pdf(args.record)
        return
    
    # Load Invenio app context if available
    app = load_app_context()
    
    # Check project directories first
    project_result = check_project_for_files(args.record, args.filename)
    
    # If file not found in project directories, check virtual environment
    if not project_result:
        venv_result = check_venv_for_files(args.record, args.filename)
        
        # If file not found in venv and Invenio is available, check database
        if not venv_result and HAS_INVENIO and app:
            with app.app_context():
                db_result = check_database_for_files(args.record, args.filename)
                
    # If file not found anywhere and we have a record ID, offer to create a test file
    if args.record and not args.create_test:
        print("\nNo PDF file found. Would you like to create a test PDF file? (y/n)")
        response = input().strip().lower()
        if response == 'y':
            create_test_pdf(args.record)

if __name__ == "__main__":
    main() 
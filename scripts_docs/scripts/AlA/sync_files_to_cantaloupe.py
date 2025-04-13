#!/usr/bin/env python
"""
Synchronize Invenio PDF files to Cantaloupe.

This script:
1. Finds all records with PDF files
2. Copies those files to the Cantaloupe directory structure
3. Creates the necessary directories if they don't exist

Usage:
    pipenv run invenio shell -c "exec(open('scripts/AlA/sync_files_to_cantaloupe.py').read())"

Options:
    --record-id=RECORD_ID  Sync only a specific record (default: sync all)
    --cantaloupe-dir=DIR   Cantaloupe data directory (default: /opt/cantaloupe/images)
"""

import os
import sys
import shutil
import logging
from flask import current_app
from invenio_db import db
from invenio_files_rest.models import ObjectVersion, FileInstance
from invenio_records_files.api import Record
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_records.models import RecordMetadata

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("sync-cantaloupe")

# Parse command line arguments
record_id = None
cantaloupe_dir = "/opt/cantaloupe/images"

for arg in sys.argv:
    if arg.startswith('--record-id='):
        record_id = arg.split('=', 1)[1]
    elif arg.startswith('--cantaloupe-dir='):
        cantaloupe_dir = arg.split('=', 1)[1]

def get_all_records_with_pdf_files():
    """Get all records that have PDF files."""
    logger.info("Searching for records with PDF files...")
    
    # Query for all published records
    records = []
    
    # If record_id is specified, only sync that record
    if record_id:
        try:
            pid = PersistentIdentifier.get('recid', record_id)
            if pid.status == PIDStatus.REGISTERED:
                rec = RecordMetadata.query.get(pid.object_uuid)
                if rec:
                    records.append((record_id, rec))
                    logger.info(f"Found record {record_id}")
        except Exception as e:
            logger.error(f"Error finding record {record_id}: {e}")
    else:
        # Get all published records
        pids = PersistentIdentifier.query.filter_by(
            pid_type='recid', status=PIDStatus.REGISTERED).all()
        
        for pid in pids:
            rec = RecordMetadata.query.get(pid.object_uuid)
            if rec:
                records.append((pid.pid_value, rec))
    
    logger.info(f"Found {len(records)} records to check")
    
    # Filter for records with PDF files
    records_with_pdfs = []
    
    for pid_value, rec in records:
        try:
            record_json = rec.json
            
            # Check if the record has files
            files = []
            
            # Check in different possible file locations
            if 'files' in record_json and 'entries' in record_json['files']:
                files = record_json['files']['entries']
            elif '_files' in record_json:
                files = [{'key': key} for key in record_json['_files']]
            
            # Find PDF files
            pdf_files = [f for f in files if f.get('key', '').lower().endswith('.pdf')]
            
            if pdf_files:
                records_with_pdfs.append((pid_value, rec, pdf_files))
                logger.info(f"Record {pid_value} has {len(pdf_files)} PDF file(s)")
        except Exception as e:
            logger.error(f"Error checking record {pid_value}: {e}")
    
    logger.info(f"Found {len(records_with_pdfs)} records with PDF files")
    return records_with_pdfs

def get_file_path(record_id, file_key):
    """Get the physical file path for a record file."""
    try:
        # Find the bucket ID for the record
        rec = Record.get_record(PersistentIdentifier.get('recid', record_id).object_uuid)
        
        # Get the bucket ID
        bucket_id = None
        if hasattr(rec, 'files') and hasattr(rec.files, 'bucket'):
            bucket_id = str(rec.files.bucket.id)
        elif 'files' in rec and 'bucket_id' in rec['files']:
            bucket_id = rec['files']['bucket_id']
        
        if not bucket_id:
            logger.error(f"Could not find bucket ID for record {record_id}")
            return None
        
        # Get the file from the bucket
        obj = ObjectVersion.get(bucket_id, file_key)
        if not obj:
            logger.error(f"Could not find file {file_key} in bucket {bucket_id}")
            return None
        
        # Get the file instance and URI
        file_instance = obj.file
        if not file_instance:
            logger.error(f"Could not find file instance for {file_key}")
            return None
        
        # Get the file path
        return file_instance.uri
    except Exception as e:
        logger.error(f"Error getting file path for {record_id}/{file_key}: {e}")
        return None

def copy_file_to_cantaloupe(record_id, file_key, file_path):
    """Copy a file to the Cantaloupe directory structure."""
    try:
        # Create the destination path - use the path expected by Cantaloupe
        # Typically in Cantaloupe, it follows a structure like: 
        # {data_dir}/private/{record_id}/{filename}
        dest_dir = os.path.join(cantaloupe_dir, "private", record_id)
        dest_path = os.path.join(dest_dir, file_key)
        
        # Create the directory if it doesn't exist
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
            logger.info(f"Created directory: {dest_dir}")
        
        # Copy the file
        shutil.copy2(file_path, dest_path)
        logger.info(f"Copied {file_path} to {dest_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error copying file to Cantaloupe: {e}")
        return False

def main():
    """Main function."""
    logger.info("=== Syncing Files to Cantaloupe ===")
    
    # Check if the Cantaloupe directory exists
    if not os.path.exists(cantaloupe_dir):
        try:
            os.makedirs(cantaloupe_dir, exist_ok=True)
            logger.info(f"Created Cantaloupe directory: {cantaloupe_dir}")
        except Exception as e:
            logger.error(f"Error creating Cantaloupe directory: {e}")
            logger.error("Please make sure the Cantaloupe directory exists and is writable")
            return False
    
    # Get all records with PDF files
    records_with_pdfs = get_all_records_with_pdf_files()
    
    # Copy files to Cantaloupe
    success_count = 0
    failed_count = 0
    
    for record_id, record, pdf_files in records_with_pdfs:
        for pdf_file in pdf_files:
            file_key = pdf_file['key']
            logger.info(f"Processing {record_id}/{file_key}")
            
            # Get the file path
            file_path = get_file_path(record_id, file_key)
            if not file_path:
                logger.error(f"Could not get file path for {record_id}/{file_key}")
                failed_count += 1
                continue
            
            # Copy the file to Cantaloupe
            if copy_file_to_cantaloupe(record_id, file_key, file_path):
                success_count += 1
            else:
                failed_count += 1
    
    logger.info("=== Sync Complete ===")
    logger.info(f"Successfully copied {success_count} files to Cantaloupe")
    if failed_count > 0:
        logger.warning(f"Failed to copy {failed_count} files")
    
    return True

if __name__ == "__main__":
    main()
else:
    # Running in Invenio shell
    main() 
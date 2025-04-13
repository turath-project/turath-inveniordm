#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Direct CLI Import Script for Turath InvenioRDM.

This script creates records directly using the Flask CLI within the application context
and uploads files to the record in batches to stay under file limits.
"""

import os
import sys
import json
import tempfile
import datetime
import shutil
import argparse
import glob
from pathlib import Path
import time
import traceback

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from flask import current_app 
from invenio_db import db
from invenio_rdm_records.services.services import RDMRecordService
from invenio_access.permissions import system_identity
from invenio_rdm_records.proxies import current_rdm_records_service
from flask_principal import g
from flask_login import current_user

def extract_book_info(book_dir):
    """Extract book information from the directory name and manifest."""
    from pathlib import Path
    
    book_path = Path(book_dir)
    book_name = book_path.name
    
    # Try to get info from manifest
    manifest_path = book_path / "manifest.json"
    
    if manifest_path.exists():
        with open(manifest_path, 'r') as f:
            try:
                manifest = json.load(f)
                title = manifest.get("label", book_name)
            except json.JSONDecodeError:
                title = book_name
    else:
        title = book_name
    
    # Create a book info dictionary
    book_info = {
        "title": title,
        "book_id": book_name.lower().replace(" ", "-"),
        "author": "Unknown Author",  # Default author
    }
    
    return book_info

def fix_creators_metadata(metadata):
    """Ensure creators metadata is in the correct format."""
    if "metadata" not in metadata:
        return metadata
    
    if "creators" not in metadata["metadata"]:
        # Add default creator if missing
        metadata["metadata"]["creators"] = [
            {
                "person_or_org": {
                    "family_name": "Author",
                    "given_name": "Unknown",
                    "type": "personal"
                }
            }
        ]
    else:
        # Fix each creator
        for i, creator in enumerate(metadata["metadata"]["creators"]):
            if "person_or_org" not in creator:
                metadata["metadata"]["creators"][i] = {
                    "person_or_org": {
                        "family_name": "Author",
                        "given_name": "Unknown",
                        "type": "personal"
                    }
                }
            else:
                person_or_org = creator["person_or_org"]
                # Check if name is used instead of family_name/given_name
                if "name" in person_or_org and "family_name" not in person_or_org:
                    name = person_or_org["name"]
                    if " " in name:
                        given_name, family_name = name.rsplit(" ", 1)
                    else:
                        given_name = name
                        family_name = "Author"
                    
                    # Update the person_or_org
                    person_or_org["family_name"] = family_name
                    person_or_org["given_name"] = given_name
                    person_or_org["type"] = "personal"
                    # Remove the name field
                    person_or_org.pop("name", None)
                
                # Ensure family_name is not blank
                if "family_name" not in person_or_org or not person_or_org["family_name"]:
                    person_or_org["family_name"] = "Author"
                
                # Ensure given_name is not blank
                if "given_name" not in person_or_org or not person_or_org["given_name"]:
                    person_or_org["given_name"] = "Unknown"
                
                # Ensure type is set
                if "type" not in person_or_org:
                    person_or_org["type"] = "personal"
    
    return metadata

def prepare_metadata(book_info, manifest_url=None):
    """Prepare metadata for the record."""
    metadata = {
        "access": {
            "record": "public",
            "files": "public"
        },
        "files": {
            "enabled": True
        },
        "metadata": {
            "title": book_info["title"],
            "publication_date": book_info.get("publication_date", datetime.date.today().strftime("%Y-%m-%d")),
            "resource_type": {"id": "publication-book"},
            "creators": [
                {
                    "person_or_org": {
                        "family_name": "Author",
                        "given_name": "Unknown",
                        "type": "personal"
                    }
                }
            ],
            "description": book_info.get("description", "Book imported with IIIF support")
        }
    }
    
    # Add IIIF manifest URL to custom fields if available
    if manifest_url:
        metadata["custom_fields"] = {"turath:iiif_manifest": manifest_url}
    
    return metadata

def copy_to_storage(book_dir, storage_path, book_id):
    """Copy book files to permanent storage location."""
    # Create target directory
    target_dir = os.path.join(storage_path, book_id)
    os.makedirs(target_dir, exist_ok=True)
    
    # Copy manifest file
    manifest_path = os.path.join(book_dir, "manifest.json")
    if os.path.exists(manifest_path):
        shutil.copy2(manifest_path, os.path.join(target_dir, "manifest.json"))
    
    # Copy pages directory
    source_pages = os.path.join(book_dir, "pages")
    target_pages = os.path.join(target_dir, "pages")
    if os.path.exists(source_pages):
        os.makedirs(target_pages, exist_ok=True)
        for file in os.listdir(source_pages):
            source_file = os.path.join(source_pages, file)
            if os.path.isfile(source_file):
                shutil.copy2(source_file, os.path.join(target_pages, file))
    
    # Copy HOCR directory if it exists
    source_hocr = os.path.join(book_dir, "hocr")
    target_hocr = os.path.join(target_dir, "hocr")
    if os.path.exists(source_hocr):
        os.makedirs(target_hocr, exist_ok=True)
        for file in os.listdir(source_hocr):
            source_file = os.path.join(source_hocr, file)
            if os.path.isfile(source_file):
                shutil.copy2(source_file, os.path.join(target_hocr, file))
    
    return target_dir

def collect_files_to_upload(book_dir, skip_hocr=False):
    """Collect files from the book directory that should be uploaded to InvenioRDM."""
    files_to_upload = []
    
    # Add manifest
    manifest_path = os.path.join(book_dir, "manifest.json")
    if os.path.exists(manifest_path):
        files_to_upload.append(manifest_path)
    
    # Add pages directory contents
    pages_dir = os.path.join(book_dir, "pages")
    if os.path.exists(pages_dir) and os.path.isdir(pages_dir):
        for file_name in os.listdir(pages_dir):
            file_path = os.path.join(pages_dir, file_name)
            if os.path.isfile(file_path):
                files_to_upload.append(file_path)
    
    # Add HOCR files if they exist and not skipped
    if not skip_hocr:
        hocr_dir = os.path.join(book_dir, "hocr")
        if os.path.exists(hocr_dir) and os.path.isdir(hocr_dir):
            for file_name in os.listdir(hocr_dir):
                file_path = os.path.join(hocr_dir, file_name)
                if os.path.isfile(file_path):
                    files_to_upload.append(file_path)
    
    return files_to_upload

def upload_files_to_record(record_id, book_dir, skip_files=False, skip_hocr=False):
    """Upload files to the record using direct service calls."""
    if skip_files:
        print("Skipping file uploads as requested")
        return True
    
    # Get all files from the book directory
    files_to_upload = collect_files_to_upload(book_dir, skip_hocr)
    print(f"Found {len(files_to_upload)} files to upload")
    
    if not files_to_upload:
        print("No files to upload")
        return True
    
    # Get system identity
    identity = system_identity
    
    # Get service
    current_rdm_records_service = current_app.extensions["invenio-rdm-records"].records_service
    
    try:
        # Initialize all files at once
        print(f"Initializing {len(files_to_upload)} files...")
        file_keys = [{"key": os.path.basename(path)} for path in files_to_upload]
        current_rdm_records_service.draft_files.init_files(
            id_=record_id,
            data=file_keys,
            identity=identity
        )
        
        # Upload each file
        for i, file_path in enumerate(files_to_upload, 1):
            file_name = os.path.basename(file_path)
            print(f"Uploading file: {file_name}")
            
            with open(file_path, "rb") as file_content:
                current_rdm_records_service.draft_files.set_file_content(
                    id_=record_id,
                    file_key=file_name,
                    stream=file_content,
                    identity=identity
                )
            
            # Commit the file
            current_rdm_records_service.draft_files.commit_file(
                id_=record_id,
                file_key=file_name,
                identity=identity
            )
            
            print(f"Successfully uploaded {i}/{len(files_to_upload)}: {file_name}")
        
        # Publish the record
        current_rdm_records_service.publish(id_=record_id, identity=identity)
        print(f"Published record successfully with {len(files_to_upload)} files")
        return True
            
    except Exception as e:
        print(f"Error uploading files: {str(e)}")
        traceback.print_exc()
        return False

def import_book(book_dir, storage_path=None, server_url=None, dry_run=False, skip_files=False, skip_hocr=False):
    """Import a book directly using the Flask CLI."""
    from flask import current_app
    
    # Default values if not provided
    if storage_path is None:
        storage_path = os.path.join(os.getcwd(), "var", "iiif-storage")
    
    if server_url is None:
        server_url = "http://localhost:8182/iiif/3"
    
    # Extract book information
    book_info = extract_book_info(book_dir)
    print("Book information:")
    for key, value in book_info.items():
        print(f"  {key}: {value}")
    
    # Copy files to storage if needed
    storage_dir = os.path.join(storage_path, book_info["book_id"])
    print("Copying files to storage...")
    
    if book_dir == storage_dir:
        print(f"Files are already in the storage location: {storage_dir}")
    else:
        copy_to_storage(book_dir, storage_path, book_info["book_id"])
    
    print(f"Files copied to {storage_dir}")
    
    # Generate manifest URL for the book
    manifest_url = f"{server_url}/{book_info['book_id']}/manifest.json"
    
    if dry_run:
        print(f"Would create record with IIIF manifest URL: {manifest_url}")
        print(f"Would upload files from: {storage_dir}")
        return {"success": True, "dry_run": True}
    
    # Create record in InvenioRDM
    print("Creating record in InvenioRDM...")
    metadata = prepare_metadata(book_info, manifest_url)
    
    # Use the InvenioRDM service directly
    try:
        # First check if we're already in an application context
        try:
            app_name = current_app.name
            in_app_context = True
        except RuntimeError:
            in_app_context = False
        
        if not in_app_context:
            # We need to create an app context
            from invenio_app.factory import create_app
            app = create_app()
            with app.app_context():
                print("Creating record within Flask application context...")
                record = current_rdm_records_service.create(system_identity, metadata)
                record_id = record.id
                print(f"Created record with ID: {record_id}")
                
                # Upload files
                print(f"Uploading files to record {record_id}...")
                upload_success = upload_files_to_record(record_id, storage_dir, skip_files, skip_hocr)
                
                if upload_success:
                    return {"success": True, "record_id": record_id}
                else:
                    return {"success": True, "record_id": record_id, "warning": "Failed to upload some files"}
        else:
            # Already in an app context
            print("Creating record (already in Flask application context)...")
            record = current_rdm_records_service.create(system_identity, metadata)
            record_id = record.id
            print(f"Created record with ID: {record_id}")
            
            # Upload files
            print(f"Uploading files to record {record_id}...")
            upload_success = upload_files_to_record(record_id, storage_dir, skip_files, skip_hocr)
            
            if upload_success:
                return {"success": True, "record_id": record_id}
            else:
                return {"success": True, "record_id": record_id, "warning": "Failed to upload some files"}
    
    except Exception as e:
        print(f"Error creating record: {e}")
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Import a book directly using the Flask CLI")
    parser.add_argument("book_dir", help="Directory containing book files")
    parser.add_argument("--storage-path", help="Path to storage directory")
    parser.add_argument("--server-url", help="URL of the IIIF server")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Don't actually create the record")
    parser.add_argument("--skip-files", "-s", action="store_true", help="Skip uploading files")
    parser.add_argument("--skip-hocr", action="store_true", help="Skip uploading HOCR files")
    parser.add_argument("--batch-size", "-b", type=int, default=90, help="Batch size for file uploads (default: 90)")
    
    args = parser.parse_args()
    
    # Need to load Flask app
    from invenio_app.factory import create_app
    app = create_app()
    
    with app.app_context():
        result = import_book(
            args.book_dir, 
            storage_path=args.storage_path, 
            server_url=args.server_url, 
            dry_run=args.dry_run,
            skip_files=args.skip_files,
            skip_hocr=args.skip_hocr
        )
        
        if result["success"]:
            if args.dry_run:
                print("Dry run completed successfully.")
            elif "warning" in result:
                print(f"Book imported successfully with record ID: {result.get('record_id')}")
                print(f"Warning: {result.get('warning')}")
                sys.exit(1)
            else:
                print(f"Book imported successfully with record ID: {result.get('record_id')}")
            sys.exit(0)
        else:
            print(f"Failed to import book: {result.get('error')}")
            sys.exit(1)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Script to fix the symlink for PDF files in record 202.
"""
import os
import sys
import shutil

try:
    from flask import current_app
    from invenio_app.factory import create_app
    from invenio_db import db
    from invenio_files_rest.models import ObjectVersion, FileInstance, Bucket
    from invenio_pidstore.models import PersistentIdentifier
    from invenio_records_files.api import RecordsBuckets
except ImportError:
    print("Error: This script requires the Invenio modules.")
    sys.exit(1)

def fix_pdf_symlink():
    """Fix the symlink for the PDF file in record 202."""
    print("\n=== Fixing PDF symlink for record 202 ===\n")
    
    # Get record 202 PID
    pid = PersistentIdentifier.query.filter_by(
        pid_type='recid',
        pid_value='202'
    ).first()
    
    if not pid:
        print("Record 202 not found in PersistentIdentifier table!")
        return False
    
    print(f"Found record 202 with UUID: {pid.object_uuid}")
    
    # Find PDF file 'history00871.pdf'
    pdf_object = ObjectVersion.query.filter(
        ObjectVersion.key == 'history00871.pdf'
    ).first()
    
    if not pdf_object:
        print("PDF file 'history00871.pdf' not found in ObjectVersion table!")
        return False
    
    print(f"Found PDF object with key 'history00871.pdf':")
    print(f"  Bucket ID: {pdf_object.bucket_id}")
    
    # Get physical file path
    file_instance = FileInstance.query.filter_by(id=pdf_object.file_id).first()
    if not file_instance:
        print("File instance not found!")
        return False
    
    if file_instance.uri.startswith('file://'):
        physical_file_path = file_instance.uri[7:]  # Remove 'file://' prefix
    else:
        physical_file_path = file_instance.uri
    
    print(f"Physical file path: {physical_file_path}")
    
    if not os.path.exists(physical_file_path):
        print(f"Physical file does not exist at: {physical_file_path}")
        return False
    
    print(f"✅ Physical file exists at: {physical_file_path}")
    
    # Create 'data/records/202' directory if it doesn't exist
    instance_path = current_app.instance_path
    record_dir_path = os.path.join(instance_path, "data", "records", "202")
    
    if not os.path.exists(record_dir_path):
        print(f"Creating directory: {record_dir_path}")
        os.makedirs(record_dir_path, exist_ok=True)
    
    # Create symlink to the physical file
    symlink_path = os.path.join(record_dir_path, "history00871.pdf")
    
    # Remove existing symlink if it exists
    if os.path.exists(symlink_path):
        print(f"Removing existing symlink: {symlink_path}")
        os.remove(symlink_path)
    
    # Create the symlink
    print(f"Creating symlink: {symlink_path} -> {physical_file_path}")
    os.symlink(physical_file_path, symlink_path)
    
    # Verify the symlink was created
    if os.path.exists(symlink_path) and os.path.islink(symlink_path):
        link_target = os.readlink(symlink_path)
        print(f"✅ Symlink created: {symlink_path} -> {link_target}")
    else:
        print(f"❌ Failed to create symlink: {symlink_path}")
        return False
    
    # Now fix the association between the bucket and record 202
    try:
        # Check if there's already an association
        existing_rb = RecordsBuckets.query.filter_by(record_id=pid.object_uuid).first()
        
        if existing_rb:
            print(f"Record 202 is already associated with bucket: {existing_rb.bucket_id}")
            
            if existing_rb.bucket_id != pdf_object.bucket_id:
                print(f"⚠️ Record 202 is associated with a different bucket than the PDF file!")
                print(f"  Record 202 bucket: {existing_rb.bucket_id}")
                print(f"  PDF file bucket: {pdf_object.bucket_id}")
        else:
            # Create the association
            print(f"Creating association between record 202 and bucket: {pdf_object.bucket_id}")
            
            new_rb = RecordsBuckets(
                record_id=pid.object_uuid,
                bucket_id=pdf_object.bucket_id
            )
            
            db.session.add(new_rb)
            db.session.commit()
            
            print(f"✅ Created association between record 202 and bucket: {pdf_object.bucket_id}")
    except Exception as e:
        print(f"❌ Error fixing record-bucket association: {e}")
        return False
    
    print("\n✅ Successfully fixed symlink and associations for record 202 PDF file.")
    return True

def main():
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            success = fix_pdf_symlink()
            if success:
                print("\nPDF symlink fixed successfully!")
                print("\nYou should now be able to access the PDF through the Cantaloupe server.")
                print("Check the IIIF manifest generation for record 202.")
            else:
                print("\nFailed to fix PDF symlink.")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main() 
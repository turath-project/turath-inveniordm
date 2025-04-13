#!/usr/bin/env python3
"""
Script to list RDM records in the database.
"""
import os
import sys
import json
from datetime import datetime, timedelta

try:
    from flask import current_app
    from invenio_app.factory import create_app
    from invenio_db import db
    from invenio_pidstore.models import PersistentIdentifier
    from invenio_records.models import RecordMetadata
    from invenio_rdm_records.records.api import RDMRecord
    from sqlalchemy import desc
except ImportError:
    print("Error: This script requires the Invenio modules.")
    sys.exit(1)

def list_rdm_records(limit=20):
    """List RDM records in the database."""
    print(f"\n=== {limit} RDM Records ===\n")
    
    records = []
    with db.session.no_autoflush:
        try:
            # Get RDM records using the RDM API
            records = RDMRecord.model_cls.query.order_by(
                desc(RDMRecord.model_cls.updated)
            ).limit(limit).all()
        except Exception as e:
            print(f"Error using RDMRecord model: {e}")
            # Fallback to PID search
            pids = PersistentIdentifier.query.filter_by(
                pid_type='recid'
            ).order_by(desc(PersistentIdentifier.updated)).limit(limit).all()
            
            for pid in pids:
                try:
                    if pid.object_type == 'rec' and pid.object_uuid:
                        record = RecordMetadata.query.filter_by(id=pid.object_uuid).first()
                        if record:
                            records.append(record)
                except Exception as inner_e:
                    print(f"Error processing PID {pid.pid_value}: {inner_e}")
    
    print(f"Found {len(records)} records:")
    
    for i, record in enumerate(records, 1):
        try:
            print(f"\n{i}. Record ID: {record.id}")
            
            # Try to get the recid
            pid = PersistentIdentifier.query.filter_by(
                object_type='rec',
                object_uuid=record.id
            ).first()
            
            if pid:
                print(f"   PID: {pid.pid_type}:{pid.pid_value}")
            else:
                print("   No PID found")
            
            # Get JSON
            record_json = record.json
            print(f"   Title: {record_json.get('metadata', {}).get('title', 'No title')}")
            
            # Check for files
            files_data = None
            if 'files' in record_json:
                if isinstance(record_json['files'], dict):
                    files_data = record_json['files']
                    if 'bucket' in files_data:
                        print(f"   Bucket ID: {files_data['bucket']}")
                    if 'entries' in files_data:
                        entries = files_data['entries']
                        print(f"   Files: {len(entries)}")
                        for key, file_info in entries.items():
                            print(f"     - {key} ({file_info.get('size', 'unknown')} bytes)")
                            print(f"       Type: {file_info.get('mimetype', 'unknown')}")
                elif isinstance(record_json['files'], list):
                    files = record_json['files']
                    print(f"   Files: {len(files)}")
                    for file_info in files:
                        if isinstance(file_info, dict):
                            key = file_info.get('key', 'unknown')
                            size = file_info.get('size', 'unknown')
                            mimetype = file_info.get('mimetype', 'unknown')
                            print(f"     - {key} ({size} bytes) [{mimetype}]")
        except Exception as e:
            print(f"Error processing record {i}: {e}")

def find_records_with_pdfs():
    """Find records that have PDF files."""
    print("\n=== Records with PDF Files ===\n")
    
    pdf_records = []
    
    try:
        # Get all records
        records = db.session.query(RecordMetadata).all()
        
        for record in records:
            try:
                record_json = record.json
                has_pdf = False
                
                # Check if record has files
                if 'files' in record_json:
                    if isinstance(record_json['files'], dict) and 'entries' in record_json['files']:
                        # Look for PDF files in entries
                        for key, file_info in record_json['files']['entries'].items():
                            if (key.lower().endswith('.pdf') or 
                                file_info.get('mimetype') == 'application/pdf'):
                                has_pdf = True
                                break
                    elif isinstance(record_json['files'], list):
                        # Look for PDF files in list
                        for file_info in record_json['files']:
                            if isinstance(file_info, dict):
                                key = file_info.get('key', '')
                                mimetype = file_info.get('mimetype', '')
                                if (key.lower().endswith('.pdf') or mimetype == 'application/pdf'):
                                    has_pdf = True
                                    break
                
                if has_pdf:
                    # Get the recid
                    pid = PersistentIdentifier.query.filter_by(
                        object_type='rec',
                        object_uuid=record.id
                    ).first()
                    
                    if pid:
                        pdf_records.append({
                            'id': record.id,
                            'recid': pid.pid_value,
                            'record': record
                        })
            except Exception as e:
                print(f"Error processing record {record.id}: {e}")
        
        print(f"Found {len(pdf_records)} records with PDF files:")
        
        for i, record_info in enumerate(pdf_records, 1):
            try:
                record = record_info['record']
                record_json = record.json
                title = record_json.get('metadata', {}).get('title', 'No title')
                
                print(f"\n{i}. Record ID: {record_info['id']}")
                print(f"   PID: recid:{record_info['recid']}")
                print(f"   Title: {title}")
                
                # List PDF files
                if 'files' in record_json:
                    if isinstance(record_json['files'], dict) and 'entries' in record_json['files']:
                        print("   PDF files:")
                        for key, file_info in record_json['files']['entries'].items():
                            if (key.lower().endswith('.pdf') or 
                                file_info.get('mimetype') == 'application/pdf'):
                                print(f"     - {key} ({file_info.get('size', 'unknown')} bytes)")
                    elif isinstance(record_json['files'], list):
                        print("   PDF files:")
                        for file_info in record_json['files']:
                            if isinstance(file_info, dict):
                                key = file_info.get('key', '')
                                mimetype = file_info.get('mimetype', '')
                                if (key.lower().endswith('.pdf') or mimetype == 'application/pdf'):
                                    print(f"     - {key} ({file_info.get('size', 'unknown')} bytes)")
            except Exception as e:
                print(f"Error displaying record {i}: {e}")
                
    except Exception as e:
        print(f"Error searching for PDF records: {e}")

def main():
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            list_rdm_records(limit=20)
            find_records_with_pdfs()
        except Exception as e:
            print(f"Error in main function: {e}")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python
# This script is meant to be run from the Invenio shell
# Usage:
#   cd /path/to/zenodo-rdm
#   pipenv run invenio shell scripts/AlA/list_records.py [limit]

import sys
from flask import current_app
from invenio_db import db
from invenio_records.api import Record

def list_records(limit=10):
    """List available records in the database."""
    print(f"Listing up to {limit} records:")
    print("-" * 80)
    
    # Try different methods to get records
    try:
        # Method 1: Using SQLAlchemy ORM
        from invenio_records.models import RecordMetadata
        records = RecordMetadata.query.limit(limit).all()
        
        if records:
            print(f"Found {len(records)} records via RecordMetadata model:")
            for i, rec in enumerate(records, 1):
                try:
                    title = rec.json.get('title', 'No title') if rec.json else 'No JSON'
                    recid = rec.json.get('recid', 'No recid') if rec.json else 'No JSON'
                    print(f"{i}. ID: {rec.id} - recid: {recid} - Title: {title}")
                except Exception as e:
                    print(f"{i}. ID: {rec.id} - Error: {e}")
            print()
        else:
            print("No records found via RecordMetadata model.")
            print()
    except Exception as e:
        print(f"Error listing records via RecordMetadata: {e}")
        print()
    
    try:
        # Method 2: Using direct SQL query
        print("Querying records via direct SQL:")
        result = db.session.execute("SELECT id, json->>'recid' as recid, json->>'title' as title FROM records_metadata LIMIT :limit", 
                                   {'limit': limit}).fetchall()
        
        if result:
            print(f"Found {len(result)} records via SQL query:")
            for i, row in enumerate(result, 1):
                print(f"{i}. ID: {row[0]} - recid: {row[1]} - Title: {row[2]}")
            print()
        else:
            print("No records found via SQL query.")
            print()
    except Exception as e:
        print(f"Error querying records via SQL: {e}")
        print()
    
    try:
        # Method 3: Check for RDM records specifically
        try:
            from invenio_rdm_records.records.api import RDMRecord
            from invenio_rdm_records.proxies import current_rdm_records
            
            print("Querying RDM records:")
            # Use the RDM records service to search for records
            search_result = current_rdm_records.records_service.search(
                identity=None,  # system identity
                params={"size": limit}
            )
            
            if search_result.total > 0:
                print(f"Found {search_result.total} RDM records:")
                for i, hit in enumerate(search_result.hits, 1):
                    print(f"{i}. ID: {hit.get('id')} - Title: {hit.get('metadata', {}).get('title')}")
                print()
            else:
                print("No RDM records found.")
                print()
        except ImportError:
            print("RDMRecord module not available.")
            print()
        except Exception as e:
            print(f"Error querying RDM records: {e}")
            print()
    except Exception as e:
        print(f"Error in RDM records section: {e}")
        print()
    
    # Method 4: Check PIDs
    try:
        from invenio_pidstore.models import PersistentIdentifier
        print("Querying persistent identifiers (PIDs):")
        pids = PersistentIdentifier.query.filter_by(pid_type='recid').limit(limit).all()
        
        if pids:
            print(f"Found {len(pids)} record PIDs:")
            for i, pid in enumerate(pids, 1):
                print(f"{i}. PID: {pid.pid_value} - Object UUID: {pid.object_uuid} - Status: {pid.status}")
            print()
        else:
            print("No record PIDs found.")
            print()
    except ImportError:
        print("PersistentIdentifier module not available.")
        print()
    except Exception as e:
        print(f"Error querying PIDs: {e}")
        print()
    
    print("-" * 80)
    print("Recommendation: Use one of the listed record IDs for testing.")
    print("Usage: pipenv run invenio shell scripts/AlA/run_pdf_iiif.py <record-id> sample.pdf")
    print("-" * 80)

def main():
    # Get limit from command line arguments
    limit = 10
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"Invalid limit: {sys.argv[1]}, using default (10)")
    
    list_records(limit)

if __name__ == "__main__":
    main() 
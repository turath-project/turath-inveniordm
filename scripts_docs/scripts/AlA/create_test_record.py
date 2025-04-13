#!/usr/bin/env python
# This script is meant to be run from the Invenio shell
# Usage:
#   cd /path/to/zenodo-rdm
#   pipenv run invenio shell scripts/AlA/create_test_record.py

import sys
import uuid
import json
import datetime
from flask import current_app
from invenio_db import db

def create_test_record():
    """Create a test record in the database."""
    print("Creating a test record...")
    
    # Try different approaches to create a record
    
    # Approach 1: Using Record API
    try:
        from invenio_records.api import Record
        
        # Create a minimal record
        record_id = str(uuid.uuid4())
        data = {
            "title": "Test Record for IIIF PDF",
            "description": "This is a test record created for testing IIIF PDF manifest generation",
            "publication_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "creators": [
                {
                    "name": "Test User",
                    "affiliation": "Test Organization"
                }
            ],
            "access": {
                "record": "public",
                "files": "public"
            }
        }
        
        # Create the record
        print(f"Creating record with ID: {record_id}")
        record = Record.create(data, id_=record_id)
        db.session.commit()
        print(f"Created record: {record.id}")
        
        # Try to create a bucket for files
        try:
            from invenio_files_rest.models import Bucket
            bucket = Bucket.create()
            record['bucket'] = str(bucket.id)
            record.commit()
            db.session.commit()
            print(f"Added bucket {bucket.id} to record")
        except ImportError:
            print("Could not import Bucket class. Skipping bucket creation.")
        except Exception as e:
            print(f"Error creating bucket: {e}")
        
        # Create a PID for the record
        try:
            from invenio_pidstore.models import PersistentIdentifier, PIDStatus
            
            # Generate a new recid
            from sqlalchemy import func
            max_recid = db.session.query(func.max(
                PersistentIdentifier.pid_value.cast(db.Integer)
            )).filter_by(pid_type='recid').scalar()
            
            next_recid = str((max_recid or 0) + 1)
            print(f"Creating PID with recid: {next_recid}")
            
            pid = PersistentIdentifier.create(
                'recid',
                next_recid,
                object_type='rec',
                object_uuid=record.id,
                status=PIDStatus.REGISTERED
            )
            db.session.commit()
            print(f"Created PID: {pid.pid_type}:{pid.pid_value}")
            
            # Add recid to record
            record['recid'] = next_recid
            record.commit()
            db.session.commit()
            
            print("\nTest record created successfully!")
            print(f"Record ID: {record.id}")
            print(f"PID: {pid.pid_type}:{pid.pid_value}")
            print(f"Bucket ID: {record.get('bucket', 'No bucket')}")
            print("\nYou can now use this record for testing:")
            print(f"pipenv run invenio shell scripts/AlA/run_pdf_iiif.py {next_recid} sample.pdf")
            
            return next_recid, record.id
            
        except ImportError:
            print("Could not import PersistentIdentifier. Skipping PID creation.")
            db.session.rollback()
        except Exception as e:
            print(f"Error creating PID: {e}")
            db.session.rollback()
        
    except ImportError:
        print("Could not import Record class. Trying alternative approaches.")
    except Exception as e:
        print(f"Error creating record: {e}")
        db.session.rollback()
    
    # Approach 2: Try using RDM Records API
    try:
        from invenio_rdm_records.proxies import current_rdm_records
        from invenio_access.permissions import system_identity
        
        print("\nTrying to create an RDM record...")
        
        # Create a minimal RDM record
        data = {
            "metadata": {
                "title": "Test Record for IIIF PDF (RDM)",
                "publication_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "creators": [
                    {
                        "person_or_org": {
                            "name": "Test User",
                            "type": "personal"
                        },
                        "affiliations": [
                            {"name": "Test Organization"}
                        ]
                    }
                ],
                "resource_type": {"id": "image-photo"}
            },
            "access": {
                "record": "public",
                "files": "public"
            }
        }
        
        # Create the record
        service = current_rdm_records.records_service
        record = service.create(system_identity, data)
        
        print("\nRDM record created successfully!")
        print(f"Record ID: {record.id}")
        pid_value = record.id.split('-')[0]  # This might be different in different RDM versions
        print(f"PID: recid:{pid_value}")
        
        print("\nYou can now use this record for testing:")
        print(f"pipenv run invenio shell scripts/AlA/run_pdf_iiif.py {pid_value} sample.pdf")
        
        return pid_value, record.id
        
    except ImportError:
        print("RDM Records API not available.")
    except Exception as e:
        print(f"Error creating RDM record: {e}")
    
    print("\nFailed to create a test record using available methods.")
    return None, None

def main():
    create_test_record()

if __name__ == "__main__":
    main() 
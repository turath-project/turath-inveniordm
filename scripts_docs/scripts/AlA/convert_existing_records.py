#!/usr/bin/env python3
"""
Script to convert existing records' images to PTIF format for IIIF support.
This utilizes Zenodo-RDM's built-in TilesProcessor class.
"""

import sys
import os
from invenio_rdm_records.proxies import current_rdm_records_service as service
from invenio_rdm_records.records.processors.tiles import TilesProcessor
from invenio_records_resources.services.files.processors.image import ImageMetadataExtractor
from invenio_records_resources.services.uow import UnitOfWork, RecordCommitOp

def generate_iiif_tiles(recid):
    """Generate IIIF tiles for a record."""
    print(f"Processing record {recid}...")
    
    with UnitOfWork() as uow:
        try:
            record = service.record_cls.pid.resolve(recid)
            processor = TilesProcessor()
            # Call the processor on the record
            processor(None, record, uow=uow)
            uow.register(RecordCommitOp(record))

            # Calculate image dimensions for each supported image file
            image_metadata_extractor = ImageMetadataExtractor()
            for file_record in record.files.values():
                if image_metadata_extractor.can_process(file_record):
                    image_metadata_extractor.process(file_record)
                    file_record.commit()
            
            uow.commit()
            print(f"✓ Successfully processed record {recid}")
            return True
        except Exception as e:
            print(f"✗ Error processing record {recid}: {e}")
            return False

def process_records(record_ids):
    """Process a list of record IDs."""
    success = 0
    failure = 0
    
    for recid in record_ids:
        if generate_iiif_tiles(recid):
            success += 1
        else:
            failure += 1
    
    print(f"\nProcessing complete: {success} successful, {failure} failed")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Process records specified as command-line arguments
        record_ids = sys.argv[1:]
        process_records(record_ids)
    else:
        print("Usage: python convert_existing_records.py RECORD_ID [RECORD_ID...]")
        print("Example: python convert_existing_records.py 1234 5678")
        sys.exit(1) 
#!/usr/bin/env python
"""
Fix Cantaloupe file paths by copying files to expected locations.
This script helps diagnose issues with PDF file access in Cantaloupe.
"""

import os
import sys
import shutil
import json
import argparse
import requests
from invenio_app.factory import create_app
from flask import current_app
from invenio_access.permissions import system_identity

def fix_cantaloupe_path(record_id, filename):
    """Copy a file to the location expected by Cantaloupe."""
    app = create_app()
    
    with app.app_context():
        # Get the record service
        service = current_app.extensions['invenio-rdm-records'].records_service
        
        # Get the record to verify it exists
        try:
            record = service.read(system_identity, record_id)
            print(f"Found record ID: {record_id}")
            print(f"Record title: {record.data['metadata']['title']}")
            
            # Get the source file path
            data_dir = current_app.instance_path
            source_path = os.path.join(data_dir, "data", "records", record_id, "files", filename)
            
            if not os.path.exists(source_path):
                print(f"ERROR: Source file does not exist: {source_path}")
                return False
            
            print(f"Found source file: {source_path} ({os.path.getsize(source_path)} bytes)")
            
            # Get Cantaloupe configuration
            cantaloupe_url = current_app.config.get('RDM_IIIF_SERVER_URL', 'http://localhost:8182')
            
            # Extract base path from Cantaloupe error message
            test_url = f"{cantaloupe_url}/iiif/2/private%2F{record_id}%2F{filename}/info.json"
            print(f"Testing Cantaloupe access: {test_url}")
            
            try:
                response = requests.get(test_url)
                print(f"Response status: {response.status_code}")
                
                # If it's a 404, see if we can extract the expected path from the error
                if response.status_code == 404:
                    error_text = response.text
                    print(f"Error message: {error_text[:200]}...")
                    
                    # Look for the expected path in the error message
                    import re
                    path_match = re.search(r'Failed to resolve .+ to (.+?)$', error_text, re.MULTILINE)
                    
                    if path_match:
                        target_base = path_match.group(1).strip()
                        # Extract the directory part
                        target_dir = os.path.dirname(target_base)
                        # Replace the filename part
                        target_path = os.path.join(os.path.dirname(target_base), filename)
                        
                        print(f"Cantaloupe expects file at: {target_base}")
                        print(f"Target directory: {target_dir}")
                        
                        # Create the target directory if it doesn't exist
                        os.makedirs(target_dir, exist_ok=True)
                        
                        # Copy the file to the target location
                        print(f"Copying file to: {target_path}")
                        shutil.copy2(source_path, target_path)
                        
                        print(f"File copied successfully. Size: {os.path.getsize(target_path)} bytes")
                        
                        # Test Cantaloupe access again
                        print(f"Testing Cantaloupe access again: {test_url}")
                        response = requests.get(test_url)
                        print(f"Response status: {response.status_code}")
                        
                        if response.status_code == 200:
                            print("Success! Cantaloupe can now access the file.")
                            info = response.json()
                            print(f"File dimensions: {info.get('width')}x{info.get('height')}")
                            print(f"Number of pages: {len(info.get('tiles', [])) or len(info.get('sizes', []))}")
                            return True
                        else:
                            print(f"Error accessing file after copying: {response.text[:200]}...")
                            return False
                    else:
                        print("Could not extract target path from error message.")
                        return False
                elif response.status_code == 200:
                    print("Cantaloupe can already access the file!")
                    info = response.json()
                    print(f"File dimensions: {info.get('width')}x{info.get('height')}")
                    print(f"Number of pages: {len(info.get('tiles', [])) or len(info.get('sizes', []))}")
                    return True
            except Exception as e:
                print(f"Error testing Cantaloupe access: {str(e)}")
                return False
                
        except Exception as e:
            print(f"Error accessing record {record_id}: {str(e)}")
            return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Fix Cantaloupe file access")
    parser.add_argument("--record", "-r", required=True, help="Record ID")
    parser.add_argument("--filename", "-f", required=True, help="Filename")
    
    args = parser.parse_args()
    
    fix_cantaloupe_path(args.record, args.filename)

if __name__ == "__main__":
    main() 
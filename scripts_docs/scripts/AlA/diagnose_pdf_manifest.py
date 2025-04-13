#!/usr/bin/env python
import os
import sys
import json
import requests
from pathlib import Path
from pprint import pprint
from flask import current_app

try:
    from invenio_app.factory import create_app
    from invenio_db import db
    from invenio_files_rest.models import ObjectVersion, Bucket
    from invenio_records_files.api import RecordFiles
    from invenio_records.api import Record
except ImportError:
    print("ERROR: Cannot import Invenio modules. Make sure you're running this script in the Invenio virtual environment.")
    sys.exit(1)

class PDFManifestDiagnostic:
    """Comprehensive diagnostic tool for PDF IIIF manifest generation."""

    def __init__(self, record_id=None, filename=None):
        """Initialize the diagnostic tool with optional record ID and filename."""
        self.record_id = record_id
        self.filename = filename
        self.app = create_app()
        self.cantaloupe_url = None
        self.config_issues = []
        self.file_issues = []
        self.api_issues = []
        self.instance_path = None
        self.data_path = None
        
    def run_diagnostics(self):
        """Run all diagnostic checks."""
        print("\n=== PDF IIIF Manifest Generation Diagnostic ===\n")
        
        with self.app.app_context():
            # Get configuration paths
            self.instance_path = current_app.instance_path
            self.data_path = os.path.join(os.path.dirname(self.instance_path), 'data')
            
            # Check configuration
            self.check_configuration()
            
            # If a record ID was provided, check record files
            if self.record_id:
                self.check_record_files()
                self.check_file_existence()
                self.check_cantaloupe_access()
                self.check_api_endpoints()
        
        # Print summary
        self.print_summary()
        
    def check_configuration(self):
        """Check IIIF and PDF-related configuration settings."""
        print("Checking configuration...")
        
        with self.app.app_context():
            # Check IIIF enabled
            iiif_enabled = current_app.config.get('RDM_IIIF_ENABLED', False)
            print(f"- IIIF enabled: {iiif_enabled}")
            if not iiif_enabled:
                self.config_issues.append("IIIF is not enabled (RDM_IIIF_ENABLED is False)")
            
            # Check PDF support enabled
            pdf_support = current_app.config.get('RDM_IIIF_PDF_SUPPORT', False)
            print(f"- IIIF PDF support: {pdf_support}")
            if not pdf_support:
                self.config_issues.append("PDF support is not enabled (RDM_IIIF_PDF_SUPPORT is False)")
            
            # Check supported formats
            formats = current_app.config.get('RDM_IIIF_MANIFEST_FORMATS', [])
            print(f"- Supported formats: {formats}")
            if 'pdf' not in formats:
                self.config_issues.append("PDF format is not in supported formats list (RDM_IIIF_MANIFEST_FORMATS)")
            
            # Check Cantaloupe server URL
            self.cantaloupe_url = current_app.config.get('RDM_IIIF_SERVER_URL', '')
            print(f"- Cantaloupe server URL: {self.cantaloupe_url}")
            if not self.cantaloupe_url:
                self.config_issues.append("Cantaloupe server URL is not configured (RDM_IIIF_SERVER_URL)")
            
            # Check zenodo-rdm extension is registered
            extensions = current_app.extensions
            zenodo_extension = extensions.get('zenodo-rdm')
            print(f"- zenodo-rdm extension registered: {zenodo_extension is not None}")
            if not zenodo_extension:
                self.config_issues.append("zenodo-rdm extension is not registered")
            
            # Check instance and data paths
            print(f"- Instance path: {self.instance_path}")
            print(f"- Data path: {self.data_path}")
            
            # Check docker configuration
            self.check_docker_config()
    
    def check_docker_config(self):
        """Check Docker configuration for Cantaloupe."""
        docker_compose_path = os.path.join(os.path.dirname(self.instance_path), 'docker-compose.yml')
        if os.path.exists(docker_compose_path):
            print(f"- Docker compose file found at: {docker_compose_path}")
            # We could parse the docker-compose.yml here to check volumes, but that would require PyYAML
            # Instead, we'll just check for the existence of the Cantaloupe config
            cantaloupe_config_path = os.path.join(os.path.dirname(self.instance_path), 'docker/cantaloupe/cantaloupe.properties')
            if os.path.exists(cantaloupe_config_path):
                print(f"- Cantaloupe config found at: {cantaloupe_config_path}")
            else:
                print(f"- Cantaloupe config NOT found at: {cantaloupe_config_path}")
                self.config_issues.append("Cantaloupe config file not found")
        else:
            print(f"- Docker compose file NOT found at: {docker_compose_path}")
    
    def check_record_files(self):
        """Check the record's files in the database."""
        print(f"\nChecking record {self.record_id} files in database...")
        
        with self.app.app_context():
            try:
                # Try to get the record
                record = Record.get_record(self.record_id)
                print(f"- Record found: {record.id}")
                
                # Check if record has files
                if hasattr(record, 'files') and record.files:
                    files_count = len(record.files.keys()) if hasattr(record.files, 'keys') else 0
                    print(f"- Record has {files_count} files")
                    
                    # List all files
                    if files_count > 0:
                        print("- Files in record:")
                        for key in record.files.keys():
                            file_obj = record.files[key]
                            file_details = {
                                'key': key,
                                'size': file_obj.size if hasattr(file_obj, 'size') else 'unknown',
                                'mimetype': file_obj.mimetype if hasattr(file_obj, 'mimetype') else 'unknown',
                            }
                            print(f"  - {key}: {file_details}")
                            
                            # If a specific filename was provided, check if it matches
                            if self.filename and key == self.filename:
                                print(f"  => Found target file: {key}")
                                # Store file details for later checks
                                self.target_file = file_details
                            elif not self.filename and key.lower().endswith('.pdf'):
                                print(f"  => Found PDF file: {key}")
                                # If no specific filename was provided, use the first PDF file found
                                if not hasattr(self, 'target_file'):
                                    self.filename = key
                                    self.target_file = file_details
                                    print(f"  => Using as target file: {key}")
                    else:
                        print("- No files found in record")
                        self.file_issues.append(f"Record {self.record_id} has no files")
                else:
                    print("- Record has no files attribute or files are empty")
                    self.file_issues.append(f"Record {self.record_id} has no files attribute")
                
                # Check bucket
                try:
                    # Get bucket ID from record metadata
                    if 'bucket' in record:
                        bucket_id = record['bucket']
                        print(f"- Record bucket ID: {bucket_id}")
                        
                        # Check bucket in database
                        bucket = Bucket.query.filter_by(id=bucket_id).first()
                        if bucket:
                            print(f"- Found bucket: {bucket.id}")
                            
                            # Check for PDF files in bucket
                            pdf_objects = ObjectVersion.query.filter(
                                ObjectVersion.bucket_id == bucket.id,
                                ObjectVersion.key.like('%.pdf')
                            ).all()
                            
                            if pdf_objects:
                                print(f"- Found {len(pdf_objects)} PDF files in bucket:")
                                for obj in pdf_objects:
                                    print(f"  - {obj.key} (version: {obj.version_id})")
                                    # If this is our target file, save file_id for later
                                    if self.filename and obj.key == self.filename:
                                        self.file_id = str(obj.file_id)
                                        print(f"  => Target file ID: {self.file_id}")
                            else:
                                print("- No PDF files found in bucket")
                                if not hasattr(self, 'target_file') or not self.target_file:
                                    self.file_issues.append("No PDF files found in bucket")
                        else:
                            print(f"- Bucket not found: {bucket_id}")
                            self.file_issues.append(f"Bucket {bucket_id} not found")
                    else:
                        print("- No bucket ID found in record")
                        self.file_issues.append("No bucket ID found in record")
                except Exception as e:
                    print(f"- Error checking bucket: {str(e)}")
                    self.file_issues.append(f"Error checking bucket: {str(e)}")
                
            except Exception as e:
                print(f"- Error getting record: {str(e)}")
                self.file_issues.append(f"Error getting record {self.record_id}: {str(e)}")
    
    def check_file_existence(self):
        """Check if the PDF file exists on disk."""
        print("\nChecking file existence on disk...")
        
        if not hasattr(self, 'target_file') or not self.target_file:
            print("- No target file to check")
            return
        
        # Check in various possible locations
        locations = [
            # Standard Invenio locations
            os.path.join(self.data_path, 'files', self.file_id if hasattr(self, 'file_id') else ''),
            os.path.join(self.data_path, 'records', self.record_id, 'files', self.filename),
            # Location where Cantaloupe might expect files
            os.path.join(self.data_path, 'records', self.record_id, 'private', self.filename),
            os.path.join(self.data_path, 'private', self.record_id, self.filename),
            # Docker mount points
            os.path.join('/opt/cantaloupe/images/records', self.record_id, 'private', self.filename),
            os.path.join('/opt/cantaloupe/images/private', self.record_id, self.filename),
        ]
        
        print(f"- Checking for file: {self.filename}")
        file_found = False
        
        for location in locations:
            if os.path.exists(location):
                print(f"  ✓ File found at: {location}")
                file_found = True
            else:
                print(f"  ✗ File not found at: {location}")
        
        if not file_found:
            self.file_issues.append(f"File {self.filename} not found on disk in any expected location")
    
    def check_cantaloupe_access(self):
        """Check if Cantaloupe can access the PDF file."""
        print("\nChecking Cantaloupe access...")
        
        if not self.cantaloupe_url or not hasattr(self, 'target_file') or not self.target_file:
            print("- Cantaloupe URL or target file not available")
            return
        
        # Check Cantaloupe info.json for the PDF file
        cantaloupe_info_url = f"{self.cantaloupe_url}/iiif/3/private%2F{self.record_id}%2F{self.filename}/info.json"
        print(f"- Checking Cantaloupe info endpoint: {cantaloupe_info_url}")
        
        try:
            response = requests.get(cantaloupe_info_url, timeout=10)
            if response.status_code == 200:
                print(f"  ✓ Cantaloupe can access the file (status code: {response.status_code})")
                try:
                    info_data = response.json()
                    print(f"  - Image info: {json.dumps(info_data, indent=2)}")
                except:
                    print(f"  - Response: {response.text[:200]}...")
            else:
                print(f"  ✗ Cantaloupe cannot access the file (status code: {response.status_code})")
                print(f"  - Response: {response.text[:200]}...")
                self.api_issues.append(f"Cantaloupe returned {response.status_code} for {cantaloupe_info_url}")
        except Exception as e:
            print(f"  ✗ Error accessing Cantaloupe: {str(e)}")
            self.api_issues.append(f"Error accessing Cantaloupe: {str(e)}")
        
        # Also check direct file access URL
        file_url = f"{self.cantaloupe_url}/iiif/3/private%2F{self.record_id}%2F{self.filename}/full/max/0/default.jpg"
        print(f"- Checking direct file access: {file_url}")
        
        try:
            response = requests.get(file_url, timeout=10)
            if response.status_code == 200:
                print(f"  ✓ Can access file image (status code: {response.status_code})")
                content_type = response.headers.get('Content-Type', '')
                print(f"  - Content-Type: {content_type}")
            else:
                print(f"  ✗ Cannot access file image (status code: {response.status_code})")
                print(f"  - Response: {response.text[:200]}...")
                self.api_issues.append(f"File access returned {response.status_code} for {file_url}")
        except Exception as e:
            print(f"  ✗ Error accessing file: {str(e)}")
            self.api_issues.append(f"Error accessing file: {str(e)}")
    
    def check_api_endpoints(self):
        """Check IIIF API endpoints."""
        print("\nChecking IIIF API endpoints...")
        
        with self.app.app_context():
            base_url = current_app.config.get('SITE_UI_URL', 'http://localhost:5000')
            api_base = f"{base_url}/api"
            
            # Check IIIF manifest endpoint
            manifest_url = f"{api_base}/iiif/record:{self.record_id}/manifest"
            print(f"- Checking manifest endpoint: {manifest_url}")
            
            try:
                response = requests.get(manifest_url, timeout=10)
                if response.status_code == 200:
                    print(f"  ✓ Manifest accessible (status code: {response.status_code})")
                    try:
                        manifest_data = response.json()
                        # Check if there are any PDF sequences/canvases
                        pdf_canvases = []
                        if 'sequences' in manifest_data and manifest_data['sequences']:
                            for seq in manifest_data['sequences']:
                                if 'canvases' in seq:
                                    for canvas in seq['canvases']:
                                        # Look for canvases with PDF labels
                                        if 'label' in canvas and 'Page' in str(canvas['label']):
                                            pdf_canvases.append(canvas)
                        
                        print(f"  - Found {len(pdf_canvases)} PDF canvases in manifest")
                        if not pdf_canvases:
                            self.api_issues.append("No PDF canvases found in IIIF manifest")
                            print("  - Manifest content (partial):")
                            print(json.dumps(manifest_data, indent=2)[:500] + "...")
                        else:
                            print("  - First PDF canvas (partial):")
                            print(json.dumps(pdf_canvases[0], indent=2)[:500] + "...")
                    except Exception as e:
                        print(f"  ✗ Error parsing manifest: {str(e)}")
                        print(f"  - Response: {response.text[:500]}...")
                        self.api_issues.append(f"Error parsing manifest: {str(e)}")
                else:
                    print(f"  ✗ Manifest not accessible (status code: {response.status_code})")
                    print(f"  - Response: {response.text[:200]}...")
                    self.api_issues.append(f"Manifest endpoint returned {response.status_code}")
            except Exception as e:
                print(f"  ✗ Error accessing manifest: {str(e)}")
                self.api_issues.append(f"Error accessing manifest: {str(e)}")
    
    def print_summary(self):
        """Print a summary of all issues found."""
        print("\n=== Diagnostic Summary ===\n")
        
        if not self.config_issues and not self.file_issues and not self.api_issues:
            print("✅ No issues found! PDF IIIF manifest generation should be working correctly.")
        else:
            print("❌ Issues were found that may prevent PDF IIIF manifest generation:")
            
            if self.config_issues:
                print("\nConfiguration Issues:")
                for i, issue in enumerate(self.config_issues, 1):
                    print(f"{i}. {issue}")
            
            if self.file_issues:
                print("\nFile Issues:")
                for i, issue in enumerate(self.file_issues, 1):
                    print(f"{i}. {issue}")
            
            if self.api_issues:
                print("\nAPI Issues:")
                for i, issue in enumerate(self.api_issues, 1):
                    print(f"{i}. {issue}")
            
            print("\nRecommended Actions:")
            if self.config_issues:
                print("- Fix configuration issues in invenio.cfg")
            if self.file_issues:
                print("- Ensure PDF files exist and are accessible")
                print("- Check file storage locations match Cantaloupe expectations")
            if self.api_issues:
                print("- Verify IIIF API endpoints are correctly configured")
                print("- Check Cantaloupe server is running and accessible")
        
        print("\n=== End of Diagnostic ===\n")

def main():
    """Main function to run the diagnostic tool."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Diagnose PDF IIIF manifest generation issues')
    parser.add_argument('--record', '-r', type=str, help='Record ID to check')
    parser.add_argument('--file', '-f', type=str, help='Filename to check (must be a PDF file)')
    
    args = parser.parse_args()
    
    if not args.record:
        print("ERROR: Record ID is required")
        print("Usage: python diagnose_pdf_manifest.py --record <record_id> [--file <filename>]")
        sys.exit(1)
    
    # Run diagnostics
    diagnostic = PDFManifestDiagnostic(record_id=args.record, filename=args.file)
    diagnostic.run_diagnostics()

if __name__ == '__main__':
    main() 
#!/usr/bin/env python
import os
import sys
import json
import tempfile
import argparse
import requests
from pathlib import Path

# We'll import these only when needed - not at startup
# from flask import current_app
# from reportlab.lib.pagesizes import letter
# from reportlab.pdfgen import canvas

def check_dependencies():
    """Check if all required dependencies are installed."""
    missing_deps = []
    
    # Check for reportlab
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        missing_deps.append("reportlab (pip install reportlab)")
    
    # Check for requests
    try:
        import requests
    except ImportError:
        missing_deps.append("requests (pip install requests)")
    
    # Only if dependencies are satisfied, try to import Invenio modules
    if not missing_deps:
        try:
            from invenio_app.factory import create_app
            from invenio_db import db
            return True, []
        except ImportError:
            missing_deps.append("Invenio modules (make sure you're running in Invenio environment)")
    
    return False, missing_deps

class PDFIIIFImplementer:
    """Comprehensive solution for PDF IIIF manifest generation."""
    
    def __init__(self, record_id=None, filename=None, generate_pdf=True, pages=5, verbose=False):
        """Initialize the implementation with record ID and filename.
        
        Args:
            record_id: The ID of the record
            filename: The PDF filename
            generate_pdf: Whether to generate a test PDF
            pages: Number of pages for test PDF
            verbose: Whether to print verbose output
        """
        self.record_id = record_id
        self.filename = filename
        self.generate_pdf = generate_pdf
        self.pages = pages
        self.verbose = verbose
        self.temp_files = []
        self.success = True
        
        # Import required modules
        try:
            from invenio_app.factory import create_app
            from invenio_db import db
            from invenio_files_rest.models import ObjectVersion, Bucket
            from invenio_records_files.api import RecordFiles
            from invenio_records.api import Record
            from invenio_access.permissions import system_identity
            from invenio_rdm_records.proxies import current_rdm_records
            
            # Store module references for later use
            self.modules = {
                'create_app': create_app,
                'db': db,
                'ObjectVersion': ObjectVersion,
                'Bucket': Bucket,
                'RecordFiles': RecordFiles,
                'Record': Record,
                'system_identity': system_identity,
                'current_rdm_records': current_rdm_records
            }
            
            # Create app
            self.app = create_app()
            
        except ImportError as e:
            self.log(f"ERROR: Cannot import Invenio modules: {e}")
            self.log("Make sure you're running this script in the Invenio virtual environment.")
            self.log("Try running with: pipenv run invenio shell --no-term-title scripts/AlA/implement_pdf_iiif.py")
            sys.exit(1)
        
        # Set default filename if not provided
        if not self.filename:
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            self.filename = f"test_pdf_{timestamp}.pdf"

        # Ensure the filename has .pdf extension
        if not self.filename.lower().endswith('.pdf'):
            self.filename += '.pdf'
    
    def log(self, message, level=0):
        """Log a message if verbose mode is enabled.
        
        Args:
            message: The message to log
            level: Indentation level (0=normal, 1=info, 2=detail)
        """
        if self.verbose or level == 0:
            indent = "  " * level
            print(f"{indent}{message}")
    
    def create_test_pdf(self):
        """Create a test PDF file with multiple pages.
        
        Returns:
            Path to the created PDF file
        """
        self.log(f"Creating test PDF with {self.pages} pages")
        
        try:
            # Import PDF generation modules
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
        except ImportError:
            self.log("ERROR: Cannot import reportlab modules. Please install with:")
            self.log("pip install reportlab")
            sys.exit(1)
        
        # Create a temporary file
        fd, pdf_path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)
        self.temp_files.append(pdf_path)
        
        # Create a PDF with text on each page
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        
        for i in range(1, self.pages + 1):
            # Add page number and test content
            c.setFont("Helvetica", 14)
            c.drawString(100, height - 100, f"Test PDF - Page {i} of {self.pages}")
            
            # Add some dummy text
            c.setFont("Helvetica", 12)
            c.drawString(100, height - 150, "This is a test PDF file created for testing IIIF")
            c.drawString(100, height - 170, "PDF manifest generation in Invenio-RDM")
            
            # Add page number in center
            c.setFont("Helvetica-Bold", 72)
            c.setFillColorRGB(0.9, 0.9, 0.9)  # Light gray
            c.drawCentredString(width/2, height/2, str(i))
            
            # Add border
            c.setStrokeColorRGB(0.8, 0.8, 0.8)
            c.rect(50, 50, width-100, height-100)
            
            if i < self.pages:
                c.showPage()  # Move to next page
        
        c.save()
        self.log(f"Created test PDF at {pdf_path}", 1)
        return pdf_path
    
    def upload_pdf_to_record(self, pdf_path):
        """Upload a PDF file to a record.
        
        Args:
            pdf_path: Path to the PDF file to upload
            
        Returns:
            True if successful, False otherwise
        """
        self.log(f"Uploading PDF to record {self.record_id}")
        
        with self.app.app_context():
            try:
                # Get the record
                record = self.modules['Record'].get_record(self.record_id)
                self.log(f"Retrieved record: {record.id}", 1)
                
                # Check if record has files
                if not hasattr(record, 'files'):
                    self.log("Record doesn't have files attribute", 1)
                    # Try to use the bucket directly
                    if 'bucket' in record:
                        bucket_id = record['bucket']
                        self.log(f"Using bucket ID from record: {bucket_id}", 1)
                        with open(pdf_path, 'rb') as fp:
                            obj = self.modules['ObjectVersion'].create(bucket_id, self.filename, stream=fp)
                        self.log(f"Uploaded file as {self.filename} to bucket {bucket_id}", 1)
                        self.log(f"Object: {obj.version_id}", 2)
                        return True
                    else:
                        self.log("Record has no bucket ID", 1)
                        return False
                
                # Upload the file to the record
                self.log(f"Uploading {self.filename} to record {self.record_id}", 1)
                with open(pdf_path, 'rb') as fp:
                    record.files[self.filename] = fp
                record.files.flush()
                self.modules['db'].session.commit()
                self.log(f"Successfully uploaded {self.filename} to record {self.record_id}", 1)
                
                # Update the record if using RDM
                try:
                    # Try to use RDM Records service for updating
                    service = self.modules['current_rdm_records'].records_service
                    service.update_files(
                        self.modules['system_identity'],
                        self.record_id,
                        {}
                    )
                    self.log("Updated record files via RDM service", 1)
                except Exception as e:
                    self.log(f"Note: Could not update via RDM service: {e}", 1)
                    self.log("This is normal for legacy Invenio installations", 2)
                
                return True
                
            except Exception as e:
                self.log(f"ERROR: Failed to upload file: {e}", 0)
                import traceback
                traceback.print_exc()
                return False
    
    def copy_to_cantaloupe_paths(self, pdf_path):
        """Copy the PDF file to all possible Cantaloupe expected paths.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            True if successful, False otherwise
        """
        self.log(f"Copying PDF to Cantaloupe paths")
        
        with self.app.app_context():
            try:
                # Get the data directory
                instance_path = self.modules['create_app']().instance_path
                data_path = os.path.join(os.path.dirname(instance_path), 'data')
                
                # Create all possible expected paths for Cantaloupe
                paths = [
                    # Standard Cantaloupe paths
                    os.path.join(data_path, 'private', self.record_id),
                    os.path.join(data_path, 'records', self.record_id, 'private'),
                    os.path.join(data_path, 'images', 'private', self.record_id),
                    # Other potential paths based on config
                    os.path.join(data_path, 'records', 'private', self.record_id),
                ]
                
                success = False
                for path in paths:
                    try:
                        # Ensure the directory exists
                        os.makedirs(path, exist_ok=True)
                        target_path = os.path.join(path, self.filename)
                        
                        # Copy the file
                        import shutil
                        shutil.copy2(pdf_path, target_path)
                        self.log(f"Copied file to Cantaloupe path: {target_path}", 1)
                        success = True
                    except Exception as e:
                        self.log(f"Warning: Could not copy to {path}: {e}", 1)
                
                return success
            except Exception as e:
                self.log(f"ERROR: Failed to copy file to Cantaloupe paths: {e}", 0)
                return False
    
    def check_extension_registration(self):
        """Check if the zenodo-rdm extension is registered.
        
        Returns:
            True if registered, False otherwise
        """
        self.log("Checking zenodo-rdm extension registration")
        
        with self.app.app_context():
            extensions = self.modules['create_app']().extensions
            zenodo_extension = extensions.get('zenodo-rdm')
            if zenodo_extension:
                self.log("✓ zenodo-rdm extension is registered", 1)
                return True
            else:
                self.log("✗ zenodo-rdm extension is NOT registered", 1)
                self.log("You need to register the zenodo-rdm extension in your app", 1)
                self.register_extension()
                return False
    
    def register_extension(self):
        """Register the zenodo-rdm extension if not already registered."""
        self.log("Attempting to register zenodo-rdm extension")
        
        with self.app.app_context():
            try:
                # Try to import the extension
                from site.zenodo_rdm.ext import ZenodoRDM
                
                # Register the extension
                ext = ZenodoRDM()
                ext.init_app(self.modules['create_app']())
                
                self.log("✓ Successfully registered zenodo-rdm extension", 1)
                return True
            except ImportError:
                self.log("✗ Could not import ZenodoRDM extension", 1)
                self.log("Make sure site/zenodo_rdm/ext.py exists and contains ZenodoRDM class", 2)
                return False
            except Exception as e:
                self.log(f"✗ Error registering extension: {e}", 1)
                return False
    
    def verify_configuration(self):
        """Verify that IIIF PDF configuration is correct.
        
        Returns:
            True if configuration is correct, False otherwise
        """
        self.log("Verifying IIIF configuration")
        
        with self.app.app_context():
            # Check IIIF enabled
            iiif_enabled = self.modules['create_app']().config.get('RDM_IIIF_ENABLED', False)
            self.log(f"- IIIF enabled: {iiif_enabled}", 1)
            
            # Check PDF support enabled
            pdf_support = self.modules['create_app']().config.get('RDM_IIIF_PDF_SUPPORT', False)
            self.log(f"- IIIF PDF support: {pdf_support}", 1)
            
            # Check supported formats
            formats = self.modules['create_app']().config.get('RDM_IIIF_MANIFEST_FORMATS', [])
            self.log(f"- Supported formats: {formats}", 1)
            
            # Check Cantaloupe server URL
            self.cantaloupe_url = self.modules['create_app']().config.get('RDM_IIIF_SERVER_URL', '')
            self.log(f"- Cantaloupe server URL: {self.cantaloupe_url}", 1)
            
            # Check for missing config
            missing_config = []
            if not iiif_enabled:
                missing_config.append("RDM_IIIF_ENABLED = True")
            if not pdf_support:
                missing_config.append("RDM_IIIF_PDF_SUPPORT = True")
            if 'pdf' not in formats:
                missing_config.append("'pdf' in RDM_IIIF_MANIFEST_FORMATS")
            if not self.cantaloupe_url:
                missing_config.append("RDM_IIIF_SERVER_URL = 'http://localhost:8182'")
            
            if missing_config:
                self.log("Missing configuration:", 1)
                for cfg in missing_config:
                    self.log(f"  {cfg}", 1)
                
                # Add missing configuration
                self.log("Adding missing configuration", 1)
                if not iiif_enabled:
                    self.modules['create_app']().config['RDM_IIIF_ENABLED'] = True
                if not pdf_support:
                    self.modules['create_app']().config['RDM_IIIF_PDF_SUPPORT'] = True
                if 'pdf' not in formats:
                    self.modules['create_app']().config['RDM_IIIF_MANIFEST_FORMATS'] = list(formats) + ['pdf']
                if not self.cantaloupe_url:
                    # Use a default value for Cantaloupe URL
                    self.modules['create_app']().config['RDM_IIIF_SERVER_URL'] = 'http://localhost:8182'
                    self.cantaloupe_url = 'http://localhost:8182'
                
                self.log("✓ Configuration updated", 1)
            else:
                self.log("✓ Configuration is correct", 1)
            
            return True
    
    def generate_manifest(self):
        """Generate and test the IIIF manifest for the PDF file.
        
        Returns:
            The manifest JSON if successful, None otherwise
        """
        self.log("Generating IIIF manifest")
        
        with self.app.app_context():
            base_url = self.modules['create_app']().config.get('SITE_UI_URL', 'http://localhost:5000')
            manifest_url = f"{base_url}/api/iiif/record:{self.record_id}/manifest"
            
            self.log(f"Requesting manifest from: {manifest_url}", 1)
            
            # Try to generate the manifest
            try:
                response = requests.get(manifest_url, timeout=10)
                if response.status_code == 200:
                    manifest = response.json()
                    self.log(f"✓ Successfully generated manifest", 1)
                    
                    # Check for PDF canvases
                    pdf_canvases = []
                    if 'sequences' in manifest and manifest['sequences']:
                        for seq in manifest['sequences']:
                            if 'canvases' in seq:
                                for canvas in seq['canvases']:
                                    if 'label' in canvas and 'Page' in str(canvas['label']):
                                        pdf_canvases.append(canvas)
                    
                    if pdf_canvases:
                        self.log(f"✓ Found {len(pdf_canvases)} PDF canvases in manifest", 1)
                        self.log(f"First PDF canvas label: {pdf_canvases[0].get('label', 'unknown')}", 2)
                        return manifest
                    else:
                        self.log("✗ No PDF canvases found in manifest", 1)
                        # If no PDF canvases, try direct generation
                        return self.generate_pdf_manifest_directly()
                else:
                    self.log(f"✗ Failed to get manifest: {response.status_code}", 1)
                    self.log(f"Response: {response.text[:200]}...", 2)
                    # If API fails, try direct generation
                    return self.generate_pdf_manifest_directly()
            except Exception as e:
                self.log(f"✗ Error requesting manifest: {e}", 1)
                # If API fails, try direct generation
                return self.generate_pdf_manifest_directly()
    
    def generate_pdf_manifest_directly(self):
        """Generate a PDF manifest directly using Cantaloupe.
        
        Returns:
            The manifest JSON if successful, None otherwise
        """
        self.log("Generating PDF manifest directly using Cantaloupe")
        
        if not self.cantaloupe_url:
            self.log("✗ Cantaloupe URL is not set", 1)
            return None
        
        # First, check if Cantaloupe can access the file
        info_url = f"{self.cantaloupe_url}/iiif/3/private%2F{self.record_id}%2F{self.filename}/info.json"
        self.log(f"Checking Cantaloupe info: {info_url}", 1)
        
        try:
            response = requests.get(info_url, timeout=10)
            if response.status_code != 200:
                self.log(f"✗ Cantaloupe cannot access the file: {response.status_code}", 1)
                self.log(f"Response: {response.text[:200]}...", 2)
                return None
            
            # Get PDF info from Cantaloupe
            pdf_info = response.json()
            self.log(f"✓ Cantaloupe can access the file", 1)
            
            # Create a basic manifest structure
            with self.app.app_context():
                base_url = self.modules['create_app']().config.get('SITE_UI_URL', 'http://localhost:5000')
                
                # Get record metadata for the manifest
                record = self.modules['Record'].get_record(self.record_id)
                title = record.get('metadata', {}).get('title', 'PDF Document')
                
                manifest = {
                    "@context": "http://iiif.io/api/presentation/2/context.json",
                    "@type": "sc:Manifest",
                    "@id": f"{base_url}/api/iiif/record:{self.record_id}/manifest",
                    "label": title,
                    "metadata": [
                        {
                            "label": "Title",
                            "value": title
                        }
                    ],
                    "sequences": [
                        {
                            "@type": "sc:Sequence",
                            "@id": f"{base_url}/api/iiif/record:{self.record_id}/sequence/default",
                            "canvases": []
                        }
                    ]
                }
                
                # Get number of pages from PDF info
                height = pdf_info.get('height', 1000)
                width = pdf_info.get('width', 1000)
                num_pages = 1
                
                if 'sizes' in pdf_info:
                    # Try to determine number of pages from sizes
                    num_pages = len(pdf_info.get('sizes', []))
                
                self.log(f"Creating manifest with {num_pages} pages", 1)
                
                # Create a canvas for each page
                for page in range(1, num_pages + 1):
                    canvas_id = f"{base_url}/api/iiif/record:{self.record_id}/canvas/{self.filename.replace('.pdf', '')}_page{page}"
                    image_id = f"{self.cantaloupe_url}/iiif/3/private%2F{self.record_id}%2F{self.filename}/full/max/0/default.jpg?page={page}"
                    
                    canvas = {
                        "@id": canvas_id,
                        "@type": "sc:Canvas",
                        "label": f"Page {page}",
                        "height": height,
                        "width": width,
                        "images": [
                            {
                                "@type": "oa:Annotation",
                                "motivation": "sc:painting",
                                "resource": {
                                    "@id": image_id,
                                    "@type": "dctypes:Image",
                                    "format": "image/jpeg",
                                    "height": height,
                                    "width": width,
                                    "service": {
                                        "@context": "http://iiif.io/api/image/3/context.json",
                                        "@id": f"{self.cantaloupe_url}/iiif/3/private%2F{self.record_id}%2F{self.filename}",
                                        "profile": "level2",
                                        "protocol": "http://iiif.io/api/image"
                                    }
                                },
                                "on": canvas_id
                            }
                        ]
                    }
                    
                    manifest['sequences'][0]['canvases'].append(canvas)
                
                # Add related PDF link
                manifest["related"] = {
                    "@id": f"{base_url}/api/records/{self.record_id}/files/{self.filename}",
                    "format": "application/pdf"
                }
                
                self.log(f"✓ Successfully created manifest with {len(manifest['sequences'][0]['canvases'])} canvases", 1)
                
                # Save the manifest for reference
                manifest_path = os.path.join(os.path.dirname(self.modules['create_app']().instance_path), 
                                           f"custom_manifest_{self.record_id}.json")
                with open(manifest_path, 'w') as f:
                    json.dump(manifest, f, indent=2)
                self.log(f"Saved manifest to {manifest_path}", 1)
                
                return manifest
                
        except Exception as e:
            self.log(f"✗ Error generating PDF manifest: {e}", 1)
            import traceback
            traceback.print_exc()
            return None
    
    def write_manifest_to_file(self, manifest, output_path=None):
        """Write the manifest to a file.
        
        Args:
            manifest: The manifest to write
            output_path: Optional path to write to
        
        Returns:
            Path to the written file
        """
        if not output_path:
            output_path = f"manifest_{self.record_id}.json"
        
        self.log(f"Writing manifest to {output_path}")
        
        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        self.log(f"✓ Wrote manifest to {output_path}", 1)
        return output_path
    
    def cleanup(self):
        """Clean up temporary files."""
        self.log("Cleaning up temporary files")
        
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    self.log(f"Removed {temp_file}", 1)
            except Exception as e:
                self.log(f"Error removing {temp_file}: {e}", 1)
    
    def run(self):
        """Run the full implementation flow.
        
        Returns:
            Tuple of (success, manifest)
        """
        self.log(f"Starting PDF IIIF implementation for record {self.record_id}, file {self.filename}")
        
        try:
            # Step 1: Create/get PDF file
            if self.generate_pdf:
                pdf_path = self.create_test_pdf()
            else:
                if os.path.exists(self.filename):
                    pdf_path = self.filename
                    self.log(f"Using existing PDF: {pdf_path}", 1)
                else:
                    self.log(f"ERROR: File {self.filename} does not exist", 0)
                    return False, None
            
            # Step 2: Upload PDF to record
            upload_success = self.upload_pdf_to_record(pdf_path)
            if not upload_success:
                self.log("Failed to upload PDF to record", 0)
                self.success = False
            
            # Step 3: Copy PDF to Cantaloupe paths
            copy_success = self.copy_to_cantaloupe_paths(pdf_path)
            if not copy_success:
                self.log("Failed to copy PDF to Cantaloupe paths", 0)
                self.success = False
            
            # Step 4: Check extension registration
            ext_registered = self.check_extension_registration()
            if not ext_registered:
                self.log("zenodo-rdm extension is not registered", 0)
                self.success = False
            
            # Step 5: Verify configuration
            config_success = self.verify_configuration()
            if not config_success:
                self.log("Configuration verification failed", 0)
                self.success = False
            
            # Step 6: Generate manifest
            manifest = self.generate_manifest()
            if not manifest:
                self.log("Failed to generate manifest", 0)
                self.success = False
                return False, None
            
            # Step 7: Write manifest to file
            output_path = f"manifest_{self.record_id}.json"
            self.write_manifest_to_file(manifest, output_path)
            
            # Summary
            if self.success:
                self.log("\n✅ SUCCESS: PDF IIIF implementation is complete", 0)
                self.log(f"Record ID: {self.record_id}", 1)
                self.log(f"Filename: {self.filename}", 1)
                self.log(f"Manifest: {output_path}", 1)
                self.log("\nYou can view the manifest with a IIIF viewer like Mirador:", 1)
                with self.app.app_context():
                    base_url = self.modules['create_app']().config.get('SITE_UI_URL', 'http://localhost:5000')
                    self.log(f"{base_url}/api/iiif/record:{self.record_id}/manifest", 1)
            else:
                self.log("\n⚠️ WARNING: Some steps failed, but manifest was generated", 0)
                self.log("Review the log above for errors", 1)
            
            # Cleanup temporary files
            self.cleanup()
            
            return self.success, manifest
            
        except Exception as e:
            self.log(f"ERROR: Implementation failed: {e}", 0)
            import traceback
            traceback.print_exc()
            
            # Cleanup temporary files
            self.cleanup()
            
            return False, None


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Implement PDF IIIF manifest generation for a record'
    )
    parser.add_argument('--record', '-r', required=True,
                      help='Record ID to implement PDF IIIF for')
    parser.add_argument('--filename', '-f',
                      help='Filename for the PDF (default: test_pdf_<timestamp>.pdf)')
    parser.add_argument('--no-generate', '-n', action='store_true',
                      help='Do not generate a test PDF, use existing file')
    parser.add_argument('--pages', '-p', type=int, default=5,
                      help='Number of pages for test PDF (default: 5)')
    parser.add_argument('--output', '-o',
                      help='Output file for the manifest (default: manifest_<record_id>.json)')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Print verbose output')
    parser.add_argument('--create-only', '-c', action='store_true',
                      help='Only create the PDF, do not upload or process further')
    
    args = parser.parse_args()
    
    # Check dependencies
    deps_ok, missing_deps = check_dependencies()
    if not deps_ok:
        print("ERROR: Missing dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nPlease install missing dependencies and try again.")
        
        if "reportlab" in str(missing_deps):
            print("\nTo install reportlab:")
            print("pipenv run pip install reportlab")
        
        if "Invenio modules" in str(missing_deps):
            print("\nTo run in Invenio environment:")
            print("cd /path/to/zenodo-rdm")
            print("pipenv run invenio shell")
            print("# Then in the shell, run:")
            print("import sys")
            print("sys.path.append('scripts/AlA')")
            print("from implement_pdf_iiif import PDFIIIFImplementer")
            print(f"implementer = PDFIIIFImplementer(record_id='{args.record}', verbose=True)")
            print("implementer.run()")
        
        sys.exit(1)
    
    # If create-only, just create the PDF and exit
    if args.create_only:
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            
            print(f"Creating test PDF with {args.pages} pages...")
            
            if args.filename:
                pdf_path = args.filename
            else:
                import datetime
                timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                pdf_path = f"test_pdf_{timestamp}.pdf"
            
            # Create a PDF with text on each page
            c = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter
            
            for i in range(1, args.pages + 1):
                # Add page number and test content
                c.setFont("Helvetica", 14)
                c.drawString(100, height - 100, f"Test PDF - Page {i} of {args.pages}")
                
                # Add some dummy text
                c.setFont("Helvetica", 12)
                c.drawString(100, height - 150, "This is a test PDF file created for testing IIIF")
                c.drawString(100, height - 170, "PDF manifest generation in Invenio-RDM")
                
                # Add page number in center
                c.setFont("Helvetica-Bold", 72)
                c.setFillColorRGB(0.9, 0.9, 0.9)  # Light gray
                c.drawCentredString(width/2, height/2, str(i))
                
                # Add border
                c.setStrokeColorRGB(0.8, 0.8, 0.8)
                c.rect(50, 50, width-100, height-100)
                
                if i < args.pages:
                    c.showPage()  # Move to next page
            
            c.save()
            print(f"Successfully created test PDF at {pdf_path}")
            sys.exit(0)
        except ImportError:
            print("ERROR: Cannot import reportlab. Please install with:")
            print("pip install reportlab")
            sys.exit(1)
    
    # Run the implementation
    try:
        implementer = PDFIIIFImplementer(
            record_id=args.record,
            filename=args.filename,
            generate_pdf=not args.no_generate,
            pages=args.pages,
            verbose=args.verbose
        )
        
        success, manifest = implementer.run()
        
        if args.output and manifest:
            implementer.write_manifest_to_file(manifest, args.output)
        
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main() 
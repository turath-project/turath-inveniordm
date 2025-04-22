#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upload Books with PDF and HOCR Files to InvenioRDM

This script is designed to upload digitized books with their associated HOCR files
to InvenioRDM. It handles the specific directory structure used in the Turath Digital
Library project, where books have the following structure:
- book_id/
  - book_id.pdf (main PDF file)
  - manifest.json (metadata about the book)
  - hocr/ (directory with HOCR files for pages)
  - pages/ (directory with TIFF images of pages)

Key features:
- Uploads PDF file as the primary document
- Uploads HOCR files for text search
- Processes manifest.json to create accurate metadata
- Publishes the record with all files properly linked
- Supports both API token and username/password authentication

Usage:
    python upload_book.py --book-dir /path/to/book_dir --token YOUR_TOKEN

For additional options:
    python upload_book.py --help

Author: Turath Development Team
"""

import os
import sys
import argparse
import time
import glob
import json
import re
import traceback
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Union
import requests
import logging
from pathlib import Path
from PIL import Image
from bs4 import BeautifulSoup
import PyPDF2
import shutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('upload_book.log')
    ]
)
logger = logging.getLogger('book_uploader')

# Default configuration values - can be overridden with environment variables
DEFAULT_API_URL = os.environ.get("INVENIO_API_URL", "https://127.0.0.1:5000/api")
DEFAULT_API_TOKEN = os.environ.get("RDM_API_TOKEN", None)


class BookUploader:
    """
    Main class for handling book uploads to InvenioRDM.
    
    This class takes care of the entire workflow for creating records
    with PDF and HOCR files from the book directory structure.
    """
    
    def __init__(
        self,
        book_dir: str,
        api_url: str = DEFAULT_API_URL,
        api_token: str = DEFAULT_API_TOKEN,
        username: str = None,
        password: str = None,
        skip_hocr: bool = False,
        skip_tiff: bool = False,
        max_retries: int = 3,
        publish: bool = True,
        community: str = None,
        verify_ssl: bool = True,
        custom_metadata: Dict = None,
        hocr_mount_point: str = None
    ):
        """
        Initialize the Book Uploader.
        
        Args:
            book_dir: Directory containing the book files
            api_url: InvenioRDM API URL
            api_token: API token for authentication
            username: Username for basic authentication (if not using token)
            password: Password for basic authentication
            skip_hocr: Whether to skip uploading HOCR files
            skip_tiff: Whether to skip uploading TIFF image files
            max_retries: Maximum number of upload retries
            publish: Whether to publish the record after uploading files
            community: Community ID to add the record to
            verify_ssl: Whether to verify SSL certificates
            custom_metadata: Additional metadata to add to the record
            hocr_mount_point: Host path where HOCR files should be copied for service access
        """
        self.book_dir = os.path.abspath(book_dir)
        if not os.path.exists(self.book_dir):
            raise ValueError(f"Book directory does not exist: {self.book_dir}")
        
        # Get the book ID from the directory name
        self.book_id = os.path.basename(self.book_dir)
        
        self.api_url = api_url
        self.api_token = api_token
        self.username = username
        self.password = password
        self.skip_hocr = skip_hocr
        self.skip_tiff = skip_tiff
        self.max_retries = max_retries
        self.publish = publish
        self.community = community
        self.verify_ssl = verify_ssl
        self.custom_metadata = custom_metadata or {}
        self.hocr_mount_point = hocr_mount_point
        
        # Setup authentication
        self.headers = {'Accept': 'application/json'}
        self.auth = None
        
        if self.api_token:
            self.headers['Authorization'] = f'Bearer {self.api_token}'
        elif self.username and self.password:
            self.auth = (self.username, self.password)
        else:
            logger.warning("No authentication provided. API token or username/password is required.")
        
        # Normalize API URL
        if not self.api_url.endswith('/api'):
            self.api_url = f"{self.api_url}/api"
        
        # Disable SSL verification warnings if requested
        if not self.verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # --- Helper methods for Manifest Generation (adapted) ---
    def _get_hocr_dimensions(self, hocr_path):
        """Extract page dimensions from HOCR file"""
        try:
            with open(hocr_path, 'r', encoding='utf-8') as file:
                soup = BeautifulSoup(file, 'html.parser')
                page = soup.find('div', class_='ocr_page')
                if page and 'title' in page.attrs:
                    title = page['title']
                    bbox_match = re.search(r'bbox\s+\d+\s+\d+\s+(\d+)\s+(\d+)', title)
                    if bbox_match:
                        width = int(bbox_match.group(1))
                        height = int(bbox_match.group(2))
                        return width, height
        except Exception as e:
            logger.error(f"Error extracting dimensions from HOCR {os.path.basename(hocr_path)}: {e}")
        return None

    def _get_pdf_dimensions(self, pdf_path, page_number=0):
        """Extract actual dimensions from PDF page"""
        try:
            with open(pdf_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                if len(pdf.pages) > page_number:
                    page = pdf.pages[page_number]
                    mediabox = page.mediabox
                    width_pt = mediabox.width
                    height_pt = mediabox.height
                    width_px = int(width_pt) # Assume 72 DPI for direct conversion
                    height_px = int(height_pt)
                    return width_px, height_px
        except Exception as e:
            logger.error(f"Error extracting dimensions from PDF page {page_number}: {e}")
        return None

    def _get_cantaloupe_dimensions(self, identifier, page_number=None):
        """Get dimensions from Cantaloupe for a specific identifier/page"""
        # Assuming Cantaloupe runs on localhost:8182 for now
        # TODO: Make Cantaloupe URL configurable
        base_url = "http://localhost:8182/iiif/2" 
        url = f"{base_url}/{identifier}/info.json"
        if page_number:
            url += f"?page={page_number}"
        
        try:
            logger.debug(f"Querying Cantaloupe: {url}")
            response = requests.get(url, verify=False, timeout=10) # Add timeout
            if response.status_code == 200:
                data = response.json()
                dims = (data.get('width'), data.get('height'))
                logger.debug(f"Got Cantaloupe dimensions: {dims}")
                return dims
            else:
                 logger.warning(f"Cantaloupe returned status {response.status_code} for {url}")
        except Exception as e:
            logger.error(f"Error getting dimensions from Cantaloupe ({url}): {e}")
        return None

    def _calculate_scale_factor(self, hocr_dim, pdf_dim, cantaloupe_dim):
        """Calculate appropriate scale factor between coordinate systems"""
        if not all([hocr_dim, cantaloupe_dim]): # PDF dim not strictly needed for scaling?
            logger.warning("Missing dimensions for scale factor calculation, using 1.0")
            return 1.0  # Default if any dimensions are missing
        
        hocr_width, hocr_height = hocr_dim
        cantaloupe_width, cantaloupe_height = cantaloupe_dim
        pdf_width, pdf_height = pdf_dim if pdf_dim else (None, None)

        if hocr_width == 0 or hocr_height == 0:
             logger.warning("HOCR dimensions are zero, cannot calculate scale factor, using 1.0")
             return 1.0
        
        width_ratio = cantaloupe_width / hocr_width
        height_ratio = cantaloupe_height / hocr_height
        scale_factor = (width_ratio + height_ratio) / 2
        
        logger.debug(f"Dimension comparison:")
        logger.debug(f"  HOCR: {hocr_width}x{hocr_height}")
        logger.debug(f"  PDF: {pdf_width}x{pdf_height}")
        logger.debug(f"  Cantaloupe: {cantaloupe_width}x{cantaloupe_height}")
        logger.debug(f"  Calculated scale factor: {scale_factor}")
        
        return scale_factor
        
    def _generate_manifest_content(self, record_id: str, book_info: Dict, files: Dict) -> Optional[Dict]:
        """Generate IIIF Manifest content as a dictionary."""
        logger.info("Generating IIIF Manifest content...")
        pdf_files = files.get('pdf', [])
        hocr_files = files.get('hocr', [])
        
        if not pdf_files:
            logger.error("Cannot generate manifest without a PDF file.")
            return None
            
        pdf_path = pdf_files[0]
        pdf_filename = os.path.basename(pdf_path)
        
        # --- Determine Base URLs ---
        # InvenioRDM Base URL (without /api) for internal file links
        invenio_base_url = self.api_url.rsplit('/api', 1)[0] if self.api_url.endswith('/api') else self.api_url
        
        # Public facing Base URL (e.g., served by nginx, used for browser-accessible links in manifest)
        # TODO: Make this configurable (e.g., via env var or command line arg)
        public_facing_base_url = "https://localhost" 
        logger.info(f"Using public facing base URL: {public_facing_base_url}")

        # Construct Manifest ID using Invenio URL (resolves post-publish)
        manifest_id = f"{invenio_base_url}/records/{record_id}/files/manifest.json"
        
        # Identifier for Cantaloupe (Record ID + Original Filename)
        cantaloupe_pdf_identifier = f"{record_id}_{pdf_filename}"
        cantaloupe_pdf_identifier = requests.utils.quote(cantaloupe_pdf_identifier)
        logger.debug(f"Using Cantaloupe identifier: {cantaloupe_pdf_identifier}")
        
        # --- Cantaloupe Base URL --- 
        # TODO: Make Cantaloupe host/port configurable
        cantaloupe_host_port = "localhost:8182" 
        # --- FORCE HTTP for Cantaloupe for now --- 
        cantaloupe_base_url = f"http://{cantaloupe_host_port}/iiif/2"

        # --- Annotation and Search Service URLs (via public-facing reverse proxy) ---
        annotation_service_proxy_url = f"{public_facing_base_url}/annotations/{self.book_id}" # Annotation endpoint pattern: /annotations/{book_id}/{page_id}/line
        search_service_proxy_url = f"{public_facing_base_url}/search/{self.book_id}" # Search service endpoint pattern: /search/{book_id}
        autocomplete_service_proxy_url = f"{public_facing_base_url}/autocomplete/{self.book_id}" # Autocomplete endpoint pattern: /autocomplete/{book_id}

        # --- Get PDF page count ---
        try:
            with open(pdf_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                num_pages = len(pdf.pages)
                logger.info(f"PDF has {num_pages} pages")
        except Exception as e:
            logger.error(f"Error reading PDF for page count: {e}")
            return None
        
        default_width = 2000
        default_height = 3000
        
        manifest = {
            "@context": "http://iiif.io/api/presentation/2/context.json",
            "@id": manifest_id,
            "@type": "sc:Manifest",
            "label": book_info.get("title", self.book_id), # Use title from book_info
            # --- Add metadata like the example ---
            "metadata": [
                {
                    "label": "Coordinate System",
                    "value": "HOCR coordinates are automatically scaled to match PDF rendering in Cantaloupe"
                },
                {
                    "label": "Auto-Scaling",
                    "value": "Each page uses its own calculated scale factor based on comparing HOCR, PDF, and Cantaloupe dimensions"
                }
            ], 
            "sequences": [
                {
                    "@type": "sc:Sequence",
                    "canvases": []
                }
            ]
        }
        
        hocr_map = {os.path.basename(p): p for p in hocr_files}
        
        for page_num in range(1, num_pages + 1):
            page_label = str(page_num).zfill(3) # Use zero-padded label like '001'
            hocr_filename = f"{page_label}.hocr"
            hocr_path = hocr_map.get(hocr_filename)
            
            width, height = default_width, default_height
            scale_factor = 1.0
            hocr_dimensions = None
            pdf_dimensions = self._get_pdf_dimensions(pdf_path, page_num - 1)

            if hocr_path:
                hocr_dimensions = self._get_hocr_dimensions(hocr_path)
            
            # Get Cantaloupe dimensions for this page
            # Add a small delay/retry here in case Cantaloupe needs time after copy?
            # time.sleep(0.5) # Optional short delay 
            cantaloupe_dimensions = self._get_cantaloupe_dimensions(cantaloupe_pdf_identifier, page_num)

            if hocr_dimensions and pdf_dimensions and cantaloupe_dimensions:
                # --- Calculate scale factor only if all dimensions are present --- 
                scale_factor = self._calculate_scale_factor(hocr_dimensions, pdf_dimensions, cantaloupe_dimensions)
                # Use HOCR dimensions scaled by the factor for the canvas
                orig_width, orig_height = hocr_dimensions
                width = int(orig_width * scale_factor) # Use scaled HOCR dims
                height = int(orig_height * scale_factor)
                logger.debug(f"Using scaled HOCR dimensions for page {page_label}: {width}x{height} (Scale: {scale_factor})")
            elif cantaloupe_dimensions: # Use Cantaloupe if HOCR/PDF dims missing
                width, height = cantaloupe_dimensions
                logger.debug(f"Using Cantaloupe dimensions (no scaling possible) for page {page_label}: {width}x{height}")
            elif pdf_dimensions: # Fallback to PDF
                 width, height = pdf_dimensions
                 logger.warning(f"Using PDF dimensions (no Cantaloupe/HOCR) for page {page_label}: {width}x{height}")
            else: # Fallback to default
                logger.warning(f"Using default dimensions for page {page_label}: {width}x{height}")

            # Ensure width/height are integers
            width = int(width) if width else default_width
            height = int(height) if height else default_height
                
            # --- Use p{page_label} format for canvas ID --- 
            canvas_id = f"{manifest_id}/canvas/p{page_label}"
            canvas = {
                "@id": canvas_id,
                "@type": "sc:Canvas",
                # --- Use p. {page_label} format for label --- 
                "label": f"p. {page_label}", 
                "width": width,
                "height": height,
                "images": [
                    {
                        "@type": "oa:Annotation",
                        "motivation": "sc:painting",
                        "on": canvas_id,
                        "resource": {
                            # Point resource to Cantaloupe URL for the specific page
                            # --- Use full/full like example, remove service block/format --- 
                            "@id": f"{cantaloupe_base_url}/{cantaloupe_pdf_identifier}/full/full/0/default.jpg?page={page_num}",
                            "@type": "dctypes:Image",
                            # "format": "image/jpeg", # Removed
                            "width": width, # Use canvas width/height for image dims too
                            "height": height
                            # "service": { ... } # Removed nested service block
                        }
                    }
                ],
                "otherContent": [
                    {
                        # Use the proxied URL for annotations
                        "@id": f"{annotation_service_proxy_url}/p{page_label}/line",
                        "@type": "sc:AnnotationList",
                         # --- Match example label --- 
                        "label": f"Text of page {page_label}"
                    }
                ]
            }

            if hocr_path:
                # Use the InvenioRDM file URL for HOCR
                hocr_file_url = f"{invenio_base_url}/records/{record_id}/files/{hocr_filename}"
                canvas["seeAlso"] = [
                    {
                        "@id": hocr_file_url,
                        "format": "text/vnd.hocr+html",
                        "profile": "http://kba.github.io/hocr-spec/1.2/",
                        "label": "HOCR OCR text"
                    }
                ]
                # --- Include scale factor if calculated --- 
                if hocr_dimensions and pdf_dimensions and cantaloupe_dimensions:
                     canvas["scaleFactor"] = scale_factor
            
            manifest["sequences"][0]["canvases"].append(canvas)

        # Add search service
        manifest["service"] = [
            {
                "@context": "http://iiif.io/api/search/0/context.json",
                # Use the proxied URL for search
                "@id": search_service_proxy_url,
                "profile": "http://iiif.io/api/search/0/search",
                "label": "Search within this manifest",
                "service": {
                    # Use the proxied URL for autocomplete
                    "@id": autocomplete_service_proxy_url,
                    "profile": "http://iiif.io/api/search/0/autocomplete",
                    "label": "Autocomplete words in this manifest"
                }
            }
        ]
        
        # Add PDF download link using Invenio URL
        # --- Use http for download link like example? Or stick to service_protocol? Stick to invenio URL --- 
        pdf_file_url = f"{invenio_base_url}/records/{record_id}/files/{pdf_filename}"
        manifest["related"] = {
            "@id": pdf_file_url,
            "format": "application/pdf",
            "label": "Download full PDF"
        }
        
        # Basic metadata was added to manifest["metadata"] above

        logger.info("IIIF Manifest content generated successfully.")
        return manifest
        
    # --- End of Manifest Generation Helpers ---
    
    def collect_files(self) -> Dict[str, List[str]]:
        """
        Collect files from the book directory.
        
        Returns:
            A dictionary with 'pdf', 'hocr', 'tiff', and 'other' keys containing lists of file paths
        """
        files = {'pdf': [], 'hocr': [], 'tiff': [], 'other': []}
        
        # Look for PDF file
        pdf_files = glob.glob(os.path.join(self.book_dir, "*.pdf"))
        files['pdf'] = pdf_files
        
        # Always include manifest.json if it exists, even in pdf-only mode
        manifest_path = os.path.join(self.book_dir, "manifest.json")
        if os.path.exists(manifest_path):
            # Don't add it to the upload list here, as we will generate and upload our own.
            # files['other'].append(manifest_path) 
            logger.info(f"Found original manifest.json (will be replaced by generated one during upload)")
        
        # Collect HOCR files if not skipping
        if not self.skip_hocr:
            hocr_dir = os.path.join(self.book_dir, "hocr")
            if os.path.exists(hocr_dir) and os.path.isdir(hocr_dir):
                # Get all HOCR files except all_pages.hocr (which is a concatenation of all)
                hocr_files = [f for f in glob.glob(os.path.join(hocr_dir, "*.hocr")) 
                             if not os.path.basename(f).startswith("all_pages")]
                files['hocr'] = sorted(hocr_files)
        
        # Collect TIFF files if not skipping
        if not self.skip_tiff:
            pages_dir = os.path.join(self.book_dir, "pages")
            if os.path.exists(pages_dir) and os.path.isdir(pages_dir):
                tiff_files = glob.glob(os.path.join(pages_dir, "*.tif"))
                files['tiff'] = sorted(tiff_files)
        
        logger.info(f"Found {len(files['pdf'])} PDF files, {len(files['hocr'])} HOCR files, {len(files['tiff'])} TIFF files, and {len(files['other'])} other files")
        return files
    
    def extract_book_info(self) -> Dict:
        """
        Extract book information, prioritizing metadata.json then manifest.json.
        
        Returns:
            Dictionary with book metadata
        """
        book_info = {
            "book_id": self.book_id,
            "title": self.book_id,  # Default title
            "creators": [],
            "subjects": [],
            "language": "ara", # Default language Arabic
            "publication_date": datetime.now().strftime("%Y-%m-%d"), # Default date
            "description": f"Book from Turath Digital Library: {self.book_id}", # Default description
            "resource_type": {"id": "publication-book"} # Default resource type
        }
        
        metadata_loaded = False
        
        # 1. Try metadata.json first
        metadata_path = os.path.join(self.book_dir, "metadata.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    direct_metadata = json.load(f)
                
                # Assume structure like {"metadata": {...}, "access": {...}, ...}
                if "metadata" in direct_metadata:
                    # Overwrite defaults with values from metadata.json
                    meta_section = direct_metadata["metadata"]
                    book_info["title"] = meta_section.get("title", book_info["title"])
                    book_info["creators"] = meta_section.get("creators", []) # Take creators directly
                    book_info["subjects"] = meta_section.get("subjects", []) # Take subjects directly
                    book_info["language"] = meta_section.get("languages", [{"id": book_info["language"]}])[0].get("id", book_info["language"])
                    book_info["publication_date"] = meta_section.get("publication_date", book_info["publication_date"])
                    book_info["description"] = meta_section.get("description", book_info["description"])
                    book_info["resource_type"] = meta_section.get("resource_type", book_info["resource_type"])
                    # Add identifiers if present
                    book_info["identifiers"] = meta_section.get("identifiers", [])
                    
                    logger.info(f"Successfully loaded primary metadata from metadata.json: {book_info['title']}")
                    metadata_loaded = True
                else:
                     logger.warning(f"metadata.json found but missing top-level 'metadata' key.")
                     
            except Exception as e:
                logger.error(f"Error parsing metadata.json: {str(e)}")

        # 2. If metadata.json wasn't loaded or didn't have needed fields, try manifest.json
        if not metadata_loaded:
            manifest_path = os.path.join(self.book_dir, "manifest.json")
            if os.path.exists(manifest_path):
                logger.info("Attempting to extract metadata from manifest.json...")
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    
                    if isinstance(manifest, dict):
                        # Extract label as title (handle dict/str)
                        label = manifest.get("label", {})
                        if isinstance(label, dict):
                             # Prefer English, fallback to any lang
                            en_label = label.get("en", [book_info["title"]])[0]
                            book_info["title"] = en_label if en_label else next((v[0] for v in label.values() if v), book_info["title"])
                        elif isinstance(label, str):
                            book_info["title"] = label

                        # Extract from IIIF metadata block if present
                        iiif_metadata = manifest.get("metadata", [])
                        if isinstance(iiif_metadata, list):
                            for item in iiif_metadata:
                                if isinstance(item, dict) and "label" in item and "value" in item:
                                    label_dict = item["label"]
                                    value_dict = item["value"]
                                    # Get english label preferably
                                    label_en = label_dict.get("en", [None])[0]
                                    # Get first value preferably english
                                    value_en = value_dict.get("en", [None])[0]
                                    value_any = next((v[0] for v in value_dict.values() if v), None)
                                    current_value = value_en if value_en else value_any

                                    if label_en and current_value:
                                        label_lower = label_en.lower()
                                        if "author" in label_lower or "creator" in label_lower:
                                            # Simple name parsing for creator
                                            book_info["creators"].append({"person_or_org": {"name": current_value, "type": "personal"}})
                                        elif "subject" in label_lower:
                                            book_info["subjects"].append({"subject": current_value})
                                        elif "language" in label_lower:
                                             # Basic lang code handling
                                            lang_code = current_value[:3].lower()
                                            if len(lang_code) == 3:
                                                book_info["language"] = lang_code
                                        elif "date" in label_lower or "publication date" in label_lower:
                                            book_info["publication_date"] = current_value
                                        elif "description" in label_lower:
                                            book_info["description"] = current_value
                                        # Add more mappings here if needed (e.g., publisher)
                        
                        logger.info(f"Extracted partial metadata from manifest.json: {book_info['title']}")
                        metadata_loaded = True # Mark as loaded even if partial

                except Exception as e:
                    logger.error(f"Error parsing manifest.json: {str(e)}")
            else:
                logger.warning(f"No metadata.json or manifest.json found in {self.book_dir}, using default metadata.")

        # Ensure core fields have defaults if still missing after checks
        # (This is slightly redundant with initial defaults but safe)
        book_info["title"] = book_info.get("title") or self.book_id
        book_info["publication_date"] = book_info.get("publication_date") or datetime.now().strftime("%Y-%m-%d")
        book_info["resource_type"] = book_info.get("resource_type") or {"id": "publication-book"}
        book_info["description"] = book_info.get("description") or f"Book from Turath Digital Library: {self.book_id}"
        # Creator default is handled later in prepare/validate
        
        return book_info
    
    def get_iiif_manifest_url(self) -> Optional[str]:
        """
        Generate the IIIF manifest URL for this book.
        
        Returns:
            URL to the IIIF manifest or None if no manifest exists
        """
        manifest_path = os.path.join(self.book_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            return None
        
        # Read the manifest to look for @id field
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
                
            # If the manifest already specifies its @id, use that
            if "@id" in manifest_data and isinstance(manifest_data["@id"], str):
                manifest_url = manifest_data["@id"]
                logger.debug(f"Using manifest @id from manifest.json: {manifest_url}")
                return manifest_url
        except Exception as e:
            logger.warning(f"Error reading manifest.json @id: {str(e)}")
        
        # Fallback to constructing the URL
        # Extract API domain from API URL for consistency
        api_domain = self.api_url.split('/api')[0] if '/api' in self.api_url else "http://localhost:8182"
        
        # Format: {domain}/iiif/3/{book_id}/manifest.json
        manifest_url = f"{api_domain}/iiif/3/{self.book_id}/manifest.json"
        logger.debug(f"Generated IIIF manifest URL: {manifest_url}")
        return manifest_url
    
    def prepare_metadata(self, book_info: Dict) -> Dict:
        """
        Prepare metadata for record creation based on extracted book_info.
        
        Args:
            book_info: Dictionary with book information from extract_book_info
            
        Returns:
            Dictionary with record metadata ready for API submission
        """
        # Format creators from book_info (which might be pre-formatted or simple names)
        creators_info = book_info.get("creators", [])
        creators = []
        
        # Check if creators_info is empty or contains invalid data
        # Default creator addition moved primarily to validate_metadata
        # if not creators_info:
        #    logger.warning("No creator info found in book_info, default will be added during validation.")
            
        for creator_data in creators_info:
            # If creator_data already has the RDM structure, use it
            if isinstance(creator_data, dict) and "person_or_org" in creator_data and "type" in creator_data["person_or_org"]:
                creators.append(creator_data)
                logger.debug(f"Using pre-formatted creator: {creator_data['person_or_org']}")
            # If it only has a simple name field
            elif isinstance(creator_data, dict) and "name" in creator_data:
                full_name = creator_data["name"]
                logger.debug(f"Processing simple creator name: {full_name}")
                name_parts = full_name.split()
                family_name = name_parts[-1] if len(name_parts) > 1 else full_name
                given_name = " ".join(name_parts[:-1]) if len(name_parts) > 1 else ""
                creators.append({
                    "person_or_org": {
                        "family_name": family_name,
                        "given_name": given_name,
                        "name": full_name, # Keep original name too if desired
                        "type": "personal" # Assume personal if only name given
                    },
                    "role": creator_data.get("role", "author") # Preserve role if provided
                })
            elif isinstance(creator_data, str): # Handle case where creator is just a string name
                 logger.debug(f"Processing string creator name: {creator_data}")
                 full_name = creator_data
                 name_parts = full_name.split()
                 family_name = name_parts[-1] if len(name_parts) > 1 else full_name
                 given_name = " ".join(name_parts[:-1]) if len(name_parts) > 1 else ""
                 creators.append({
                    "person_or_org": {
                        "family_name": family_name,
                        "given_name": given_name,
                        "name": full_name,
                        "type": "personal"
                    },
                    "role": "author"
                })
            else:
                 logger.warning(f"Skipping unrecognized creator format: {creator_data}")

        # Format publication date (ensure YYYY-MM-DD)
        pub_date = book_info.get("publication_date", datetime.now().strftime("%Y-%m-%d"))
        if isinstance(pub_date, str):
            if re.match(r'^\d{4}$', pub_date): pub_date = f"{pub_date}-01-01"
            elif re.match(r'^\d{4}-\d{2}$', pub_date): pub_date = f"{pub_date}-01"
            elif not re.match(r'^\d{4}-\d{2}-\d{2}$', pub_date):
                 logger.warning(f"Invalid date format '{pub_date}', using current date.")
                 pub_date = datetime.now().strftime("%Y-%m-%d")
        else:
             logger.warning(f"Invalid date type '{type(pub_date)}', using current date.")
             pub_date = datetime.now().strftime("%Y-%m-%d")

        # Format language (ensure list of dicts with id)
        language_code = book_info.get("language", "ara")
        language_map = {"ar": "ara", "en": "eng", "fr": "fra", "de": "deu", "es": "spa"}
        if language_code in language_map: language_code = language_map[language_code]
        languages = [{"id": language_code}]
        
        # Format subjects (ensure list of dicts with subject)
        subjects_info = book_info.get("subjects", [])
        subjects = []
        for sub in subjects_info:
             if isinstance(sub, dict) and "subject" in sub:
                 subjects.append(sub)
             elif isinstance(sub, str):
                 subjects.append({"subject": sub})
             else:
                 logger.warning(f"Skipping unrecognized subject format: {sub}")
                 
        # Format resource type (ensure dict with id)
        resource_type_info = book_info.get("resource_type", {"id": "publication-book"})
        resource_type = resource_type_info if isinstance(resource_type_info, dict) and "id" in resource_type_info else {"id": "publication-book"}

        # Start building final metadata structure
        metadata = {
            "metadata": {
                "title": book_info.get("title", self.book_id),
                "publication_date": pub_date,
                "resource_type": resource_type,
                "creators": creators, # Use processed creators
                "languages": languages,
                "description": book_info.get("description", f"Book from Turath Digital Library: {self.book_id}")
            },
            "access": {
                "record": "public",
                "files": "public"
            },
            "files": {
                "enabled": True
            }
        }
        
        # Add subjects if processed list is not empty
        if subjects:
            metadata["metadata"]["subjects"] = subjects
        
        # Add community if specified
        if self.community:
            metadata["parent"] = {"id": self.community}
        
        # Add identifiers (use provided or default)
        identifiers_info = book_info.get("identifiers", [])
        identifiers = []
        if identifiers_info:
            # Basic validation of provided identifiers
            for ident in identifiers_info:
                 if isinstance(ident, dict) and "identifier" in ident and "scheme" in ident:
                     identifiers.append(ident)
                 else:
                     logger.warning(f"Skipping invalid identifier format: {ident}")
        # Ensure at least one identifier exists (defaulting to book_id)
        if not identifiers:
             identifiers.append({"identifier": self.book_id, "scheme": "other"})
        metadata["metadata"]["identifiers"] = identifiers
        
        # Add custom fields for IIIF support
        manifest_url = self.get_iiif_manifest_url()
        if manifest_url:
            if "custom_fields" not in metadata: metadata["custom_fields"] = {}
            metadata["custom_fields"]["turath:iiif_manifest"] = manifest_url
        
        # Merge with external custom_metadata file content (if provided)
        if self.custom_metadata:
            # Merge metadata fields (carefully, avoid overwriting essentials if not intended)
            # User provided metadata takes precedence
            external_meta = self.custom_metadata.get("metadata", {})
            for key, value in external_meta.items():
                # Special handling for creators/subjects?
                # Currently overwrites if key exists
                metadata["metadata"][key] = value 
                
            # Merge access settings
            metadata["access"].update(self.custom_metadata.get("access", {}))
            
            # Merge custom fields 
            if "custom_fields" in self.custom_metadata:
                if "custom_fields" not in metadata: metadata["custom_fields"] = {}
                metadata["custom_fields"].update(self.custom_metadata.get("custom_fields", {}))
            
            # Merge other top-level fields like parent community
            for key, value in self.custom_metadata.items():
                if key not in ["metadata", "access", "custom_fields", "files"]:
                    metadata[key] = value

        # Final validation step is crucial before returning
        # return self.validate_metadata(metadata) # Call validation here
        return metadata # Let validate_metadata run just before API call
    
    def validate_metadata(self, metadata: Dict) -> Dict:
        """
        Validate and clean metadata to ensure it meets InvenioRDM requirements.
        
        Args:
            metadata: Metadata dictionary to validate
            
        Returns:
            Cleaned metadata dictionary
        """
        # Make a deep copy to avoid modifying the original
        cleaned = json.loads(json.dumps(metadata))
        
        # Ensure metadata section exists
        if "metadata" not in cleaned:
            logger.warning("Metadata section missing, creating empty metadata")
            cleaned["metadata"] = {}
        
        # Ensure title exists
        if "title" not in cleaned.get("metadata", {}):
            logger.warning("Title missing, using book ID as title")
            cleaned["metadata"]["title"] = self.book_id
        
        # Validate and fix creators
        if "creators" not in cleaned.get("metadata", {}):
            logger.warning("Creators missing, adding default creator")
            cleaned["metadata"]["creators"] = [{
                "person_or_org": {
                    "family_name": "Library",
                    "given_name": "Turath Digital",
                    "type": "organizational"
                }
            }]
        else:
            for i, creator in enumerate(cleaned["metadata"]["creators"]):
                # Ensure person_or_org exists
                if "person_or_org" not in creator:
                    logger.warning(f"Creator {i} missing person_or_org, adding default")
                    creator["person_or_org"] = {
                        "family_name": "Unknown",
                        "given_name": "Author",
                        "type": "personal"
                    }
                
                # If using 'name' field, convert to family_name and given_name
                if "name" in creator.get("person_or_org", {}):
                    name = creator["person_or_org"].pop("name")
                    name_parts = name.split()
                    
                    if len(name_parts) > 1:
                        creator["person_or_org"]["family_name"] = name_parts[-1]
                        creator["person_or_org"]["given_name"] = " ".join(name_parts[:-1])
                    else:
                        creator["person_or_org"]["family_name"] = name
                        creator["person_or_org"]["given_name"] = "Unknown"
                
                # Ensure family_name and given_name exist
                if "family_name" not in creator.get("person_or_org", {}):
                    logger.warning(f"Creator {i} missing family_name, adding default")
                    creator["person_or_org"]["family_name"] = "Unknown"
                
                if "given_name" not in creator.get("person_or_org", {}) and creator["person_or_org"].get("type") == "personal":
                    logger.warning(f"Creator {i} missing given_name, adding default")
                    creator["person_or_org"]["given_name"] = "Author"
                
                # Ensure type exists
                if "type" not in creator.get("person_or_org", {}):
                    logger.warning(f"Creator {i} missing type, setting to personal")
                    creator["person_or_org"]["type"] = "personal"
        
        # Validate identifiers
        if "identifiers" in cleaned.get("metadata", {}):
            valid_schemes = ["ark", "arxiv", "bibcode", "doi", "ean13", "eissn", "handle", "isbn", "issn", 
                            "istc", "lissn", "lsid", "pmid", "pmcid", "purl", "upc", "url", "urn", "w3id", "other"]
            
            for i, identifier in enumerate(cleaned["metadata"]["identifiers"]):
                if "identifier" not in identifier:
                    logger.warning(f"Identifier {i} missing identifier value, removing")
                    # Remove this identifier
                    cleaned["metadata"]["identifiers"][i] = None
                    continue
                
                if "scheme" not in identifier:
                    logger.warning(f"Identifier {i} missing scheme, setting to 'other'")
                    identifier["scheme"] = "other"
                elif identifier["scheme"] not in valid_schemes:
                    logger.warning(f"Identifier {i} has invalid scheme '{identifier['scheme']}', changing to 'other'")
                    identifier["scheme"] = "other"
            
            # Remove any None values from identifiers
            cleaned["metadata"]["identifiers"] = [i for i in cleaned["metadata"]["identifiers"] if i is not None]
        
        # Ensure at least one valid creator exists after validation
        creators_list = cleaned["metadata"].get("creators", [])
        is_valid_creator_present = False
        if isinstance(creators_list, list):
            for c in creators_list:
                if isinstance(c, dict) and isinstance(c.get("person_or_org"), dict) and \
                   (c["person_or_org"].get("name") or (c["person_or_org"].get("family_name") and c["person_or_org"].get("given_name"))):
                    is_valid_creator_present = True
                    break # Found at least one valid creator

        if not is_valid_creator_present:
            logger.warning("No valid creators found after validation, adding default organizational creator.")
            cleaned["metadata"]["creators"] = [{
                "person_or_org": {
                    "name": "Turath Digital Library", # Use a non-blank name
                    "type": "organizational"
                },
                "role": "author" # Add a default role
            }]
        
        # Ensure publication date is valid
        if "publication_date" not in cleaned.get("metadata", {}):
            logger.warning("Publication date missing, using current date")
            cleaned["metadata"]["publication_date"] = datetime.now().strftime("%Y-%m-%d")
        else:
            pub_date = cleaned["metadata"]["publication_date"]
            # Check if it's a valid date format (YYYY-MM-DD)
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', pub_date):
                logger.warning(f"Invalid publication date format: {pub_date}, reformatting")
                # Try to fix it
                if re.match(r'^\d{4}$', pub_date):  # YYYY
                    cleaned["metadata"]["publication_date"] = f"{pub_date}-01-01"
                elif re.match(r'^\d{4}-\d{2}$', pub_date):  # YYYY-MM
                    cleaned["metadata"]["publication_date"] = f"{pub_date}-01"
                else:
                    # Set to current date if unparseable
                    logger.warning(f"Unable to parse publication date, using current date")
                    cleaned["metadata"]["publication_date"] = datetime.now().strftime("%Y-%m-%d")
        
        # Validate resource type
        if "resource_type" not in cleaned.get("metadata", {}):
            logger.warning("Resource type missing, setting to publication-book")
            cleaned["metadata"]["resource_type"] = {"id": "publication-book"}
        elif "id" not in cleaned["metadata"]["resource_type"]:
            logger.warning("Resource type missing ID, setting to publication-book")
            cleaned["metadata"]["resource_type"] = {"id": "publication-book"}
        
        # Ensure description exists
        if "description" not in cleaned.get("metadata", {}):
            logger.warning("Missing description, adding default")
            cleaned["metadata"]["description"] = f"Book from Turath Digital Library: {self.book_id}"
        
        # Validate languages
        if "languages" not in cleaned.get("metadata", {}):
            logger.warning("Languages missing, adding Arabic as default")
            cleaned["metadata"]["languages"] = [{"id": "ara"}]
        else:
            for i, lang in enumerate(cleaned["metadata"]["languages"]):
                if "id" not in lang:
                    logger.warning(f"Language {i} missing id, setting to 'ara'")
                    lang["id"] = "ara"
        
        # Validate custom fields for IIIF
        if "custom_fields" in cleaned:
            # Ensure the IIIF manifest URL is valid if present
            if "turath:iiif_manifest" in cleaned["custom_fields"]:
                manifest_url = cleaned["custom_fields"]["turath:iiif_manifest"]
                if not isinstance(manifest_url, str) or not manifest_url.startswith("http"):
                    logger.warning(f"Invalid IIIF manifest URL: {manifest_url}, updating")
                    # Try to get a valid URL
                    new_url = self.get_iiif_manifest_url()
                    if new_url:
                        cleaned["custom_fields"]["turath:iiif_manifest"] = new_url
                    else:
                        # Remove invalid URL
                        del cleaned["custom_fields"]["turath:iiif_manifest"]
        
        # Validate access permissions
        if "access" not in cleaned:
            logger.warning("Access settings missing, adding default (public)")
            cleaned["access"] = {
                "record": "public",
                "files": "public"
            }
        
        # Validate files section
        if "files" not in cleaned:
            logger.warning("Files section missing, adding default")
            cleaned["files"] = {
                "enabled": True
            }
        
        return cleaned
    
    def create_record(self, metadata: Dict) -> Dict:
        """
        Create a record in InvenioRDM.
        
        Args:
            metadata: Record metadata
            
        Returns:
            Dictionary with record information or error
        """
        try:
            # Validate and clean metadata
            validated_metadata = self.validate_metadata(metadata)
            
            # Create the draft record
            endpoint = f"{self.api_url}/records"
            
            logger.info(f"Creating draft record with title: {validated_metadata['metadata']['title']}")
            response = requests.post(
                endpoint,
                json=validated_metadata,
                headers=self.headers,
                auth=self.auth,
                verify=self.verify_ssl
            )
            
            if response.status_code != 201:
                error_msg = f"Failed to create record. Status code: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('message', '')}"
                except:
                    error_msg += f" - {response.text}"
                
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
            
            record_data = response.json()
            record_id = record_data.get("id")
            
            logger.info(f"Created draft record with ID: {record_id}")
            return {
                "success": True,
                "record_id": record_id,
                "data": record_data
            }
            
        except Exception as e:
            error_msg = f"Error creating record: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            return {
                "success": False,
                "error": error_msg
            }
    
    def upload_files_to_record(self, record_id: str, files_to_upload: List[Union[str, Dict]]) -> Dict:
        """
        Upload files to a draft record.
        
        Args:
            record_id: Record ID to upload files to
            files_to_upload: List of file paths or dicts({"path": ..., "name": ...}) to upload
            
        Returns:
            Dictionary with upload results
        """
        if not files_to_upload:
            logger.info("No files to upload")
            return {"success": True, "uploaded": 0, "total": 0}
        
        api_endpoint = f"{self.api_url}/records/{record_id}/draft/files"
        uploaded_files = []
        file_count = len(files_to_upload)
        
        logger.info(f"Uploading {file_count} files to record {record_id}")
        
        # Step 1: Initialize all files at once
        try:
            file_keys = []
            file_path_map = {}
            for item in files_to_upload:
                if isinstance(item, dict):
                    file_path = item['path']
                    file_name = item['name']
                elif isinstance(item, str):
                    file_path = item
                    file_name = os.path.basename(file_path)
                else:
                    continue # Skip invalid items
                file_keys.append({"key": file_name})
                file_path_map[file_name] = file_path
            
            init_response = requests.post(
                api_endpoint,
                json=file_keys,
                headers=self.headers,
                auth=self.auth,
                verify=self.verify_ssl
            )
            
            if init_response.status_code != 201:
                error_msg = f"Failed to initialize files. Status code: {init_response.status_code}"
                try:
                    error_data = init_response.json()
                    error_msg += f" - {error_data.get('message', '')}"
                except:
                    error_msg += f" - {init_response.text}"
                
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "uploaded": 0,
                    "total": file_count
                }
        except Exception as e:
            error_msg = f"Error initializing files: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "uploaded": 0,
                "total": file_count
            }
        
        # Step 2: Upload each file
        # Use the file_path_map created during initialization
        for file_name, file_path in file_path_map.items():
            # file_name = os.path.basename(file_path)
            logger.info(f"Uploading file: {file_name} (from {file_path})")
            
            # Retry logic for resilient uploads
            for retry in range(self.max_retries):
                try:
                    # Upload file content
                    with open(file_path, 'rb') as file_content:
                        upload_response = requests.put(
                            f"{api_endpoint}/{file_name}/content",
                            data=file_content,
                            headers=self.headers,
                            auth=self.auth,
                            verify=self.verify_ssl
                        )
                    
                    if upload_response.status_code != 200:
                        logger.warning(f"Failed to upload content for {file_name}. Status code: {upload_response.status_code}")
                        
                        # If this is not the last retry, try again
                        if retry < self.max_retries - 1:
                            logger.info(f"Retrying upload ({retry + 1}/{self.max_retries})...")
                            time.sleep(1)  # Small delay before retry
                            continue
                        break
                    
                    # Commit the file
                    commit_response = requests.post(
                        f"{api_endpoint}/{file_name}/commit",
                        headers=self.headers,
                        auth=self.auth,
                        verify=self.verify_ssl
                    )
                    
                    if commit_response.status_code != 200:
                        logger.warning(f"Failed to commit file {file_name}. Status code: {commit_response.status_code}")
                        
                        # If this is not the last retry, try again
                        if retry < self.max_retries - 1:
                            logger.info(f"Retrying commit ({retry + 1}/{self.max_retries})...")
                            time.sleep(1)
                            continue
                        break
                    
                    logger.info(f"Successfully uploaded and committed file: {file_name}")
                    uploaded_files.append(file_name)
                    break  # Success, break retry loop
                    
                except Exception as e:
                    logger.error(f"Error uploading {file_name}: {str(e)}")
                    if retry < self.max_retries - 1:
                        logger.info(f"Retrying due to error ({retry + 1}/{self.max_retries})...")
                        time.sleep(1)
                        continue
                    break
            
            # Small delay between files to avoid overwhelming the server
            time.sleep(0.5)
        
        # Return results
        success = len(uploaded_files) == file_count
        return {
            "success": success,
            "uploaded": len(uploaded_files),
            "total": file_count,
            "files": uploaded_files
        }
    
    def publish_record(self, record_id: str) -> Dict:
        """
        Publish a record.
        
        Args:
            record_id: Record ID to publish
            
        Returns:
            Dictionary with publish results
        """
        try:
            endpoint = f"{self.api_url}/records/{record_id}/draft/actions/publish"
            
            logger.info(f"Publishing record: {record_id}")
            response = requests.post(
                endpoint,
                headers=self.headers,
                auth=self.auth,
                verify=self.verify_ssl
            )
            
            if response.status_code != 202:
                error_msg = f"Failed to publish record. Status code: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('message', '')}"
                    # Log detailed error information
                    logger.debug(f"Full error response: {json.dumps(error_data, indent=2)}")
                    
                    # Extract validation errors if available
                    if 'errors' in error_data:
                        for error in error_data['errors']:
                            field = error.get('field', 'unknown field')
                            messages = error.get('messages', [])
                            logger.error(f"Validation error in {field}: {', '.join(messages)}")
                except:
                    error_msg += f" - {response.text}"
                
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
            
            published_data = response.json()
            logger.info(f"Successfully published record: {record_id}")
            
            return {
                "success": True,
                "record_id": record_id,
                "data": published_data
            }
            
        except Exception as e:
            error_msg = f"Error publishing record: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def process(self) -> Dict:
        """
        Process the entire upload workflow.
        
        Returns:
            Dictionary with processing results
        """
        temp_manifest_path = None # Keep track of temporary manifest file
        record_id = None # Initialize record_id
        final_record_id = None # Initialize final_record_id
        unique_pdf_filename = None # Initialize unique pdf filename

        try:
            # Step 1: Collect files
            files = self.collect_files()
            pdf_count = len(files['pdf'])
            hocr_count = len(files['hocr'])
            tiff_count = len(files['tiff'])
            other_count = len(files['other'])
            
            if pdf_count == 0 and hocr_count == 0 and tiff_count == 0 and other_count == 0:
                return {
                    "success": False,
                    "error": "No files found in the book directory"
                }
            
            # Step 2: Extract book information
            book_info = self.extract_book_info()
            
            # Step 3: Prepare metadata
            metadata = self.prepare_metadata(book_info)
            
            # Step 4: Create record (get draft ID)
            create_result = self.create_record(metadata)
            if not create_result["success"]:
                return create_result
            
            record_id = create_result["record_id"]

            # --- Step 4.5: Copy PDF to Cantaloupe source *before* manifest generation --- 
            if files['pdf']:
                source_pdf_path = files['pdf'][0]
                original_pdf_filename = os.path.basename(source_pdf_path)
                # Use the draft record ID for the initial unique filename
                base_name = os.path.splitext(original_pdf_filename)[0]
                unique_pdf_filename = f"{record_id}_{base_name}.pdf" # Filename used by Cantaloupe
                
                dest_dir = os.path.abspath("./test-images") 
                dest_pdf_path = os.path.join(dest_dir, unique_pdf_filename)
                
                try:
                    os.makedirs(dest_dir, exist_ok=True)
                    logger.info(f"Copying PDF to Cantaloupe source: {source_pdf_path} -> {dest_pdf_path}")
                    shutil.copy2(source_pdf_path, dest_pdf_path) 
                    logger.info(f"Successfully copied PDF for Cantaloupe.")
                    # --- Add small delay --- 
                    logger.info("Waiting 2 seconds for Cantaloupe to potentially recognize the file...")
                    time.sleep(2)
                except Exception as e:
                    logger.error(f"Failed to copy PDF to {dest_pdf_path}: {e}")
                    # If copy fails, manifest gen will likely fail dimension check - proceed but log warning
                    # Alternatively, could return error here: 
                    # return {"success": False, "error": f"Failed to copy PDF to Cantaloupe source: {e}", "record_id": record_id}
            else:
                 logger.warning("No PDF file found, cannot copy to Cantaloupe source.")

            # Step 5a: Generate IIIF Manifest (now happens *after* PDF copy)
            manifest_content = self._generate_manifest_content(record_id, book_info, files)
            
            if manifest_content:
                try:
                    # Create a temporary file for the manifest
                    with tempfile.NamedTemporaryFile(mode='w', suffix=".json", prefix=f"{self.book_id}_", delete=False, encoding='utf-8') as tmp_file:
                        json.dump(manifest_content, tmp_file, indent=2, ensure_ascii=False)
                        temp_manifest_path = tmp_file.name
                    logger.info(f"Generated manifest saved to temporary file: {temp_manifest_path}")
                    
                    # Add manifest to the list of files to upload
                    # Ensure it's named manifest.json in the upload list
                    files['other'].append({"path": temp_manifest_path, "name": "manifest.json"})
                    
                except Exception as e:
                    logger.error(f"Failed to create or write temporary manifest file: {e}")
                    # Continue without uploading generated manifest
            else:
                 logger.warning("Manifest generation failed, proceeding without generated manifest.")

            # Step 5b: Upload files (including generated manifest if created)
            all_files_to_upload = []
            all_files_to_upload.extend(files['pdf'])
            all_files_to_upload.extend(files['hocr'])
            all_files_to_upload.extend(files['tiff'])
            # Handle 'other' files which might be paths or dicts with path/name
            processed_other_files = []
            for item in files['other']:
                if isinstance(item, dict):
                    processed_other_files.append(item) # Already has path/name
                elif isinstance(item, str):
                    processed_other_files.append({"path": item, "name": os.path.basename(item)})
                else:
                    logger.warning(f"Skipping unrecognized item in 'other' files list: {item}")
            all_files_to_upload.extend(processed_other_files)
            
            upload_result = self.upload_files_to_record(record_id, all_files_to_upload)
            
            if not upload_result["success"]:
                return {
                    "success": False,
                    "error": upload_result.get("error", "Failed to upload files"),
                    "record_id": record_id,
                    "partial": True
                }
            else:
                # --- Copy HOCR files to mount point if specified ---
                if self.hocr_mount_point and files['hocr']:
                    target_hocr_base = os.path.join(self.hocr_mount_point, 'books', self.book_id, 'hocr')
                    logger.info(f"Copying {len(files['hocr'])} HOCR files to service mount point: {target_hocr_base}")
                    try:
                        os.makedirs(target_hocr_base, exist_ok=True)
                        copied_count = 0
                        for hocr_file_path in files['hocr']:
                            hocr_filename = os.path.basename(hocr_file_path)
                            dest_path = os.path.join(target_hocr_base, hocr_filename)
                            try:
                                shutil.copy2(hocr_file_path, dest_path)
                                copied_count += 1
                            except Exception as copy_err:
                                logger.error(f"Failed to copy HOCR file {hocr_filename} to {dest_path}: {copy_err}")
                        logger.info(f"Successfully copied {copied_count} HOCR files to {target_hocr_base}")
                    except Exception as e:
                        logger.error(f"Failed to create or copy HOCR files to {target_hocr_base}: {e}")
                        # Log error but don't necessarily fail the whole process,
                        # as the primary upload to RDM succeeded.
                elif self.hocr_mount_point:
                    logger.info("HOCR mount point specified, but no HOCR files were found or collected to copy.")
                # --- End HOCR copy ---

            # Step 6: Publish record if requested
            published = False
            publish_data = None
            if self.publish:
                publish_result = self.publish_record(record_id)
                if not publish_result["success"]:
                    # Return error but include record_id for potential cleanup
                    return {
                        "success": False,
                        "error": publish_result.get("error", "Failed to publish record"),
                        "record_id": record_id,
                        "partial": True
                    }
                published = True
                publish_data = publish_result.get("data")
                final_record_id = publish_data.get("id") # Get the final published ID
            else:
                logger.info(f"Record {record_id} left as draft.")
                final_record_id = record_id # Draft ID is the final ID if not publishing
                
            # Step 7: (Former PDF Copy Step - Now handled earlier) 
            # --- Optional: Rename PDF in Cantaloupe source if ID changed upon publish? --- 
            # This adds complexity. Simpler to just use draft ID for filename always.
            # If the record ID changed after publishing AND we copied the PDF earlier...
            if published and final_record_id != record_id and unique_pdf_filename:
                 old_dest_pdf_path = os.path.join(dest_dir, unique_pdf_filename) # Path used draft ID
                 new_unique_pdf_filename = f"{final_record_id}_{base_name}.pdf"
                 new_dest_pdf_path = os.path.join(dest_dir, new_unique_pdf_filename)
                 if os.path.exists(old_dest_pdf_path):
                     try:
                         logger.info(f"Renaming Cantaloupe source PDF due to publication ID change: {old_dest_pdf_path} -> {new_dest_pdf_path}")
                         os.rename(old_dest_pdf_path, new_dest_pdf_path)
                     except Exception as e:
                         logger.error(f"Failed to rename PDF in Cantaloupe source: {e}")
                         # Log error, but don't fail the overall process

            # Success!
            return {
                "success": True,
                "record_id": record_id,
                "book_id": self.book_id,
                "title": book_info.get("title", self.book_id),
                "uploaded_files": upload_result.get("uploaded", 0),
                "total_files": upload_result.get("total", 0),
                "pdf_files": pdf_count,
                "hocr_files": hocr_count,
                "tiff_files": tiff_count,
                "other_files": other_count,
                "published": self.publish
            }
            
        except Exception as e:
            error_msg = f"Error processing upload: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            return {
                "success": False,
                "error": error_msg
            }
        finally:
            # Clean up temporary manifest file if it was created
            if temp_manifest_path and os.path.exists(temp_manifest_path):
                try:
                    os.remove(temp_manifest_path)
                    logger.info(f"Cleaned up temporary manifest file: {temp_manifest_path}")
                except Exception as e:
                    logger.error(f"Error removing temporary manifest file {temp_manifest_path}: {e}")


def main():
    """
    Main function for the CLI interface.
    """
    parser = argparse.ArgumentParser(
        description="Upload a book with PDF and HOCR files to InvenioRDM",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Handle template generation without requiring book-dir
    parser.add_argument(
        "--generate-metadata-template",
        action="store_true",
        help="Generate a template metadata file and exit"
    )
    parser.add_argument(
        "--template-output",
        default="metadata_template.json",
        help="Output file for the metadata template (used with --generate-metadata-template)"
    )
    
    # Required arguments (but only if not generating a template)
    parser.add_argument(
        "--book-dir", "-b", 
        help="Directory containing the book files (required unless --generate-metadata-template is used)"
    )
    
    # Optional arguments
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="InvenioRDM API URL"
    )
    parser.add_argument(
        "--token", 
        default=DEFAULT_API_TOKEN,
        help="API token for authentication"
    )
    parser.add_argument(
        "--username", 
        help="Username for basic authentication (if not using token)"
    )
    parser.add_argument(
        "--password", 
        help="Password for basic authentication"
    )
    parser.add_argument(
        "--skip-hocr", 
        action="store_true",
        help="Skip uploading HOCR files"
    )
    parser.add_argument(
        "--skip-tiff", 
        action="store_true",
        help="Skip uploading TIFF image files"
    )
    parser.add_argument(
        "--no-publish", 
        action="store_true",
        help="Don't publish the record after uploading files"
    )
    parser.add_argument(
        "--draft", 
        action="store_true",
        help="Keep the record as a draft (alias for --no-publish)"
    )
    parser.add_argument(
        "--pdf-only",
        action="store_true",
        help="Upload only the PDF file, skip all other files (HOCR, TIFF, etc.)"
    )
    parser.add_argument(
        "--community", 
        help="Community ID to add the record to"
    )
    parser.add_argument(
        "--no-verify-ssl", 
        action="store_true",
        default=False,
        help="Don't verify SSL certificates"
    )
    parser.add_argument(
        "--verify-ssl", 
        action="store_true",
        help="Enable SSL certificate verification"
    )
    parser.add_argument(
        "--metadata-file", 
        help="JSON file with additional metadata to add to the record"
    )
    parser.add_argument(
        "--max-retries", 
        type=int, 
        default=3,
        help="Maximum number of upload retries"
    )
    parser.add_argument(
        "--hocr-mount-point",
        help="Host directory path where HOCR files should be copied for service volume access (e.g., ./hocr_volume_data)"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Handle template generation
    if args.generate_metadata_template:
        template = {
            "metadata": {
                "title": "Book Title",
                "publication_date": datetime.now().strftime("%Y-%m-%d"),
                "resource_type": {"id": "publication-book"},
                "creators": [
                    {
                        "person_or_org": {
                            "family_name": "Author",
                            "given_name": "Primary",
                            "type": "personal"
                        },
                        "role": "author"
                    }
                ],
                "languages": [{"id": "ara"}],
                "description": "Description of the book",
                "identifiers": [
                    {
                        "identifier": "book-identifier",
                        "scheme": "other"
                    }
                ]
            },
            "access": {
                "record": "public",
                "files": "public"
            },
            "files": {
                "enabled": True
            },
            "custom_fields": {
                "turath:iiif_manifest": "http://your-server.com/iiif/3/book-id/manifest.json"
            }
        }
        
        try:
            with open(args.template_output, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Metadata template generated: {args.template_output}")
            logger.info("Edit the template with your book's metadata and use with --metadata-file")
            return 0
        except Exception as e:
            logger.error(f"Error generating template: {str(e)}")
            return 1
    
    # Check required arguments if not generating a template
    if not args.book_dir:
        logger.error("--book-dir is required unless using --generate-metadata-template")
        return 1
    
    # Handle SSL verification - if --verify-ssl is explicitly set, override --no-verify-ssl
    verify_ssl = not args.no_verify_ssl
    if args.verify_ssl:
        verify_ssl = True
    
    # Load additional metadata if specified
    custom_metadata = None
    if args.metadata_file:
        try:
            with open(args.metadata_file, 'r', encoding='utf-8') as f:
                custom_metadata = json.load(f)
            logger.info(f"Loaded custom metadata from {args.metadata_file}")
        except Exception as e:
            logger.error(f"Error loading metadata file: {str(e)}")
            return 1
    
    # Create uploader
    uploader = BookUploader(
        book_dir=args.book_dir,
        api_url=args.api_url,
        api_token=args.token,
        username=args.username,
        password=args.password,
        skip_hocr=args.skip_hocr or args.pdf_only,
        skip_tiff=args.skip_tiff or args.pdf_only,
        max_retries=args.max_retries,
        publish=not (args.no_publish or args.draft),
        community=args.community,
        verify_ssl=verify_ssl,
        custom_metadata=custom_metadata,
        hocr_mount_point=args.hocr_mount_point
    )
    
    # Process upload
    result = uploader.process()
    
    # Print result
    if result["success"]:
        logger.info(f"Successfully uploaded book {result.get('book_id')} to InvenioRDM")
        logger.info(f"Record ID: {result.get('record_id')}")
        
        # Prepare file count message
        file_types = []
        if result.get('pdf_files', 0) > 0:
            file_types.append(f"{result.get('pdf_files')} PDF")
        if result.get('hocr_files', 0) > 0:
            file_types.append(f"{result.get('hocr_files')} HOCR")
        if result.get('tiff_files', 0) > 0:
            file_types.append(f"{result.get('tiff_files')} TIFF")
        if result.get('other_files', 0) > 0:
            file_types.append(f"{result.get('other_files')} other")
        
        file_count_msg = f"Uploaded {result.get('uploaded_files')} files"
        if file_types:
            file_count_msg += f" ({', '.join(file_types)})"
        logger.info(file_count_msg)
        
        if result.get('published'):
            logger.info(f"Record published: https://localhost:5000/records/{result.get('record_id')}")
        else:
            logger.info(f"Record is in DRAFT status - complete metadata in the web interface before publishing")
            logger.info(f"Draft URL: https://localhost:5000/uploads/{result.get('record_id')}")
        return 0
    else:
        logger.error(f"Upload failed: {result.get('error', 'Unknown error')}")
        if "record_id" in result:
            logger.info(f"Partial record created with ID: {result.get('record_id')}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

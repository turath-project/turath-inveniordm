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
from datetime import datetime
from typing import Dict, List, Optional, Union
import requests
import logging
from pathlib import Path

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
        custom_metadata: Dict = None
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
            files['other'].append(manifest_path)
            logger.info(f"Including manifest.json for IIIF viewer support")
        
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
        Extract book information from manifest.json or infer from directory structure.
        
        Returns:
            Dictionary with book metadata
        """
        book_info = {
            "book_id": self.book_id,
            "title": self.book_id,  # Default title is the book ID
            "creators": [],
            "subjects": [],
            "language": "ar",
            "publication_date": "1900-01-01"
        }
        
        # Try to load from manifest.json
        manifest_path = os.path.join(self.book_dir, "manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = f.read()
                
                try:
                    manifest = json.loads(manifest_data)
                    
                    # Extract basic metadata
                    if isinstance(manifest, dict):
                        # Handle label - could be a string or dict with language keys
                        label = manifest.get("label", {})
                        if isinstance(label, dict):
                            # Try English label first, then any label
                            if "en" in label and isinstance(label["en"], list) and label["en"]:
                                book_info["title"] = label["en"][0]
                            elif label:
                                # Get first label from any language
                                for lang, values in label.items():
                                    if isinstance(values, list) and values:
                                        book_info["title"] = values[0]
                                        break
                        elif isinstance(label, str):
                            book_info["title"] = label
                        
                        # Look for metadata in the manifest
                        metadata = manifest.get("metadata", {})
                        
                        # Extract creator information
                        if "author" in metadata:
                            authors = metadata["author"]
                            if isinstance(authors, list):
                                for author in authors:
                                    if isinstance(author, dict) and "value" in author:
                                        book_info["creators"].append({"name": author["value"]})
                            elif isinstance(authors, dict) and "value" in authors:
                                book_info["creators"].append({"name": authors["value"]})
                        
                        # Extract subject information
                        if "subject" in metadata:
                            subjects = metadata["subject"]
                            if isinstance(subjects, list):
                                for subject in subjects:
                                    if isinstance(subject, dict) and "value" in subject:
                                        book_info["subjects"].append(subject["value"])
                            elif isinstance(subjects, dict) and "value" in subjects:
                                book_info["subjects"].append(subjects["value"])
                        
                        # Extract language
                        if "language" in metadata:
                            language = metadata["language"]
                            if isinstance(language, list) and language:
                                book_info["language"] = language[0]
                            elif isinstance(language, str):
                                book_info["language"] = language
                        
                        # Extract publication date
                        if "date" in metadata:
                            date = metadata["date"]
                            if isinstance(date, list) and date:
                                if isinstance(date[0], dict) and "value" in date[0]:
                                    book_info["publication_date"] = date[0]["value"]
                                else:
                                    book_info["publication_date"] = str(date[0])
                            elif isinstance(date, str):
                                book_info["publication_date"] = date
                    
                    logger.info(f"Successfully extracted book info from manifest.json: {book_info['title']}")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in manifest.json")
            except Exception as e:
                logger.error(f"Error parsing manifest.json: {str(e)}")
        else:
            logger.warning(f"No manifest.json found in {self.book_dir}, using default metadata")
        
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
        Prepare metadata for record creation.
        
        Args:
            book_info: Dictionary with book information
            
        Returns:
            Dictionary with record metadata
        """
        # Format creators
        creators = []
        for creator in book_info.get("creators", []):
            if isinstance(creator, dict) and "name" in creator:
                # Split the name into family name and given name
                full_name = creator["name"]
                name_parts = full_name.split()
                
                if len(name_parts) > 1:
                    # Use the last part as family name and the rest as given name
                    family_name = name_parts[-1]
                    given_name = " ".join(name_parts[:-1])
                else:
                    # If only one part, use it as family name
                    family_name = full_name
                    given_name = "Unknown"
                
                creators.append({
                    "person_or_org": {
                        "family_name": family_name,
                        "given_name": given_name,
                        "type": "personal"
                    },
                    "role": "author"
                })
        
        # If no creators were found, add a default one
        if not creators:
            creators.append({
                "person_or_org": {
                    "family_name": "Library",
                    "given_name": "Turath Digital",
                    "type": "organizational"
                }
            })
        
        # Format publication date
        pub_date = book_info.get("publication_date", "1900-01-01")
        # Make sure it's in YYYY-MM-DD format
        if re.match(r'^\d{4}$', pub_date):  # YYYY
            pub_date = f"{pub_date}-01-01"
        elif re.match(r'^\d{4}-\d{2}$', pub_date):  # YYYY-MM
            pub_date = f"{pub_date}-01"
        
        # Convert language code to ISO 639-3 if necessary
        language_code = book_info.get("language", "ara")
        # Map common 2-letter codes to 3-letter codes
        language_map = {
            "ar": "ara",
            "en": "eng",
            "fr": "fra",
            "de": "deu",
            "es": "spa"
        }
        if language_code in language_map:
            language_code = language_map[language_code]
        
        # Start with base metadata
        metadata = {
            "metadata": {
                "title": book_info.get("title", self.book_id),
                "publication_date": pub_date,
                "resource_type": {"id": "publication-book"},
                "creators": creators,
                "languages": [{"id": language_code}],
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
        
        # Add subjects if available
        if book_info.get("subjects"):
            metadata["metadata"]["subjects"] = [
                {"subject": subject} for subject in book_info.get("subjects", [])
            ]
        
        # Add community if specified
        if self.community:
            metadata["parent"] = {"id": self.community}
        
        # Add book ID as identifier with proper scheme
        metadata["metadata"]["identifiers"] = [
            {
                "identifier": self.book_id,
                "scheme": "other"  # Use a valid scheme accepted by InvenioRDM
            }
        ]
        
        # Add custom fields for IIIF support
        manifest_url = self.get_iiif_manifest_url()
        if manifest_url:
            if "custom_fields" not in metadata:
                metadata["custom_fields"] = {}
            
            # Add IIIF manifest URL
            metadata["custom_fields"]["turath:iiif_manifest"] = manifest_url
        
        # Merge with custom_metadata, allowing override
        if self.custom_metadata:
            # Merge metadata fields
            for key, value in self.custom_metadata.get("metadata", {}).items():
                metadata["metadata"][key] = value
            
            # Merge access settings
            for key, value in self.custom_metadata.get("access", {}).items():
                metadata["access"][key] = value
            
            # Merge custom fields if any
            if "custom_fields" in self.custom_metadata:
                if "custom_fields" not in metadata:
                    metadata["custom_fields"] = {}
                
                for key, value in self.custom_metadata.get("custom_fields", {}).items():
                    metadata["custom_fields"][key] = value
            
            # Merge other top-level fields
            for key, value in self.custom_metadata.items():
                if key not in ["metadata", "access", "custom_fields"]:
                    metadata[key] = value
        
        return metadata
    
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
    
    def upload_files_to_record(self, record_id: str, files_to_upload: List[str]) -> Dict:
        """
        Upload files to a draft record.
        
        Args:
            record_id: Record ID to upload files to
            files_to_upload: List of file paths to upload
            
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
            file_keys = [{"key": os.path.basename(path)} for path in files_to_upload]
            
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
        for file_path in files_to_upload:
            file_name = os.path.basename(file_path)
            logger.info(f"Uploading file: {file_name}")
            
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
            
            # Step 4: Create record
            create_result = self.create_record(metadata)
            if not create_result["success"]:
                return create_result
            
            record_id = create_result["record_id"]
            
            # Step 5: Upload files
            all_files_to_upload = []
            all_files_to_upload.extend(files['pdf'])
            all_files_to_upload.extend(files['hocr'])
            all_files_to_upload.extend(files['tiff'])
            all_files_to_upload.extend(files['other'])
            
            upload_result = self.upload_files_to_record(record_id, all_files_to_upload)
            
            if not upload_result["success"]:
                return {
                    "success": False,
                    "error": upload_result.get("error", "Failed to upload files"),
                    "record_id": record_id,
                    "partial": True
                }
            
            # Step 6: Publish record if requested
            if self.publish:
                publish_result = self.publish_record(record_id)
                if not publish_result["success"]:
                    return {
                        "success": False,
                        "error": publish_result.get("error", "Failed to publish record"),
                        "record_id": record_id,
                        "partial": True
                    }
            
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
        custom_metadata=custom_metadata
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

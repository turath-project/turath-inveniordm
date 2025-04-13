#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Create a test book with pages and import it to InvenioRDM.

This script generates a test book with actual image pages
and imports it into InvenioRDM using the book_importer.
"""

import os
import sys
import json
import argparse
import tempfile
import shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

def create_test_book(output_dir=None, num_pages=5, cleanup=True):
    """Create a test book with pages."""
    if output_dir is None:
        # Create a temporary directory if no output directory is specified
        temp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(temp_dir, "test_book")
    
    # Create the book directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create pages directory
    pages_dir = os.path.join(output_dir, "pages")
    os.makedirs(pages_dir, exist_ok=True)
    
    # Create metadata file
    metadata = {
        "title": "Test Book with Pages",
        "authors": [{"name": "Test Author"}],
        "publication_date": "2024",
        "language": "ara",
        "description": "A test book with automatically generated pages",
        "subjects": ["Testing", "Automation"],
        "test_record": True
    }
    
    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # Create pages with page numbers
    for i in range(1, num_pages + 1):
        # Create a blank white image
        img = Image.new('RGB', (800, 1200), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a font that's available on most systems
        try:
            # Try to find a font (this will vary by system)
            font_path = None
            system_font_dirs = [
                "/System/Library/Fonts",  # macOS
                "/usr/share/fonts",       # Linux
                "C:\\Windows\\Fonts"      # Windows
            ]
            
            for font_dir in system_font_dirs:
                if os.path.exists(font_dir):
                    # Find any .ttf font file
                    font_files = list(Path(font_dir).glob("**/*.ttf"))
                    if font_files:
                        font_path = str(font_files[0])
                        break
            
            if font_path:
                font = ImageFont.truetype(font_path, 60)
            else:
                # Use default font if no TTF font found
                font = ImageFont.load_default()
        except Exception:
            # Fallback to default font if there are any issues
            font = ImageFont.load_default()
        
        # Add page number text
        page_text = f"Page {i}"
        text_bbox = draw.textbbox((0, 0), page_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Position text in the center
        position = ((800 - text_width) // 2, (1200 - text_height) // 2)
        draw.text(position, page_text, fill='black', font=font)
        
        # Save the image
        page_path = os.path.join(pages_dir, f"page-{i:03d}.tif")
        img.save(page_path)
    
    print(f"Created test book with {num_pages} pages in: {output_dir}")
    return output_dir

def import_test_book(book_dir, username=None, password=None, token=None, dry_run=False):
    """Import the test book to InvenioRDM."""
    try:
        from app_data.scripts.book_importer import create_record, upload_files
        from app_data.scripts.config import IIIF_SERVER_URL
        import json
        import os
        
        print(f"Importing existing book from: {book_dir}")
        
        # Check if metadata file exists, create one if not
        metadata_path = os.path.join(book_dir, "metadata.json")
        if not os.path.exists(metadata_path):
            print(f"No metadata.json found in {book_dir}, creating a minimal one...")
            
            # Extract book_id from directory name
            book_id = os.path.basename(book_dir)
            
            # Create minimal metadata
            metadata = {
                "book_id": book_id,
                "title": f"Book: {book_id}",
                "authors": [{"name": "Auto-imported"}],
                "publication_date": "2024",
                "language": "ara",
                "description": f"Auto-imported book from {book_dir}",
                "subjects": ["Auto-imported"]
            }
            
            # Write metadata to file
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            print(f"Created metadata file: {metadata_path}")
        
        # Now load the metadata (either existing or newly created)
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Check for manifest.json
        manifest_path = os.path.join(book_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            print(f"Warning: No manifest.json found in {book_dir}")
            # We can continue without a manifest, but won't have IIIF features
        
        # Check for pages directory
        pages_dir = os.path.join(book_dir, "pages")
        if not os.path.isdir(pages_dir):
            # If no 'pages' directory, use the book directory itself for files
            print(f"No 'pages' directory found, will look for images in {book_dir}")
            pages_dir = book_dir
        
        # Prepare book_info structure as expected by create_record
        book_info = {
            "book_id": metadata.get("book_id", os.path.basename(book_dir)),
            "title": metadata.get("title", "Test Book"),
            "author": metadata.get("authors", [{"name": "Unknown Author"}])[0]["name"],
            "authors": metadata.get("authors", []),
            "publication_date": metadata.get("publication_date", "2024"),
            "language": metadata.get("language", "ara"),
            "description": metadata.get("description", "Test book import"),
            "subjects": metadata.get("subjects", [])
        }
        
        print(f"Creating record for book: {book_info['title']}")
        
        # Generate manifest URL if manifest exists
        manifest_url = None
        if os.path.exists(manifest_path):
            manifest_url = f"{IIIF_SERVER_URL}/{book_info['book_id']}/manifest.json"
            print(f"Using manifest URL: {manifest_url}")
        
        # If it's a dry run, just show what would happen
        if dry_run:
            print("DRY RUN: Would create record with book info:")
            import pprint
            pprint.pprint(book_info)
            print(f"Manifest URL: {manifest_url}")
            return {"success": True, "dry_run": True}
        
        # Create the record using book_importer.create_record
        record_id = None
        
        try:
            # Try with token first if provided
            if token:
                record_id = create_record(book_info, manifest_url, api_token=token)
            # Fall back to username/password if token not provided or failed
            if not record_id and username and password:
                record_id = create_record(book_info, manifest_url, username=username, password=password)
                
            if not record_id:
                return {"success": False, "error": "Failed to create record"}
                
            print(f"Record created successfully with ID: {record_id}")
            
            # Upload files to the record
            print(f"Uploading files from {pages_dir} to record {record_id}...")
            
            # Use consistent authentication method
            if token:
                upload_success = upload_files(record_id, pages_dir, token)
            else:
                upload_success = upload_files(record_id, pages_dir, None, username=username, password=password)
                
            if upload_success:
                print("Files uploaded successfully")
            else:
                print("Warning: Some or all file uploads failed")
                return {
                    "success": True,  # Still mark as success since record was created
                    "record_id": record_id,
                    "warning": "File uploads may have failed"
                }
                
            return {
                "success": True,
                "record_id": record_id
            }
            
        except Exception as e:
            import traceback
            print(f"Error during record creation or file upload: {e}")
            print(traceback.format_exc())
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        import traceback
        print(f"Error during book import: {e}")
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}

def main():
    """Main function to create and import a test book."""
    parser = argparse.ArgumentParser(description="Create and import a test book with pages")
    parser.add_argument("--output", "-o", help="Output directory for the test book")
    parser.add_argument("--pages", "-p", type=int, default=5, help="Number of pages to create")
    parser.add_argument("--username", "-u", help="Username for authentication")
    parser.add_argument("--password", "-w", help="Password for authentication")
    parser.add_argument("--token", "-t", help="API token for authentication")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Dry run (don't actually create records)")
    parser.add_argument("--import-only", "-i", help="Import existing book without creating a new one")
    
    args = parser.parse_args()
    
    if args.import_only:
        # Import an existing book
        book_dir = args.import_only
        print(f"Importing existing book from: {book_dir}")
    else:
        # Create a new test book
        book_dir = create_test_book(args.output, args.pages)
    
    # Import the book
    import_test_book(book_dir, args.username, args.password, args.token, args.dry_run)

if __name__ == "__main__":
    main()

# IIIF Manifests for PDF Files

This guide provides a preliminary approach to generating IIIF manifests for PDF files in Zenodo RDM. By default, Zenodo RDM only generates IIIF manifests for image files (JPG, PNG, TIFF, etc.), but with some additional processing, PDF files can also be made available through IIIF.

## Overview

The process of creating IIIF manifests for PDFs involves:

1. Extracting individual pages from the PDF as images
2. Converting these images to PTIF format
3. Storing the PTIF files in the IIPImage server
4. Generating a IIIF manifest that includes all pages as canvases

## Prerequisites

- A working Zenodo RDM installation with IIIF support
- IIPImage server properly configured
- `pdftoppm` or `ghostscript` for PDF to image conversion
- `kdu_compress` for PTIF conversion
- Python with necessary libraries (pdf2image, PIL)

## Implementation Steps

### 1. PDF Page Extraction

First, we need to extract individual pages from the PDF as high-quality images:

```python
# pdf_to_images.py
import os
from pdf2image import convert_from_path

def extract_pdf_pages(pdf_path, output_dir, dpi=300):
    """Extract all pages from a PDF as images.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted images
        dpi: Resolution for extracted images (default: 300)
    
    Returns:
        List of paths to extracted images
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract pages as images
    pages = convert_from_path(pdf_path, dpi=dpi)
    
    # Save each page as TIFF
    image_paths = []
    for i, page in enumerate(pages):
        image_path = os.path.join(output_dir, f"page-{i+1:03d}.tiff")
        page.save(image_path, "TIFF")
        image_paths.append(image_path)
    
    return image_paths
```

### 2. Integration with Zenodo RDM

Next, we'll create a script that processes PDF files in records and sets up IIIF for each page:

```python
# setup_pdf_iiif.py
import os
import sys
import json
import requests
import subprocess
from pdf2image import convert_from_path

def setup_pdf_iiif(record_id, pdf_filename):
    """Set up IIIF for a PDF file in a Zenodo RDM record.
    
    Args:
        record_id: The record ID containing the PDF
        pdf_filename: The filename of the PDF in the record
    """
    # Step 1: Download the PDF from the record
    print(f"Downloading PDF file {pdf_filename} from record {record_id}...")
    subprocess.run(["python", "get_file.py", record_id, pdf_filename, "."])
    
    if not os.path.exists(pdf_filename):
        print(f"Error: Could not download {pdf_filename}")
        return False
    
    # Step 2: Create temporary directory for extracted pages
    temp_dir = f"temp_pdf_{record_id}"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Step 3: Extract pages as images
    print(f"Extracting pages from {pdf_filename}...")
    image_paths = extract_pdf_pages(pdf_filename, temp_dir)
    print(f"Extracted {len(image_paths)} pages")
    
    # Step 4: Convert each page to PTIF and set up IIIF
    for image_path in image_paths:
        page_filename = os.path.basename(image_path)
        print(f"Setting up IIIF for page {page_filename}...")
        subprocess.run(["python", "convert_to_ptif.py", image_path, record_id])
    
    # Step 5: Clean up
    print("Cleaning up temporary files...")
    for image_path in image_paths:
        os.remove(image_path)
    os.rmdir(temp_dir)
    os.remove(pdf_filename)
    
    # Step 6: Verify IIIF setup
    print("Verifying IIIF manifest...")
    subprocess.run(["python", "check_iiif.py", record_id])
    
    return True

def extract_pdf_pages(pdf_path, output_dir, dpi=300):
    """Extract all pages from a PDF as images."""
    # Implementation from previous code
    pages = convert_from_path(pdf_path, dpi=dpi)
    
    image_paths = []
    for i, page in enumerate(pages):
        image_path = os.path.join(output_dir, f"page-{i+1:03d}.tiff")
        page.save(image_path, "TIFF")
        image_paths.append(image_path)
    
    return image_paths

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python setup_pdf_iiif.py RECORD_ID PDF_FILENAME")
        sys.exit(1)
    
    record_id = sys.argv[1]
    pdf_filename = sys.argv[2]
    
    setup_pdf_iiif(record_id, pdf_filename)
```

### 3. Makefile Integration

Add the PDF-to-IIIF functionality to your Makefile:

```makefile
# Add to scripts/AlA/Makefile

# PDF IIIF setup
setup-pdf-iiif:
	@if [ -z "$(RECORD)" ]; then \
		echo "Setting up IIIF for PDF record. Usage: make setup-pdf-iiif RECORD=<id> PDF=<filename>"; \
		exit 1; \
	fi
	@if [ -z "$(PDF)" ]; then \
		echo "Setting up IIIF for PDF record. Usage: make setup-pdf-iiif RECORD=<id> PDF=<filename>"; \
		exit 1; \
	fi
	@echo "Setting up IIIF for PDF $(PDF) in record $(RECORD)..."
	@python setup_pdf_iiif.py $(RECORD) $(PDF)
```

### 4. Custom Manifest Generation

For better PDF representation, you might want to customize the manifest to indicate it's a PDF document:

```python
# Extend ZenodoIIIFManifestV2Schema to handle PDFs
class PDFIIIFManifestV2Schema(ZenodoIIIFManifestV2Schema):
    """Enhanced IIIF manifest schema for PDF files."""

    def get_metadata(self, obj):
        """Generate enhanced metadata with PDF information."""
        metadata = super().get_metadata(obj)
        
        # Add PDF-specific metadata
        pdf_files = [f for f in obj.get("files", {}).get("entries", {}).values() 
                    if f.get("ext") == "pdf"]
        
        if pdf_files:
            pdf_file = pdf_files[0]
            metadata.append({
                "label": _("Source Document"),
                "value": f"PDF: {pdf_file['key']} ({pdf_file['size']} bytes)"
            })
            
            # Add page count if available
            if "pages" in pdf_file.get("metadata", {}):
                metadata.append({
                    "label": _("Pages"),
                    "value": str(pdf_file["metadata"]["pages"])
                })
        
        return metadata
```

## Usage

To use the PDF IIIF functionality:

1. Upload a PDF file to a Zenodo RDM record
2. Run the setup-pdf-iiif command:

```bash
cd scripts/AlA
make setup-pdf-iiif RECORD=123 PDF=document.pdf
```

3. Access the IIIF manifest at:

```
https://your-zenodo-instance/api/iiif/record:123/manifest
```

## Limitations and Considerations

- **Performance**: Converting large PDFs with many pages can be resource-intensive
- **Quality**: The quality of extracted images affects the viewing experience
- **Storage**: Each PDF page requires additional storage as PTIF files
- **Updates**: If the PDF is updated, the IIIF manifests need to be regenerated
- **Text Content**: This approach treats PDFs as image collections, losing text content and search

## Future Improvements

Future enhancements could include:

1. **OCR Integration**: Extracting text from PDF pages for search
2. **PDF Structure Preservation**: Maintaining bookmarks and document structure
3. **Selective Page Extraction**: Converting only specific pages for large documents
4. **Caching**: Implementing a cache system to avoid redundant conversions
5. **Annotation Support**: Enabling IIIF annotations on PDF pages

## Conclusion

While Zenodo RDM doesn't natively generate IIIF manifests for PDFs, this approach provides a workaround by treating PDFs as collections of images. This enables the use of IIIF viewers for PDF content, providing features like deep zoom and side-by-side comparison that aren't available in standard PDF viewers. 
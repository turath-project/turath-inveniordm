# PDF IIIF Integration by Example

![PDF IIIF Example Workflow](https://mermaid.ink/img/pako:eNp9ksFu2zAMhl-F0CnZ8gA5JEW7pWmLrYdd2h6KHQJZom2htmRIctos8LvPdpw0yeEwYJB_fvpJkc4wNtaBhp2ttx-uRT-aGpMxlxu4_uGbVe1_Dct1Lc47QgyYLXe0WRH646JyHvowXRZivGtOhm5ihB5YFSp08sxjY33Ip3zKwPNXbO-qwgEN2RhMwxc-iAyFu25gaBuBlg1BVTMWh-rHQ9VbmEYuZDo52n9vgnmxk66Qd-cNIKVTMoO8xFyWOKq8l0eDLpqTdnLXRXVzALnGj9fxlRN4K38TUgbqUKHhJXiNdxTU_Ro4W2vXqGSP2Y_RdBbOfyKOeOG9ZC5ykhsabNrrcagPnoPsfC-zXmWb2Hq4ndoB1GNSZZJaO2hxzyqRr5eeQDzRRdcGgmdoDbWs9CXibg7PXxGFaxykTd1mwrRe4TdWYmvtudBc_n5SvztxCXJRnULnGTVvt4Hxh57-ZfS-Lut77OhV-Tt7_5qH_PXp_eHw9JQ_XQ6Hw-EpQ97HQsOLcfwsCaGyfVcpamr2vMDSdyLq4xgVe28kh2-jMsPejGGVLeT8a1H1VI9wblu3sSzPvwCx0LY1?type=png)

## Table of Contents

1. [Introduction](#introduction)
2. [Common Use Cases](#common-use-cases)
3. [Working with PDF Files](#working-with-pdf-files)
4. [Example: Simple PDF Upload and View](#example-simple-pdf-upload-and-view)
5. [Example: Testing PDF Page Navigation](#example-testing-pdf-page-navigation)
6. [Example: Creating PDF Thumbnails](#example-creating-pdf-thumbnails)
7. [Example: Integrating with a Viewer](#example-integrating-with-a-viewer)
8. [Code Examples](#code-examples)

## Introduction

This guide provides practical examples for working with PDF files in the IIIF integration with Zenodo RDM. Unlike image files, which are converted to PTIF format, PDFs are handled directly by the Cantaloupe server, which can extract individual pages as images.

## Common Use Cases

The PDF IIIF integration enables several common use cases:

1. **Online PDF Viewing**: View PDF documents directly in the browser without plugins.
2. **Page-by-Page Navigation**: Navigate through PDF pages using IIIF viewers.
3. **PDF Thumbnails**: Generate thumbnails of specific PDF pages.
4. **Region Selection**: Zoom and crop specific areas of a PDF page.
5. **PDF in Presentation API**: Include PDFs in IIIF presentations alongside other content.

## Working with PDF Files

PDF files are handled differently from images in our IIIF implementation:

- **Storage Path**: `data/images/private/<record_id>/<filename>.pdf`
- **URL Pattern**: `/api/iiif/record:<record_id>:<filename>.pdf/<region>/<size>/<rotation>/<quality>.<format>?page=<page_number>`
- **Page Selection**: Pages are selected with the `?page=` parameter (starting from 1)

## Example: Simple PDF Upload and View

This example demonstrates how to upload a PDF to a record and access it through IIIF.

### 1. Upload a PDF to a New Record

```bash
# Set API token
export API_TOKEN="your-api-token-here"

# Upload PDF to a new record
python scripts/AlA/upload_pdf.py new /path/to/document.pdf
```

Example output:
```
Created new record with ID: 212
Generated DOI: 10.5281/zenodo.iy1pvums
File committed successfully
Successfully uploaded PDF file /path/to/document.pdf to new record 212
You can now test the IIIF manifest with:
python3 check_iiif.py 212
```

### 2. Verify the Record Details

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
     "https://127.0.0.1:5000/api/records/212" -k | jq .
```

Example output (truncated):
```json
{
  "id": 212,
  "doi": "10.5281/zenodo.iy1pvums",
  "metadata": {
    "title": "Test PDF Record",
    "publication_date": "2025-04-07",
    "creators": [
      {
        "person_or_org": {
          "family_name": "User",
          "given_name": "Test",
          "type": "personal"
        }
      }
    ],
    "resource_type": {
      "id": "publication-article"
    },
    "publisher": "Zenodo",
    "license": {
      "id": "cc-by-4.0"
    }
  },
  "files": [
    {
      "key": "history00871.pdf",
      "size": 1362336,
      "checksum": "md5:8a7fb5d3b5c719c6d10ed7746a86b8a9"
    }
  ]
}
```

### 3. Access the PDF's IIIF Info

```bash
curl "http://localhost:8182/iiif/2/images%2Fprivate%2F212%2Fhistory00871.pdf/info.json" | jq .
```

Example output (truncated):
```json
{
  "@context": "http://iiif.io/api/image/2/context.json",
  "@id": "http://localhost:8182/iiif/2/images%2Fprivate%2F212%2Fhistory00871.pdf",
  "protocol": "http://iiif.io/api/image",
  "width": 612,
  "height": 792,
  "sizes": [
    { "width": 306, "height": 396 },
    { "width": 153, "height": 198 },
    { "width": 76, "height": 99 }
  ],
  "tiles": [
    { "width": 256, "height": 256, "scaleFactors": [ 1, 2, 4, 8 ] }
  ],
  "profile": [
    "http://iiif.io/api/image/2/level2.json",
    {
      "formats": [ "jpg", "png", "gif", "webp" ],
      "qualities": [ "color", "gray", "bitonal", "default" ],
      "supports": [
        "regionByPx", "sizeByW", "sizeByH", "sizeByPct",
        "sizeByConfinedWh", "sizeByDistortedWh", "sizeByWh",
        "rotationBy90s", "mirroring", "regionSquare"
      ]
    }
  ]
}
```

### 4. View the First Page of the PDF

```bash
curl "http://localhost:8182/iiif/2/images%2Fprivate%2F212%2Fhistory00871.pdf/full/full/0/default.jpg?page=1" -o page1.jpg
```

This will save the first page of the PDF as a JPEG image named `page1.jpg`.

## Example: Testing PDF Page Navigation

This example shows how to navigate through different pages of a PDF using IIIF.

### 1. Using the Cantaloupe Tester Script

```bash
python test/test_cantaloupe_basic.py --record 212 --file history00871.pdf --page 2
```

Example output:
```
Testing Cantaloupe PDF functionality
Server: http://localhost:8182
Record ID: 212
Filename: history00871.pdf
Page: 2

Testing PDF info at URL: http://localhost:8182/iiif/2/images%2Fprivate%2F212%2Fhistory00871.pdf/info.json
SUCCESS! Received info.json (Status: 200)
Content type: application/json;charset=utf-8
Response size: 1688 bytes

Testing PDF page rendering at URL: http://localhost:8182/iiif/2/images%2Fprivate%2F212%2Fhistory00871.pdf/full/full/0/default.jpg?page=2
SUCCESS! Downloaded page 2 as JPEG (Status: 200)
Content type: image/jpeg
Image saved to: test_page2.jpg
File size: 68540 bytes

Testing PDF thumbnail rendering at URL: http://localhost:8182/iiif/2/images%2Fprivate%2F212%2Fhistory00871.pdf/full/200,/0/default.jpg?page=2
SUCCESS! Downloaded thumbnail for page 2 (Status: 200)
Content type: image/jpeg
Image saved to: test_thumbnail2.jpg
File size: 5823 bytes

=== Test Summary ===
Info.json: ✅ PASS
Page rendering: ✅ PASS
Thumbnail: ✅ PASS

✅ All tests PASSED!
```

### 2. Manually Testing Different Pages

To manually download multiple pages:

```bash
# Page 1
curl "http://localhost:8182/iiif/2/images%2Fprivate%2F212%2Fhistory00871.pdf/full/full/0/default.jpg?page=1" -o page1.jpg

# Page 2
curl "http://localhost:8182/iiif/2/images%2Fprivate%2F212%2Fhistory00871.pdf/full/full/0/default.jpg?page=2" -o page2.jpg

# Page 3
curl "http://localhost:8182/iiif/2/images%2Fprivate%2F212%2Fhistory00871.pdf/full/full/0/default.jpg?page=3" -o page3.jpg
```

### 3. Testing Page Numbers Beyond PDF Length

```bash
# Attempt to access a page beyond the PDF length
curl -I "http://localhost:8182/iiif/2/images%2Fprivate%2F212%2Fhistory00871.pdf/full/full/0/default.jpg?page=999"
```

Expected output:
```
HTTP/1.1 400 Bad Request
Date: Mon, 08 Apr 2025 08:45:12 GMT
X-Powered-By: Cantaloupe/5.0.5
Content-Type: text/plain;charset=utf-8
Content-Length: 95
Server: Jetty(9.4.34.v20201102)

PdfBoxProcessor: page number 999 is outside the range of pages in the PDF (1-10)
```

## Example: Creating PDF Thumbnails

This example demonstrates how to create thumbnails of PDF pages using IIIF.

### 1. Create Thumbnails of Various Sizes

```bash
# Small thumbnail (width: 100px)
curl "http://localhost:8182/iiif/2/images%2Fprivate%2F212%2Fhistory00871.pdf/full/100,/0/default.jpg?page=1" -o thumb_small.jpg

# Medium thumbnail (width: 200px)
curl "http://localhost:8182/iiif/2/images%2Fprivate%2F212%2Fhistory00871.pdf/full/200,/0/default.jpg?page=1" -o thumb_medium.jpg

# Large thumbnail (width: 400px)
curl "http://localhost:8182/iiif/2/images%2Fprivate%2F212%2Fhistory00871.pdf/full/400,/0/default.jpg?page=1" -o thumb_large.jpg
```

### 2. Create Square Thumbnails

```bash
# Square thumbnail (100x100 pixels)
curl "http://localhost:8182/iiif/2/images%2Fprivate%2F212%2Fhistory00871.pdf/square/100,100/0/default.jpg?page=1" -o thumb_square.jpg
```

### 3. Create Thumbnails with Region Selection

```bash
# Region thumbnail (top-left quadrant, 200px wide)
curl "http://localhost:8182/iiif/2/images%2Fprivate%2F212%2Fhistory00871.pdf/0,0,306,396/200,/0/default.jpg?page=1" -o thumb_region.jpg
```

## Example: Integrating with a Viewer

This example shows how to integrate PDF viewing with the Universal Viewer.

### 1. Get the IIIF Manifest for the Record

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
     "https://127.0.0.1:5000/api/iiif/record:212/manifest" -k > manifest.json
```

### 2. Create a Simple HTML Viewer Page

```html
<!DOCTYPE html>
<html>
<head>
    <title>PDF IIIF Viewer</title>
    <script src="https://unpkg.com/universalviewer/dist/uv.js"></script>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/universalviewer/dist/uv.css">
    <style>
        body { margin: 0; padding: 0; }
        #uv { width: 100%; height: 800px; }
    </style>
</head>
<body>
    <div id="uv"></div>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const UV = window.UV;
            const data = {
                manifest: "manifest.json"
            };
            uv = UV.init("uv", data);
            window.uv = uv;
        });
    </script>
</body>
</html>
```

Save this as `pdf_viewer.html` and open it in a browser to view the PDF with IIIF navigation.

## Code Examples

### Python Example: Fetching Multiple PDF Pages

```python
#!/usr/bin/env python3
import os
import requests
import argparse

def fetch_pdf_pages(record_id, filename, start_page, end_page):
    """Fetch a range of PDF pages as images."""
    # Create output directory
    os.makedirs("pdf_pages", exist_ok=True)
    
    base_url = f"http://localhost:8182/iiif/2/images%2Fprivate%2F{record_id}%2F{filename}"
    
    # First get the info.json to know how many pages are available
    info_response = requests.get(f"{base_url}/info.json")
    if info_response.status_code != 200:
        print(f"Error fetching PDF info: {info_response.status_code}")
        return
    
    print(f"Successfully fetched PDF info")
    
    # Download each page
    for page_num in range(start_page, end_page + 1):
        page_url = f"{base_url}/full/full/0/default.jpg?page={page_num}"
        response = requests.get(page_url)
        
        if response.status_code == 200:
            output_path = f"pdf_pages/page_{page_num:03d}.jpg"
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"Downloaded page {page_num} to {output_path}")
        else:
            print(f"Error downloading page {page_num}: {response.status_code}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch PDF pages as images via IIIF")
    parser.add_argument("record_id", help="Record ID")
    parser.add_argument("filename", help="PDF filename")
    parser.add_argument("--start", type=int, default=1, help="Starting page (default: 1)")
    parser.add_argument("--end", type=int, default=10, help="Ending page (default: 10)")
    
    args = parser.parse_args()
    fetch_pdf_pages(args.record_id, args.filename, args.start, args.end)
```

Save this as `fetch_pdf_pages.py` and run it:

```bash
python fetch_pdf_pages.py 212 history00871.pdf --start 1 --end 5
```

### Python Example: Creating a PDF Contact Sheet

```python
#!/usr/bin/env python3
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import math
import argparse

def create_contact_sheet(record_id, filename, pages, columns=3, size=200):
    """Create a contact sheet from PDF pages."""
    base_url = f"http://localhost:8182/iiif/2/images%2Fprivate%2F{record_id}%2F{filename}"
    
    # Get pages
    page_images = []
    for page in pages:
        page_url = f"{base_url}/full/{size},/0/default.jpg?page={page}"
        response = requests.get(page_url)
        
        if response.status_code == 200:
            img = Image.open(io.BytesIO(response.content))
            page_images.append(img)
            print(f"Downloaded page {page}")
        else:
            print(f"Error downloading page {page}: {response.status_code}")
    
    if not page_images:
        print("No pages downloaded.")
        return
    
    # Calculate layout
    rows = math.ceil(len(page_images) / columns)
    img_width = page_images[0].width
    img_height = page_images[0].height
    
    # Create contact sheet
    contact_sheet = Image.new('RGB', 
                             (columns * img_width, rows * img_height + 30),
                             (255, 255, 255))
    
    # Add title
    draw = ImageDraw.Draw(contact_sheet)
    try:
        font = ImageFont.truetype("Arial", 20)
    except IOError:
        font = ImageFont.load_default()
    
    title = f"PDF Contact Sheet: {filename} (Record {record_id})"
    draw.text((10, 5), title, fill=(0, 0, 0), font=font)
    
    # Paste images
    for i, img in enumerate(page_images):
        row = i // columns
        col = i % columns
        contact_sheet.paste(img, (col * img_width, row * img_height + 30))
        
        # Add page number
        page_num = pages[i]
        draw.text((col * img_width + 5, row * img_height + 35), 
                 f"Page {page_num}", fill=(0, 0, 0), font=font)
    
    # Save contact sheet
    output_path = f"contact_sheet_{record_id}_{filename.replace('.pdf', '')}.jpg"
    contact_sheet.save(output_path, "JPEG", quality=90)
    print(f"Contact sheet saved to {output_path}")
    
    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a contact sheet from PDF pages")
    parser.add_argument("record_id", help="Record ID")
    parser.add_argument("filename", help="PDF filename")
    parser.add_argument("--pages", default="1,2,3,4,5,6", 
                       help="Comma-separated list of pages (default: 1,2,3,4,5,6)")
    parser.add_argument("--columns", type=int, default=3, 
                       help="Number of columns (default: 3)")
    parser.add_argument("--size", type=int, default=200, 
                       help="Thumbnail width (default: 200)")
    
    args = parser.parse_args()
    pages = [int(p) for p in args.pages.split(",")]
    
    create_contact_sheet(args.record_id, args.filename, pages, args.columns, args.size)
```

Save this as `create_contact_sheet.py` and run it:

```bash
python create_contact_sheet.py 212 history00871.pdf --pages 1,2,3,4,5,6 --columns 3 --size 200
```

---

*This guide provides practical examples for working with PDF files in IIIF. Try these examples with your own PDFs to see how the integration works.*

# PDF Support in Cantaloupe: A Practical Guide

This guide provides a hands-on approach to implementing and troubleshooting PDF support in Cantaloupe IIIF server within InvenioRDM. We'll walk through common challenges and solutions with practical examples.

## Table of Contents

1. [Understanding the Problem](#understanding-the-problem)
2. [Testing PDF Access](#testing-pdf-access)
3. [Implementing the Solution](#implementing-the-solution)
4. [Troubleshooting](#troubleshooting)
5. [Advanced Usage](#advanced-usage)

## Understanding the Problem

### The Issue with PDF Paths

The core issue with PDF support in Cantaloupe is the handling of file paths. Let's see what happens when we try to access a PDF without proper URL encoding:

```bash
# Incorrect approach - using regular slashes
curl "http://localhost:8182/iiif/2/private/212/history00871.pdf/info.json"
```

Response:
```
404 Not Found - No route for path: /iiif/2/private/212/history00871.pdf/info.json
```

Why does this happen? Cantaloupe expects the file path to be URL-encoded, with slashes (`/`) encoded as `%2F`. When we don't encode the slashes, Cantaloupe can't correctly identify the file path.

### Visual Explanation

```
Unencoded path:
http://localhost:8182/iiif/2/private/212/history00871.pdf/info.json
                             ^      ^        
                             |      |        
                         These slashes confuse Cantaloupe

Encoded path:
http://localhost:8182/iiif/2/private%2F212%2Fhistory00871.pdf/info.json
                             ^^^^^^^^^^^^^^^
                             Properly encoded path
```

## Testing PDF Access

Let's walk through a step-by-step process to test PDF access with Cantaloupe:

### 1. Check Cantaloupe Configuration

First, verify that Cantaloupe is configured for PDF support:

```bash
docker exec -it zenodo-rdm-master-cantaloupe-1 cat /etc/cantaloupe.properties | grep -E "processor.pdf|source"
```

You should see something like:
```
processor.pdf = PdfBoxProcessor
source.static = FilesystemSource
```

### 2. Check File Locations

Verify your PDF files are in the expected location:

```bash
docker exec -it zenodo-rdm-master-cantaloupe-1 ls -la /opt/cantaloupe/images/private/212/
```

### 3. Test Direct Access with Encoded Path

Try accessing the PDF info with proper encoding:

```bash
curl "http://localhost:8182/iiif/2/private%2F212%2Fhistory00871.pdf/info.json"
```

If successful, you'll get a JSON response with PDF information:

```json
{
  "@context": "http://iiif.io/api/image/2/context.json",
  "@id": "http://localhost:8182/iiif/2/private%2F212%2Fhistory00871.pdf",
  "protocol": "http://iiif.io/api/image",
  "width": 955,
  "height": 1380,
  "sizes": [
    {"width": 119, "height": 173},
    {"width": 239, "height": 345},
    {"width": 478, "height": 690},
    {"width": 955, "height": 1380}
  ],
  "tiles": [
    {"width": 512, "height": 512, "scaleFactors": [1, 2, 4, 8]},
    ...
  ],
  "profile": [
    "http://iiif.io/api/image/2/level2.json",
    {
      "formats": ["tif", "jpg", "gif", "png"],
      ...
    }
  ]
}
```

### 4. Accessing PDF Pages

To access a specific page of the PDF:

```bash
curl "http://localhost:8182/iiif/2/private%2F212%2Fhistory00871.pdf/full/full/0/default.jpg?page=1" -o page1.jpg
```

This will save page 1 of the PDF as a JPEG image.

## Implementing the Solution

Now, let's implement the solution in our Python code:

### 1. Update the URL Building Function

```python
def build_cantaloupe_url(self, record_id, filename, region, size, rotation, quality, format, page=None):
    """Build a URL for the Cantaloupe server."""
    # Get the file path
    file_path = self._get_file_path(record_id, filename)
    
    # Encode slashes in the path
    encoded_path = file_path.replace("/", "%2F")
    
    # Build the URL based on the request type
    if region == "info.json":
        url = f"{self.base_url}/iiif/2/{encoded_path}/info.json"
    else:
        url = f"{self.base_url}/iiif/2/{encoded_path}/{region}/{size}/{rotation}/{quality}.{format}"
    
    # Add page parameter for PDFs if needed
    if page is not None and self._is_pdf(filename):
        url += f"?page={page}"
    
    return url
```

### 2. Updating the PDF Info Retrieval

```python
def get_pdf_info(self, record_id, filename):
    """Get information about a PDF file from Cantaloupe."""
    # Ensure we're dealing with a PDF
    if not self._is_pdf(filename):
        return None
    
    # Get the file path and encode it
    file_path = self._get_file_path(record_id, filename)
    encoded_path = file_path.replace("/", "%2F")
    
    # Construct the URL
    url = f"{self.base_url}/iiif/2/{encoded_path}/info.json"
    
    try:
        # Make the request
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error(f"Error getting PDF info: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        self.logger.error(f"Exception in get_pdf_info: {e}")
        return None
```

### 3. Testing with Our Custom Script

Create a test script (`test_pdf_manifest.py`) to verify your implementation:

```python
import requests
import logging
import json
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_cantaloupe_direct(record_id, filename):
    """Test direct access to Cantaloupe."""
    path = f"private/{record_id}/{filename}"
    encoded_path = path.replace("/", "%2F")
    url = f"http://localhost:8182/iiif/2/{encoded_path}/info.json"
    
    logger.info(f"Testing Cantaloupe direct access with encoded slashes: {url}")
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            info = response.json()
            logger.info(f"Successfully retrieved PDF info: {info}")
            return True
        else:
            logger.error(f"Error fetching PDF info: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Exception in test_cantaloupe_direct: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <record_id> [<filename>]")
        sys.exit(1)
    
    record_id = sys.argv[1]
    filename = "history00871.pdf"  # Default filename
    
    if len(sys.argv) >= 3:
        filename = sys.argv[2]
    
    # Run test
    result = test_cantaloupe_direct(record_id, filename)
    print(f"Test result: {'PASS' if result else 'FAIL'}")
```

Run the script:
```bash
python test_pdf_manifest.py 212
```

## Troubleshooting

### Common Issues and Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| Path not encoded | 404 "No route for path" | Encode slashes with `%2F` |
| PDF not found | 404 "Not Found" | Verify file exists in correct location |
| PDF processor not enabled | Error response | Set `CANTALOUPE_PROCESSOR_PDF=PdfBoxProcessor` |
| Empty manifest | Manifest has no canvases | Ensure PDF info retrieval works and canvas generation logic is correct |
| Page parameter missing | Wrong page displayed | Add `?page=N` parameter for PDFs |

### Debugging Steps

1. **Check Cantaloupe logs:**
   ```bash
   docker logs zenodo-rdm-master-cantaloupe-1
   ```

2. **Verify PDF accessibility:**
   ```bash
   docker exec -it zenodo-rdm-master-cantaloupe-1 ls -la /opt/cantaloupe/images/private/212/history00871.pdf
   ```

3. **Test basic image access first:**
   ```bash
   curl "http://localhost:8182/iiif/2/test%2Ftest.jpg/info.json"
   ```

4. **Add detailed logging in your code:**
   ```python
   self.logger.info(f"Attempting to access PDF at {url}")
   self.logger.info(f"Response status: {response.status_code}")
   ```

## Advanced Usage

### Generating PDF Manifests

To create a complete IIIF manifest for a PDF:

```python
def generate_pdf_manifest(self, record_id, filename, base_url, id_prefix, label="PDF Document", metadata=None):
    """Generate a IIIF manifest for a PDF file."""
    # Get PDF info
    pdf_info = self.get_pdf_info(record_id, filename)
    if not pdf_info:
        self.logger.error(f"Failed to get PDF info for {record_id}/{filename}")
        return None
    
    # Default size if not available
    width = pdf_info.get('width', 800)
    height = pdf_info.get('height', 1200)
    
    # Create basic manifest structure
    manifest = {
        "@context": "http://iiif.io/api/presentation/2/context.json",
        "@type": "sc:Manifest",
        "@id": f"{base_url}/api/iiif/record:{record_id}/manifest",
        "label": label,
        "description": "Manifest generated by InvenioRDM",
        "sequences": [
            {
                "@id": f"{base_url}/api/iiif/record:{record_id}/sequence/default",
                "@type": "sc:Sequence",
                "label": "Current Page Order",
                "viewingDirection": "left-to-right",
                "viewingHint": "individuals",
                "canvases": []
            }
        ]
    }
    
    # Add metadata if provided
    if metadata:
        manifest["metadata"] = metadata
    
    # Determine number of pages from PDF info
    # Check 'tiles' array as it typically contains one entry per page
    num_pages = 0
    if 'tiles' in pdf_info:
        num_pages = len(pdf_info['tiles'])
    elif 'sizes' in pdf_info:
        num_pages = len(pdf_info['sizes'])
        
    if num_pages <= 0:
        num_pages = 1  # Default to at least one page
        
    self.logger.info(f"PDF has {num_pages} pages according to Cantaloupe info.json")
    
    # Encode the file path for Cantaloupe
    file_path = self._get_file_path(record_id, filename)
    encoded_path = file_path.replace("/", "%2F")
    
    # Create a canvas for each page
    for page_num in range(1, num_pages + 1):
        canvas_id = f"{base_url}/api/iiif/record:{record_id}:{filename}/canvas/p{page_num:03d}"
        canvas = {
            "@id": canvas_id,
            "@type": "sc:Canvas",
            "label": f"Page {page_num}",
            "width": width,
            "height": height,
            "images": [
                {
                    "@id": f"{canvas_id}/image",
                    "@type": "oa:Annotation",
                    "motivation": "sc:painting",
                    "resource": {
                        "@id": f"{self.base_url}/iiif/2/{encoded_path}/full/full/0/default.jpg?page={page_num}",
                        "@type": "dctypes:Image",
                        "format": "image/jpeg",
                        "width": width,
                        "height": height,
                        "service": {
                            "@context": "http://iiif.io/api/image/2/context.json",
                            "@id": f"{self.base_url}/iiif/2/{encoded_path}",
                            "profile": "http://iiif.io/api/image/2/level2.json"
                        }
                    },
                    "on": canvas_id
                }
            ]
        }
        manifest["sequences"][0]["canvases"].append(canvas)
    
    self.logger.info(f"Successfully generated manifest with {len(manifest['sequences'][0]['canvases'])} canvases")
    return manifest
```

### Custom URL Construction

For special cases where you need to construct URLs with additional parameters:

```python
def build_custom_cantaloupe_url(self, path, params=None):
    """Build a custom URL for the Cantaloupe server."""
    # Encode slashes in the path
    encoded_path = path.replace("/", "%2F")
    
    # Construct the base URL
    url = f"{self.base_url}/iiif/2/{encoded_path}"
    
    # Add query parameters
    if params:
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url += f"?{query_string}"
    
    return url
```

## Conclusion

With this practical guide, you should now be able to properly implement and troubleshoot PDF support in your Cantaloupe IIIF server. Remember, the key is always to encode the file paths by replacing slashes with `%2F`. 
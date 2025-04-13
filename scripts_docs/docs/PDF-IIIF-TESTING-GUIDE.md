# PDF-IIIF Testing Guide

This guide provides a systematic approach to testing PDF support in Cantaloupe IIIF server, ensuring integration with InvenioRDM works correctly.

## Table of Contents

1. [Testing Prerequisites](#testing-prerequisites)
2. [Comprehensive Test Cases](#comprehensive-test-cases)
3. [Test Script Implementation](#test-script-implementation)
4. [Manual Testing Steps](#manual-testing-steps)
5. [Interpreting Test Results](#interpreting-test-results)
6. [Continuous Integration](#continuous-integration)

## Testing Prerequisites

Before beginning tests, ensure:

1. **Environment Setup**
   - Cantaloupe IIIF server is running
   - Test PDF files are available in the correct locations
   - Required configuration for PDF support is enabled

2. **Required Test Files**
   - Sample PDF files of various sizes and complexities
   - Test files should be in the correct directories:
     - `/opt/cantaloupe/images/private/{record_id}/{filename}.pdf`
     - `/opt/cantaloupe/images/test/{filename}.pdf`

3. **Test Account**
   - Access to a test account with appropriate permissions

4. **Testing Tools**
   - curl or similar HTTP client for direct API testing
   - Python with requests library for scripted testing
   - Web browser for visual testing of PDF rendering

## Comprehensive Test Cases

### 1. Basic PDF Access Tests

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| PDF-001 | Access PDF info.json with properly encoded path | 200 OK with JSON response containing PDF metadata |
| PDF-002 | Access PDF info.json with non-encoded path | 404 Not Found error |
| PDF-003 | Access first page of PDF as JPEG image | 200 OK with JPEG image content |
| PDF-004 | Access non-existent page number | Error response |
| PDF-005 | Access PDF with various quality parameters | Different quality renderings of the page |

### 2. PDF Manifest Tests

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| MANIFEST-001 | Generate manifest for single-page PDF | Manifest with 1 canvas |
| MANIFEST-002 | Generate manifest for multi-page PDF | Manifest with correct number of canvases |
| MANIFEST-003 | Verify canvas URLs use encoded paths | All resource URLs use %2F encoding |
| MANIFEST-004 | Verify manifest for non-existent PDF | Appropriate error response |
| MANIFEST-005 | Verify manifest metadata | Correct label, description and other metadata |

### 3. Edge Case Tests

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| EDGE-001 | Access very large PDF (>100MB) | Proper handling without timeouts |
| EDGE-002 | Access PDF with special characters in filename | Correct encoding and access |
| EDGE-003 | Access password-protected PDF | Appropriate error handling |
| EDGE-004 | Access PDF with embedded images | Correct rendering of images within the PDF |
| EDGE-005 | Test concurrent access to same PDF | All requests handled without errors |

## Test Script Implementation

### Testing Script: `test_pdf_support.py`

```python
#!/usr/bin/env python3
import requests
import logging
import json
import sys
import os
import time
from urllib.parse import quote

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleCantaloupeProxy:
    """Simple proxy for testing Cantaloupe with PDFs."""
    
    def __init__(self, base_url="http://localhost:8182"):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
    
    def _is_pdf(self, filename):
        """Check if a file is a PDF based on extension."""
        return filename.lower().endswith('.pdf')
    
    def _get_file_path(self, record_id, filename):
        """Get the file path for a record."""
        path = f"private/{record_id}/{filename}"
        # Encode slashes for Cantaloupe
        encoded_path = path.replace("/", "%2F")
        self.logger.info(f"Generated file path: {encoded_path}")
        return encoded_path
    
    def get_pdf_info(self, record_id, filename):
        """Get information about a PDF file from Cantaloupe."""
        if not self._is_pdf(filename):
            return None
        
        encoded_path = self._get_file_path(record_id, filename)
        url = f"{self.base_url}/iiif/2/{encoded_path}/info.json"
        
        self.logger.info(f"Querying Cantaloupe for PDF info at: {url}")
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                self.logger.info("Successfully retrieved PDF info")
                return response.json()
            else:
                self.logger.error(f"Error getting PDF info: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Exception in get_pdf_info: {e}")
            return None
    
    def generate_pdf_manifest(self, record_id, filename, base_url, id_prefix="record"):
        """Generate a IIIF manifest for a PDF file."""
        # Get PDF info
        pdf_info = self.get_pdf_info(record_id, filename)
        if not pdf_info:
            return None
        
        # Default values
        width = pdf_info.get('width', 800)
        height = pdf_info.get('height', 1200)
        
        # Create basic manifest
        manifest = {
            "@context": "http://iiif.io/api/presentation/2/context.json",
            "@type": "sc:Manifest",
            "@id": f"{base_url}/api/iiif/{id_prefix}:{record_id}/manifest",
            "label": "Test PDF Record",
            "metadata": [
                {
                    "label": "Publication Date",
                    "value": time.strftime("%Y-%m-%d")
                }
            ],
            "description": "Manifest generated by InvenioRDM",
            "sequences": [
                {
                    "@id": f"{base_url}/api/iiif/{id_prefix}:{record_id}/sequence/default",
                    "@type": "sc:Sequence",
                    "label": "Current Page Order",
                    "viewingDirection": "left-to-right",
                    "viewingHint": "individuals",
                    "canvases": []
                }
            ]
        }
        
        # Determine number of pages
        num_pages = 0
        if 'tiles' in pdf_info:
            num_pages = len(pdf_info['tiles'])
        elif 'sizes' in pdf_info:
            num_pages = len(pdf_info['sizes'])
            
        if num_pages <= 0:
            num_pages = 1
            
        self.logger.info(f"PDF has {num_pages} pages according to Cantaloupe info.json")
        
        # Create a canvas for each page
        encoded_path = self._get_file_path(record_id, filename)
        
        for page_num in range(1, num_pages + 1):
            canvas_id = f"{base_url}/api/iiif/{id_prefix}:{record_id}:{filename}/canvas/p{page_num:03d}"
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

def test_cantaloupe_direct(record_id, filename):
    """Test direct access to Cantaloupe for a PDF file."""
    # Create path with encoded slashes
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
            
            # Try alternative locations
            alt_paths = [
                f"test/{filename}",
                f"records/{record_id}/{filename}"
            ]
            
            for alt_path in alt_paths:
                encoded_alt_path = alt_path.replace("/", "%2F")
                alt_url = f"http://localhost:8182/iiif/2/{encoded_alt_path}/info.json"
                
                logger.info(f"Trying alternative path: {alt_url}")
                alt_response = requests.get(alt_url)
                
                if alt_response.status_code == 200:
                    logger.info(f"Successfully retrieved PDF info from alternative path: {alt_response.json()}")
                    return True
            
            return False
    except Exception as e:
        logger.error(f"Exception in test_cantaloupe_direct: {e}")
        return False

def test_proxy_directly(record_id, filename):
    """Test the SimpleCantaloupeProxy class directly."""
    proxy = SimpleCantaloupeProxy()
    
    # Test getting PDF info
    pdf_info = proxy.get_pdf_info(record_id, filename)
    if pdf_info:
        logger.info("Successfully retrieved PDF info directly via proxy")
    else:
        logger.error("Failed to retrieve PDF info directly via proxy")
        return False
    
    # Test generating manifest
    manifest = proxy.generate_pdf_manifest(record_id, filename, "https://127.0.0.1:5000")
    if manifest:
        logger.info("Successfully generated manifest")
        return True
    else:
        logger.error("Failed to generate manifest")
        return False

def test_api_manifest(record_id):
    """Test the API manifest endpoint."""
    try:
        url = f"https://127.0.0.1:5000/api/iiif/record:{record_id}/manifest"
        
        logger.info(f"Testing API manifest at: {url}")
        
        # SSL verification is disabled for testing on localhost
        response = requests.get(url, verify=False)
        
        if response.status_code == 200:
            manifest = response.json()
            logger.info(f"Successfully retrieved manifest: {json.dumps(manifest, indent=2)}")
            
            # Check if PDF support is detected
            canvases = manifest.get("sequences", [{}])[0].get("canvases", [])
            logger.info(f"Manifest has {len(canvases)} canvases")
            
            label = manifest.get("label", "")
            description = manifest.get("description", "")
            
            logger.info(f"Manifest label: {label}")
            logger.info(f"Manifest description: {description}")
            
            return True
        else:
            logger.error(f"Error fetching manifest (status {response.status_code}): {response.text}")
            return False
    except Exception as e:
        logger.error(f"Exception in API manifest test: {e}")
        return False

def test_page_access(record_id, filename, page=1):
    """Test accessing a specific page of the PDF."""
    try:
        # Create path with encoded slashes
        path = f"private/{record_id}/{filename}"
        encoded_path = path.replace("/", "%2F")
        
        url = f"http://localhost:8182/iiif/2/{encoded_path}/full/full/0/default.jpg?page={page}"
        logger.info(f"Testing page access: {url}")
        
        response = requests.get(url)
        if response.status_code == 200:
            logger.info(f"Successfully retrieved page {page} (content length: {len(response.content)} bytes)")
            return True
        else:
            logger.error(f"Error fetching page (status {response.status_code})")
            
            # Try alternative path (test directory)
            alt_path = f"test/{filename}"
            encoded_alt_path = alt_path.replace("/", "%2F")
            alt_url = f"http://localhost:8182/iiif/2/{encoded_alt_path}/full/full/0/default.jpg?page={page}"
            
            logger.info(f"Trying alternative path for page access: {alt_url}")
            alt_response = requests.get(alt_url)
            
            if alt_response.status_code == 200:
                logger.info(f"Successfully retrieved page {page} using alternative path (content length: {len(alt_response.content)} bytes)")
                return True
            else:
                logger.error(f"Error fetching page with alternative path (status {alt_response.status_code})")
                return False
    except Exception as e:
        logger.error(f"Exception in page access test: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <record_id> [<filename>]")
        sys.exit(1)
    
    record_id = sys.argv[1]
    filename = "history00871.pdf"  # Default filename
    
    if len(sys.argv) >= 3:
        filename = sys.argv[2]
    
    logger.info(f"Testing PDF support for record {record_id} with file {filename}")
    
    # Run tests
    cantaloupe_direct = test_cantaloupe_direct(record_id, filename)
    proxy_direct = test_proxy_directly(record_id, filename)
    api_manifest = test_api_manifest(record_id)
    page_access = test_page_access(record_id, filename, page=1)
    
    # Print test results
    print("\nTest Results:")
    print(f"Cantaloupe Direct Access: {'PASS' if cantaloupe_direct else 'FAIL'}")
    print(f"SimpleCantaloupeProxy Direct: {'PASS' if proxy_direct else 'FAIL'}")
    print(f"API Manifest: {'PASS' if api_manifest else 'FAIL'}")
    print(f"Page Access: {'PASS' if page_access else 'FAIL'}")
```

## Manual Testing Steps

### 1. Direct Cantaloupe Access Tests

1. **Test PDF info.json Access**
   ```bash
   # With proper encoding (should work)
   curl "http://localhost:8182/iiif/2/private%2F212%2Fhistory00871.pdf/info.json" | python -m json.tool
   
   # Without encoding (should fail)
   curl "http://localhost:8182/iiif/2/private/212/history00871.pdf/info.json"
   ```

2. **Test PDF Page Access**
   ```bash
   # Page 1 with proper encoding
   curl "http://localhost:8182/iiif/2/private%2F212%2Fhistory00871.pdf/full/full/0/default.jpg?page=1" -o page1.jpg
   
   # Page 2 with proper encoding
   curl "http://localhost:8182/iiif/2/private%2F212%2Fhistory00871.pdf/full/full/0/default.jpg?page=2" -o page2.jpg
   ```

3. **Verify Images**
   ```bash
   # Check if images were successfully downloaded
   file page1.jpg page2.jpg
   ```

### 2. API Integration Tests

1. **Test API Manifest**
   ```bash
   # Get manifest through API (SSL verification disabled for localhost)
   curl -k "https://127.0.0.1:5000/api/iiif/record:212/manifest" | python -m json.tool
   ```

2. **Test API Image Access**
   ```bash
   # Access page through API
   curl -k "https://127.0.0.1:5000/api/iiif/record:212:history00871.pdf/full/full/0/default.jpg?page=1" -o api_page1.jpg
   ```

3. **Test in Browser**
   Visit the following URLs in a browser:
   - `https://127.0.0.1:5000/api/iiif/record:212/manifest` (should display JSON)
   - `https://127.0.0.1:5000/api/iiif/record:212:history00871.pdf/full/full/0/default.jpg?page=1` (should display an image)

### 3. Edge Case Testing

1. **Test with Various Image Parameters**
   ```bash
   # Different sizes
   curl "http://localhost:8182/iiif/2/private%2F212%2Fhistory00871.pdf/full/200,/0/default.jpg?page=1" -o page1_200w.jpg
   
   # Different regions
   curl "http://localhost:8182/iiif/2/private%2F212%2Fhistory00871.pdf/100,100,300,300/full/0/default.jpg?page=1" -o page1_region.jpg
   
   # Different quality
   curl "http://localhost:8182/iiif/2/private%2F212%2Fhistory00871.pdf/full/full/0/gray.jpg?page=1" -o page1_gray.jpg
   ```

2. **Test with Special Characters in Filenames**
   If you have PDFs with special characters in their filenames, test them with:
   ```bash
   curl "http://localhost:8182/iiif/2/test%2Fspecial%20filename%2B%24.pdf/info.json"
   ```

## Interpreting Test Results

### Success Indicators

1. **Info.json Access:**
   - Status 200 OK
   - JSON response contains:
     - `width` and `height` values
     - `tiles` or `sizes` array with multiple entries for multi-page PDFs
     - Properly formatted IIIF Image API structure

2. **Page Access:**
   - Status 200 OK
   - Response is a valid image file (JPEG, PNG, etc.)
   - Image content matches the expected page from the PDF

3. **Manifest Generation:**
   - Manifest has the correct number of canvases
   - Canvas URLs use properly encoded paths
   - Image annotations point to valid URLs

### Common Failure Patterns

| Error Pattern | Likely Cause | Solution |
|---------------|--------------|----------|
| 404 Not Found with "No route for path" | Path not encoded | Encode slashes with %2F |
| 404 Not Found without specific message | File doesn't exist | Check file path and existence |
| 500 Internal Server Error | Cantaloupe configuration issue | Check PDF processor configuration |
| Empty canvases array in manifest | Incorrect page detection | Review manifest generation logic |
| Successful response but blank/invalid image | Wrong page parameter | Verify page parameter is correct |

## Continuous Integration

To include PDF-IIIF testing in CI/CD pipelines:

### 1. Test Script for CI

Create a simplified test script (`ci_test_pdf.py`) that returns exit codes:

```python
#!/usr/bin/env python3
import requests
import sys
import json
import time

def test_pdf_support(record_id, filename, cantaloupe_url, api_url):
    """Test basic PDF support for CI."""
    failures = 0
    
    # Test 1: info.json access
    path = f"private/{record_id}/{filename}"
    encoded_path = path.replace("/", "%2F")
    info_url = f"{cantaloupe_url}/iiif/2/{encoded_path}/info.json"
    
    try:
        print(f"Testing info.json access: {info_url}")
        response = requests.get(info_url, timeout=10)
        if response.status_code == 200:
            print("✅ info.json access: PASS")
        else:
            print(f"❌ info.json access: FAIL ({response.status_code})")
            failures += 1
    except Exception as e:
        print(f"❌ info.json access: FAIL (Exception: {e})")
        failures += 1
    
    # Test 2: Page access
    page_url = f"{cantaloupe_url}/iiif/2/{encoded_path}/full/full/0/default.jpg?page=1"
    
    try:
        print(f"Testing page access: {page_url}")
        response = requests.get(page_url, timeout=10)
        if response.status_code == 200 and len(response.content) > 1000:
            print(f"✅ Page access: PASS ({len(response.content)} bytes)")
        else:
            status = response.status_code
            size = len(response.content) if response.status_code == 200 else 0
            print(f"❌ Page access: FAIL (Status: {status}, Size: {size})")
            failures += 1
    except Exception as e:
        print(f"❌ Page access: FAIL (Exception: {e})")
        failures += 1
    
    # Test 3: API manifest
    manifest_url = f"{api_url}/api/iiif/record:{record_id}/manifest"
    
    try:
        print(f"Testing API manifest: {manifest_url}")
        response = requests.get(manifest_url, verify=False, timeout=10)
        if response.status_code == 200:
            manifest = response.json()
            canvases = manifest.get("sequences", [{}])[0].get("canvases", [])
            if canvases:
                print(f"✅ API manifest: PASS ({len(canvases)} canvases)")
            else:
                print("❌ API manifest: FAIL (No canvases)")
                failures += 1
        else:
            print(f"❌ API manifest: FAIL ({response.status_code})")
            failures += 1
    except Exception as e:
        print(f"❌ API manifest: FAIL (Exception: {e})")
        failures += 1
    
    # Return exit code
    return failures

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <record_id> <filename> [<cantaloupe_url> <api_url>]")
        sys.exit(1)
    
    record_id = sys.argv[1]
    filename = sys.argv[2]
    cantaloupe_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8182"
    api_url = sys.argv[4] if len(sys.argv) > 4 else "https://127.0.0.1:5000"
    
    print(f"Testing PDF support for record {record_id} with file {filename}")
    print(f"Cantaloupe URL: {cantaloupe_url}")
    print(f"API URL: {api_url}")
    print("="*50)
    
    failures = test_pdf_support(record_id, filename, cantaloupe_url, api_url)
    
    print("="*50)
    if failures == 0:
        print("✅ All PDF-IIIF tests PASSED")
        sys.exit(0)
    else:
        print(f"❌ {failures} PDF-IIIF tests FAILED")
        sys.exit(1)
```

### 2. GitHub Actions Integration

Example GitHub Actions workflow:

```yaml
name: PDF-IIIF Tests

on:
  push:
    branches: [ main, develop ]
    paths:
      - 'site/zenodo_rdm/iiif/**'
  pull_request:
    branches: [ main, develop ]
    paths:
      - 'site/zenodo_rdm/iiif/**'

jobs:
  test-pdf-support:
    runs-on: ubuntu-latest
    
    services:
      cantaloupe:
        image: edirom/cantaloupe
        ports:
          - 8182:8182
        env:
          CANTALOUPE_PROCESSOR_PDF: PdfBoxProcessor
          CANTALOUPE_SOURCE_STATIC: FilesystemSource
        volumes:
          - ./test_data:/opt/cantaloupe/images/test
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests pytest
      
      - name: Copy test PDFs to Cantaloupe
        run: |
          mkdir -p test_data/private/212
          cp test_fixtures/pdfs/sample.pdf test_data/private/212/history00871.pdf
      
      - name: Run PDF-IIIF tests
        run: |
          python scripts/ci_test_pdf.py 212 history00871.pdf http://localhost:8182
      
      - name: Output test artifacts
        if: always()
        run: |
          curl "http://localhost:8182/iiif/2/private%2F212%2Fhistory00871.pdf/full/full/0/default.jpg?page=1" -o page1.jpg || true
          curl "http://localhost:8182/iiif/2/private%2F212%2Fhistory00871.pdf/info.json" -o info.json || true
      
      - name: Upload test artifacts
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: pdf-iiif-test-artifacts
          path: |
            page1.jpg
            info.json
```

## Conclusion

This testing guide provides a comprehensive approach to verify PDF support in Cantaloupe IIIF server. By following these testing procedures, you can ensure that:

1. PDF files are properly accessed through Cantaloupe
2. File paths are correctly encoded with slashes replaced by %2F
3. PDF pages can be retrieved as images
4. PDF manifests are correctly generated with the proper number of canvases
5. The integration between InvenioRDM and Cantaloupe works for PDF files

Remember that the key to successful PDF support is proper URL encoding, especially replacing slashes with %2F in all file paths sent to Cantaloupe. 
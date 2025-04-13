# PDF IIIF Integration Troubleshooting Guide

![Troubleshooting Workflow](https://mermaid.ink/img/pako:eNplksFuwjAMhl_FyhnaHpBgsDFpGqcdJnFgO0RVlIbQoUISmoRpE-_OkwCDjR38-_-_2I59DLkxFjSsy3z_ZmvwzmQYtlk5C7ZrjLeM6FFwpeVmR5BHWbOh1YLQH-ZFW5hCf1qwMS4-VaKLEXoglYuwFnMeGul8OuN9CkWL642JOGBn3aBPL1BFzj02GBqdoWVDUJSExVZ-3hWdhUnlFQ8OSS23g6MenF8w7GEavjiBV4nhlTHPAi9LCf9MnPDCc9bdc5JrGqTtdDjWA8-e136FXi-SdawtbI_lGXo0Rp5eCxs0ewIZo8elKxAn2uxGzecBFsZWtGWgLwlnfXjWjy13nYe0sXVFg069wm8sx8aac6G5_H6gfrOxAQ0bbdBKOBgN7X_YsSu7r6r2Fk16Ef7J3hUa0ufZeZrNZmn-Mk3TNMsg66PQcDBGHomCS1W3qQw1OTmaIXfNWGTnIUryUYsWX0dmCL0uhKwaoGTbhtGKzRGuc1Mt25b5AoEBxow?type=png)

## Table of Contents

1. [Introduction](#introduction)
2. [Diagnosing Issues](#diagnosing-issues)
3. [Common Issues and Solutions](#common-issues-and-solutions)
4. [Advanced Troubleshooting](#advanced-troubleshooting)
5. [Debugging Tools](#debugging-tools)
6. [Configuration Issues](#configuration-issues)
7. [API Errors and Fixes](#api-errors-and-fixes)

## Introduction

This guide provides troubleshooting steps for issues that might arise when working with PDF files in the IIIF integration with Zenodo RDM. The PDF IIIF integration relies on the Cantaloupe image server to handle PDF files directly, rather than converting them to another format like PTIF.

## Diagnosing Issues

Before diving into specific fixes, follow this general diagnostic approach:

1. **Identify the Layer**: Determine if the issue is with:
   - The Zenodo RDM application
   - The IIIF proxy implementation
   - The Cantaloupe server
   - The file storage

2. **Check Logs**: Look at logs for each component:
   ```bash
   # Zenodo RDM logs
   docker-compose logs web
   
   # Cantaloupe logs
   docker-compose logs cantaloupe
   ```

3. **Test Direct Access**: Try accessing the PDF directly through Cantaloupe:
   ```bash
   curl -I "http://localhost:8182/iiif/2/images%2Fprivate%2F<record_id>%2F<filename>.pdf/info.json"
   ```

4. **Verify File Presence**: Check if the PDF file is in the expected location:
   ```bash
   docker-compose exec cantaloupe find /opt/cantaloupe/images -name "*.pdf"
   ```

## Common Issues and Solutions

### 1. Record Creation Errors

#### Issue: Missing Required Fields

```
{"status": 400, "message": "A validation error occurred.", "errors": [{"field": "metadata.resource_type", "messages": ["Missing data for required field."]}]}
```

**Solution:**
- Ensure your record metadata includes all required fields:
  - `title` 
  - `publication_date`
  - `creators` (with `family_name`, `given_name` and `type` specified)
  - `resource_type` with `id` field
  - `publisher` for DOI registration
  - `license` with `id` field
  - `access_right` with `id` field

#### Issue: Bucket Locked for Modifications

```
{"status": 403, "message": "Bucket is locked for modifications."}
```

**Solution:**
- Create a new record instead of trying to modify an existing one
- Or, create a new version of the record:
  ```bash
  curl -X POST -H "Authorization: Bearer $API_TOKEN" \
       "https://127.0.0.1:5000/api/records/<record_id>/versions" -k
  ```

### 2. File Upload Issues

#### Issue: File Upload Fails

```
{"status": 500, "message": "Internal server error"}
```

**Solution:**
- Check file size (there may be upload limits)
- Ensure the file is a valid PDF
- Try uploading a smaller test PDF first

#### Issue: File Not Committed

```
{"status": 400, "message": "A validation error occurred.", "errors": [{"field": "files", "messages": ["One or more files have not completed their transfer, please wait."]}]}
```

**Solution:**
- Make sure to call the commit endpoint for each uploaded file before publishing:
  ```bash
  curl -X POST -H "Authorization: Bearer $API_TOKEN" \
       "https://127.0.0.1:5000/api/records/<record_id>/draft/files/<filename>/commit" -k
  ```

### 3. Cantaloupe Issues

#### Issue: PDF Not Found in Cantaloupe

```
HTTP/1.1 404 Not Found
```

**Solution:**
1. Verify the PDF path is correct:
   ```bash
   docker-compose exec cantaloupe find /opt/cantaloupe/images -name "*.pdf"
   ```

2. Check if your PDF record was published correctly:
   ```bash
   curl -H "Authorization: Bearer $API_TOKEN" \
        "https://127.0.0.1:5000/api/records/<record_id>" -k
   ```

3. Ensure the volumes in docker-compose.yml are properly mapped:
   ```yaml
   cantaloupe:
     volumes:
       - ./data:/opt/cantaloupe/images
   ```

#### Issue: Cannot Access PDF Pages

```
HTTP/1.1 400 Bad Request
```

**Solution:**
1. Ensure you're using the correct page parameter:
   ```
   ?page=1  # Page numbers start from 1, not 0
   ```

2. Check if Cantaloupe has PDF support enabled in its properties:
   ```properties
   # In cantaloupe.properties
   processor.pdf = PdfBoxProcessor
   ```

3. Verify the PDF isn't corrupted:
   ```bash
   docker-compose exec cantaloupe pdfinfo /opt/cantaloupe/images/images/private/<record_id>/<filename>.pdf
   ```

### 4. IIIF Manifest Issues

#### Issue: Manifest Not Generated

```
HTTP/1.1 404 Not Found
```

**Solution:**
1. Check if the IIIF resource is properly configured:
   ```python
   # In site/zenodo_rdm/config.py
   class ZenodoIIIFResourceConfig(IIIFResourceConfig):
       proxy_cls = CantaloupeProxy
   ```

2. Verify the record has IIIF-supported files:
   ```bash
   curl -H "Authorization: Bearer $API_TOKEN" \
        "https://127.0.0.1:5000/api/records/<record_id>/files" -k
   ```

3. Refresh the IIIF cache:
   ```bash
   curl -X DELETE -H "Authorization: Bearer $API_TOKEN" \
        "https://127.0.0.1:5000/api/records/<record_id>/cache" -k
   ```

#### Issue: PDF Not Showing in Manifest

**Solution:**
1. Ensure PDF is in the list of supported formats:
   ```python
   # In invenio.cfg
   RDM_IIIF_MANIFEST_FORMATS = ["jpeg", "jpg", "png", "tiff", "tif", "pdf"]
   ```

2. Check if the PDF detection method is working:
   ```python
   # In site/zenodo_rdm/iiif/proxy.py
   def _is_pdf(self, filename):
       return filename.lower().endswith('.pdf')
   ```

## Advanced Troubleshooting

### Debugging the CantaloupeProxy

To debug issues with the CantaloupeProxy class, you can create a simple test script:

```python
# debug_proxy.py
from flask import Flask
from zenodo_rdm.iiif.proxy import CantaloupeProxy

app = Flask(__name__)
with app.app_context():
    proxy = CantaloupeProxy()
    
    # Test PDF detection
    print(f"Is PDF: {proxy._is_pdf('test.pdf')}")
    
    # Test URL generation
    url = proxy.build_cantaloupe_url("123", "document.pdf", page=1)
    print(f"Generated URL: {url}")
    
    # Test info.json
    try:
        info = proxy.get_pdf_info("123", "document.pdf")
        print(f"PDF info: {info}")
    except Exception as e:
        print(f"Error getting PDF info: {e}")
```

Run it with:
```bash
FLASK_APP=debug_proxy.py flask shell
```

### Testing IIIF URLs Directly

To test if the issue is with Cantaloupe or the proxy, try accessing the Cantaloupe server directly:

```bash
# Get PDF metadata
curl "http://localhost:8182/iiif/2/images%2Fprivate%2F<record_id>%2F<filename>.pdf/info.json" | jq .

# Get a specific page (save to file)
curl "http://localhost:8182/iiif/2/images%2Fprivate%2F<record_id>%2F<filename>.pdf/full/full/0/default.jpg?page=1" -o test_page.jpg
```

### Checking File Permission Issues

If Cantaloupe can't access the PDF files:

```bash
# Check permissions
docker-compose exec cantaloupe ls -la /opt/cantaloupe/images/images/private/<record_id>/

# Fix permissions if needed
docker-compose exec cantaloupe chmod 644 /opt/cantaloupe/images/images/private/<record_id>/<filename>.pdf
```

## Configuration Issues

### Cantaloupe Configuration

If you're having issues with Cantaloupe, check these settings in `cantaloupe.properties`:

```properties
# Enable PDF support
processor.pdf = PdfBoxProcessor

# Set cache directory
FilesystemCache.pathname = /opt/cantaloupe/cache

# Base directory for source images
FilesystemSource.BasicLookupStrategy.path_prefix = /opt/cantaloupe/images

# URL paths
server.endpoint.api.enabled = true
server.endpoint.api.base_uri = /iiif/2
```

### Zenodo RDM Configuration

Check these settings in `invenio.cfg`:

```python
# Cantaloupe server URL
RDM_IIIF_SERVER_URL = "http://localhost:8182"

# Use our CantaloupeProxy class
IIIF_PROXY_CLASS = "zenodo_rdm.iiif.proxy:CantaloupeProxy"

# Add PDF to supported formats
RDM_IIIF_MANIFEST_FORMATS = ["jpeg", "jpg", "png", "tiff", "tif", "pdf"]
```

## API Errors and Fixes

| HTTP Status | Error Message | Possible Cause | Solution |
|-------------|---------------|----------------|----------|
| 400 | "Missing data for required field" | Incomplete metadata | Add all required fields |
| 403 | "Permission denied" | Invalid or expired token | Generate a new token |
| 403 | "Bucket is locked for modifications" | Record is published | Create a new version |
| 404 | "Not found" | Resource doesn't exist | Check record ID and file paths |
| 500 | "Internal server error" | Various server-side issues | Check application logs |

---

*This troubleshooting guide is based on real-world testing and debugging of the PDF IIIF integration in Zenodo RDM. If you encounter additional issues, please update this guide with your findings.* 
# PDF Support in Cantaloupe IIIF Server: Integration Guide

## Introduction

This guide documents how to properly integrate PDF support with Cantaloupe IIIF server in the InvenioRDM platform. It explains common challenges, solutions, and best practices based on real debugging experiences.

## The URL Encoding Challenge

### Problem

The primary challenge with PDF support in Cantaloupe is the handling of file paths. When accessing PDF files through Cantaloupe, the server expects the file path to be URL-encoded, with slashes `/` represented as `%2F`. If this encoding is not performed, the server returns a 404 error with messages like:

```
No route for path: /iiif/2/private/212/history00871.pdf/info.json
```

### Root Cause

Cantaloupe processes the URL identifiers differently depending on whether they contain encoded slashes. When a path like `/private/212/filename.pdf` is sent without encoding, Cantaloupe treats `/private/212/filename.pdf` as a single identifier and fails to locate the file. When properly encoded as `private%2F212%2Ffilename.pdf`, Cantaloupe can correctly parse and locate the file.

## Solution: URL Encoding in the Proxy

The solution is to properly encode file paths by replacing slashes with `%2F` in all methods that interact with Cantaloupe:

```python
# Instead of using the path directly
file_path = f"private/{record_id}/{filename}"
cantaloupe_url = f"{base_url}/iiif/2/{file_path}/info.json"

# Use URL encoding for slashes
file_path = f"private/{record_id}/{filename}"
encoded_path = file_path.replace("/", "%2F")
cantaloupe_url = f"{base_url}/iiif/2/{encoded_path}/info.json"
```

## Implementation Details

### Key Methods Updated

The following methods in the `CantaloupeProxy` class need to be updated:

1. `build_cantaloupe_url` - Encode file paths when constructing URLs
2. `get_pdf_info` - Ensure the PDF info URL uses encoded paths
3. `generate_pdf_manifest` - Generate IIIF manifests with encoded paths
4. `proxy` - Update to handle encoded paths for routing
5. `proxy_request` - Ensure the proxy requests use encoded paths
6. `stream_image` - Stream images with proper encoding, including page parameters

### Example: Updated build_cantaloupe_url Method

```python
def build_cantaloupe_url(self, record_id, filename, region, size, rotation, quality, format, page=None):
    """Build a URL for the Cantaloupe server.
    
    Parameters:
        record_id (str): The ID of the record
        filename (str): The filename of the image
        region (str): The region of the image to use
        size (str): The size of the image
        rotation (str): The rotation of the image
        quality (str): The quality of the image
        format (str): The format of the image
        page (int): The page number for PDFs (optional)
    
    Returns:
        str: The URL to fetch the image from Cantaloupe
    """
    file_path = self._get_file_path(record_id, filename)
    
    # Encode slashes in the path for Cantaloupe
    encoded_path = file_path.replace("/", "%2F")
    
    # Create the URL with the encoded path
    if region == "info.json":
        url = f"{self.base_url}/iiif/2/{encoded_path}/info.json"
    else:
        url = f"{self.base_url}/iiif/2/{encoded_path}/{region}/{size}/{rotation}/{quality}.{format}"
    
    # Add page parameter for PDFs if specified
    if page is not None and self._is_pdf(filename):
        url += f"?page={page}"
    
    return url
```

## Testing PDF Support

### Manual Testing

You can test PDF support using curl commands:

```bash
# Access PDF info
curl -k "http://localhost:8182/iiif/2/private%2F212%2Fhistory00871.pdf/info.json"

# Get a specific page as an image
curl -k "http://localhost:8182/iiif/2/private%2F212%2Fhistory00871.pdf/full/full/0/default.jpg?page=1" -o test_page.jpg
```

### Automated Testing

We've created a test script in `scripts/AlA/test_pdf_manifest.py` that verifies PDF support:

```bash
cd scripts/AlA
python test_pdf_manifest.py 212
```

The script runs four tests:
1. Direct Cantaloupe access
2. SimpleCantaloupeProxy direct access
3. API manifest generation
4. PDF page access

## Common Errors and Solutions

### 1. "No route for path" Error

**Error:** 
```
404 Not Found - No route for path: /iiif/2/private/212/history00871.pdf/info.json
```

**Solution:** 
Encode slashes in the path with `%2F`:
```python
encoded_path = path.replace("/", "%2F")
```

### 2. Empty Canvases in Manifest

**Error:**
The manifest is retrieved but has an empty canvases array.

**Solution:**
Ensure the `generate_pdf_manifest` method correctly:
1. Retrieves PDF info with encoded paths
2. Properly determines the number of pages
3. Creates a canvas for each page with properly encoded URLs

### 3. PDF Page Not Found

**Error:**
```
Error streaming image: 404 Client Error: Not Found
```

**Solution:**
1. Verify the page parameter is being passed correctly: `?page=1`
2. Ensure the file path is properly encoded
3. Confirm the PDF file exists at the expected location

## Deployment Considerations

When deploying PDF support:

1. **Path Configuration:** Ensure Cantaloupe's `FilesystemSource.BasicLookupStrategy.path_prefix` is correctly set.
2. **PDF Processor:** Verify Cantaloupe has the PDF processor enabled with `CANTALOUPE_PROCESSOR_PDF=PdfBoxProcessor`.
3. **Memory Allocation:** PDFs can be memory-intensive; consider increasing Java heap size for large PDFs.
4. **Testing:** Test with various PDF files, especially large or complex ones.

## Conclusion

PDF support in Cantaloupe requires proper URL encoding of file paths, replacing slashes with `%2F`. With the changes outlined in this guide, your InvenioRDM instance should now correctly handle PDF files through the IIIF server, enabling viewing of PDF pages as images and generating proper IIIF manifests. 
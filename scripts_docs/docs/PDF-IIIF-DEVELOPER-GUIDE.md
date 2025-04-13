# PDF IIIF Integration: Developer Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Implementation Details](#implementation-details)
4. [Key Concepts](#key-concepts)
5. [Code Structure](#code-structure)
6. [Common Challenges and Solutions](#common-challenges-and-solutions)
7. [How-To Guide](#how-to-guide)
8. [Testing Your Implementation](#testing-your-implementation)
9. [Testing Before Installation](#testing-before-installation)
10. [Debugging Tips](#debugging-tips)
11. [Performance Considerations](#performance-considerations)

## Introduction

This guide provides a comprehensive overview of the PDF IIIF integration with Zenodo RDM. It's designed to help developers understand how PDF files are integrated with the IIIF framework in Zenodo RDM, how the Cantaloupe image server is leveraged for PDF support, and how to extend, maintain, and debug the implementation.

### What is IIIF?

The International Image Interoperability Framework (IIIF) is a set of open APIs that provide a standardized way of viewing, zooming, comparing, annotating, and sharing images across repositories and image servers. In the context of Zenodo RDM, IIIF allows for the viewing of images and PDFs through a standardized interface.

### What is Cantaloupe?

Cantaloupe is an open-source image server that implements the IIIF Image API. It supports a wide range of image formats, including JPEG, TIFF, PNG, and importantly for our implementation, PDF. It allows for the dynamic resizing, cropping, rotation, and format conversion of images on-the-fly.

## Architecture Overview

![Architecture Diagram](https://mermaid.ink/img/pako:eNqNkk9PwzAMxb9KlHMR_QBcUCeQEBIc9jdwSN3UWnGSOY5gQvvuOO3GNnFA4mTrPT_7ydERucmQB9yp8vQS-UqBdnCXgYn8pCw4j1JB5EzjXVnFY2lL7TmKtSotYzz1Pbo0w-g9KPYmC7B1cFDtYCsbpStfGdCFbm3Zj4S9Z1DWKwvGo9pjMDmYxOp_vKtrzPcLfxFaF2nC56oLlzHb1OYk6-RXg3Oyt-7Pk3KUWngC5VwL2a-1S9JO3i-Vg6KDnRrGFoTBx1hWdh-GJm74sUyVgZsELBzAGkVprNq2UEtLRMa5cTm2-H4wP22OzjO4I2PpO0cXBzxDxmMCpPOaB1zz2EkX0JoS95zHxCB_-Z7XPDQdvRSf5a6qWZukYXQM9r2mD7KNAptOGD7sZtH4AYjNlgI?type=png)

The architecture of our PDF IIIF integration involves several components:

1. **Web Browser/Client**: Sends requests to view PDFs or images through the IIIF interface.
2. **Zenodo RDM Web Application**: Receives and processes the request, determining if it should handle it directly or proxy to Cantaloupe.
3. **CantaloupeProxy Class**: A custom class that implements the IIIFProxy interface, handling PDF-specific logic and proxying requests to the Cantaloupe server.
4. **Cantaloupe Image Server**: Processes the IIIF image requests for PDFs, returning the appropriate response.
5. **File Storage**: Where the actual PDF files are stored.

### Request Flow

1. User requests a PDF page through the IIIF URL.
2. Request reaches Zenodo RDM web application.
3. The application identifies it as an IIIF request and routes it to the appropriate IIIF resource handler.
4. The `ZenodoIIIFResource` passes the request to the `CantaloupeProxy`.
5. `CantaloupeProxy` determines it's a PDF request, constructs the appropriate URL for Cantaloupe, and proxies the request.
6. Cantaloupe processes the request, extracting the appropriate page from the PDF, applying any transformations (resize, crop, etc.), and returns the image.
7. The proxy returns this response to the user.

## Implementation Details

### Extending the Invenio RDM Framework

Our implementation extends the base Invenio RDM IIIF functionality. Here's what we inherited and extended:

#### Base Classes:
- `IIIFProxy` (Abstract): Defines the interface for IIIF proxies
- `IIIFResource`: Handles IIIF requests and routes them appropriately
- `IIIFManifestV2Schema`: Defines the structure of IIIF manifests

#### Our Extensions:
- `CantaloupeProxy`: Extends `IIIFProxy` to handle PDF files
- `ZenodoIIIFResource`: Extends `IIIFResource` to use our custom serializer
- `ZenodoIIIFManifestV2Schema`: Extends `IIIFManifestV2Schema` to include additional metadata

### Key Implementation Files

| File | Purpose |
|------|---------|
| `site/zenodo_rdm/iiif/proxy.py` | Contains the `CantaloupeProxy` class that handles the proxying of IIIF requests for PDFs to Cantaloupe |
| `site/zenodo_rdm/iiif/resource.py` | Contains the `ZenodoIIIFResource` class that extends the base IIIF resource |
| `site/zenodo_rdm/iiif/schema.py` | Contains the `ZenodoIIIFManifestV2Schema` that enhances manifests with additional metadata |
| `site/zenodo_rdm/iiif/serializers.py` | Contains the `ZenodoIIIFManifestV2JSONSerializer` that uses our custom schema |
| `site/zenodo_rdm/iiif/__init__.py` | Exports the `CantaloupeProxy` class |
| `site/zenodo_rdm/config.py` | Contains the `ZenodoIIIFResourceConfig` that configures the IIIF resource |
| `invenio.cfg` | Contains configuration settings for the IIIF integration |

## Key Concepts

### 1. The IIIFProxy Interface

The `IIIFProxy` abstract base class defines the interface for proxying requests to a IIIF server:

```python
class IIIFProxy(ABC):
    """IIIF Proxy interface."""

    def should_proxy(self):
        """Check if the current request should be proxied."""
        return request.endpoint in (
            "iiif.image_api",
            "iiif.info",
        )

    @abstractmethod
    def proxy_request(self):
        """Proxy the current request to IIIF server."""

    def __call__(self):
        """Proxy request to IIIF server if the endpoint is configured."""
        if self.should_proxy():
            return self.proxy_request()
        return None
```

### 2. The CantaloupeProxy Implementation

Our `CantaloupeProxy` class implements the `IIIFProxy` interface, adding PDF-specific functionality:

```python
class CantaloupeProxy(IIIFProxy):
    """Proxy for Cantaloupe image server with PDF support."""

    def __init__(self, server_url=None, base_path=None):
        """Initialize the proxy."""
        self.server_url = server_url
        self.base_path = base_path or "images/private"

    @property
    def server_url(self):
        """IIIF server URL."""
        if hasattr(self, '_server_url') and self._server_url:
            return self._server_url
        return current_app.config.get("RDM_IIIF_SERVER_URL", "http://localhost:8182")
    
    @server_url.setter
    def server_url(self, value):
        """Set the server URL."""
        self._server_url = value

    def should_proxy(self):
        """Check if the current request should be proxied."""
        # First check Invenio RDM's standard endpoints
        standard_endpoints = super().should_proxy()
        if standard_endpoints:
            return True
            
        # Then check our custom URL pattern if needed
        if request.path.startswith('/api/iiif/record:'):
            return self.is_iiif_request(request.path)
        
        return False

    def proxy_request(self):
        """Proxy the current request to Cantaloupe server."""
        # Implementation details...
```

### 3. IIIF URL Structure

IIIF URLs follow a specific structure for image requests:

```
{scheme}://{server}{/prefix}/{identifier}/{region}/{size}/{rotation}/{quality}.{format}
```

Example:
```
https://example.org/iiif/2/record:123:document.pdf/full/800,/0/default.jpg?page=2
```

Where:
- `scheme`: HTTP or HTTPS
- `server`: Domain name
- `prefix`: Optional path prefix (e.g., `/iiif/2`)
- `identifier`: Resource identifier (e.g., `record:123:document.pdf`)
- `region`: Part of the image to return (e.g., `full`, `100,100,300,300`)
- `size`: Dimensions to which the image should be resized (e.g., `full`, `800,`, `!800,600`)
- `rotation`: Rotation in degrees (e.g., `0`, `90`, `180`, `270`)
- `quality`: Quality layer (e.g., `default`, `color`, `gray`)
- `format`: Image format (e.g., `jpg`, `png`, `gif`)
- `page`: Optional query parameter for PDF page number

### 4. PDF vs PTIF Handling

Our implementation handles two types of files differently:

- **PTIF Files**: Legacy pyramid TIFF files used by the IIPImage server
  - Path structure: `ch1/ch2/tail/filename.ptif` where `ch1`, `ch2`, and `tail` are partitioned record IDs
  
- **PDF Files**: Handled directly by Cantaloupe
  - Path structure: `images/private/{record_id}/{filename}`
  - Additional `page` parameter for selecting specific pages

## Code Structure

![Code Structure Diagram](https://mermaid.ink/img/pako:eNqdlE9v2zAMxb-KoFMK5APkkAZdsBbbsGK3DAl2CAzDsBXZQmXJkKQgLeLvPjlxnLTrgV0s6vGR_Mkn-Y0SYzCZ0NFKuuU6oGITmIBzoO9uiTrgoGsgGBzNGQMFDMuxwLlBBQ53oA20pBUsdGtQKwhrMMgvOSRnBzW2GiiBUhprVLiBFx9kgxnK8vD-uXO2eFu0fMxJiB8bZeAAZJD8slXGkmzA4UrClN4WGmjnRBrDEoSG5yEHdLa29AOFV17aZM08P-p1KFBq4CXVqxJN22B_K5H4f5_i_XpJKXm4_GGJnQMG4w0HV9dZVqL0CZFJr6xf0QO2Vvs_h9U5dOLVgWXQcR-f_wXUFhRa2yMkd2LCuQ9oNXhqBG17kXY03xGzJhZUcfV5QCYMh8e4C-rT9iIZLCTGZ9fDR_TaL2Bd7yWNkbShm4KvBjT4fBZcLGhR0E4ovSu5HyafqVwb3BYJ-CZlJTRg-zr2nHXCK6NKKnXM9TTkOhLn-UuQukLLW-RJhZzFYCsRtmQw82Av9bZOlumIXJa8i9hbv8pnkUwmk25SDiEXTbL3Mh7yfjGZ-s_xvpM9_PpRk_-IzfWtMsE5ydO8-J7PLsrz8uJ6Wsx-lFdXeVFczqdzuk3nNClmOGXBLdwNxm-Q5TvIIzDTnPazvb4PSf8YUeWxfrE92YiZuZS7LPuZxjC9eDUbTrqQk3xejqE_J-XlYH8fQYexuxdg?type=png)

The implementation follows a clear structure where each class has a specific responsibility:

1. **CantaloupeProxy**: Handles the proxying of IIIF requests to Cantaloupe
2. **ZenodoIIIFResource**: Extends the base IIIF resource to use our custom serializer
3. **ZenodoIIIFManifestV2Schema**: Enhances the manifest schema with additional metadata
4. **ZenodoIIIFManifestV2JSONSerializer**: Uses our custom schema to serialize manifests

## Common Challenges and Solutions

### Challenge 1: Path Structure Differences

**Problem**: Cantaloupe and IIPImage use different path structures for files.

**Solution**: We implemented a method to detect file type and generate the appropriate path:

```python
def _get_file_path(self, record_id, filename):
    """Get the file path for a record file."""
    if self._is_pdf(filename):
        # Path structure for PDFs in Cantaloupe
        return f"images/private/{record_id}/{filename}"
    else:
        # Legacy PTIF structure with partitioned record ID
        recid_str = str(record_id)
        ch1 = recid_str[0:2].ljust(2, '_')
        ch2 = recid_str[2:4].ljust(2, '_')
        tail = recid_str[4:].ljust(1, '_')
        
        # Use .ptif extension for non-PDF image files
        base_name = os.path.splitext(filename)[0]
        return f"{ch1}/{ch2}/{tail}/{base_name}.ptif"
```

### Challenge 2: URL Pattern Recognition

**Problem**: We needed to handle both standard Invenio RDM IIIF URLs and our custom URL pattern.

**Solution**: We extended the `should_proxy` method to check both patterns:

```python
def should_proxy(self):
    """Check if the current request should be proxied."""
    # First check Invenio RDM's standard endpoints
    standard_endpoints = super().should_proxy()
    if standard_endpoints:
        return True
        
    # Then check our custom URL pattern if needed
    if request.path.startswith('/api/iiif/record:'):
        return self.is_iiif_request(request.path)
    
    return False
```

### Challenge 3: PDF Page Selection

**Problem**: PDFs have multiple pages, but IIIF doesn't natively support page selection.

**Solution**: We added a `page` query parameter to select specific PDF pages:

```python
def build_cantaloupe_url(self, record_id, filename, region='full', size='full', 
                        rotation=0, quality='default', format='jpg', page=None, 
                        **kwargs):
    # Implementation...
    
    # Add page parameter for PDFs if specified
    if page is not None and self._is_pdf(filename):
        kwargs['page'] = page
    
    # Add any additional query parameters
    if kwargs:
        query_string = urllib.parse.urlencode(kwargs)
        url = f"{url}?{query_string}"
    
    return url
```

### Challenge 4: Server URL Configuration

**Problem**: The server URL needs to be configurable both at initialization and through Flask's config.

**Solution**: We implemented a property with a setter to handle both cases:

```python
@property
def server_url(self):
    """IIIF server URL."""
    if hasattr(self, '_server_url') and self._server_url:
        return self._server_url
    return current_app.config.get("RDM_IIIF_SERVER_URL", "http://localhost:8182")

@server_url.setter
def server_url(self, value):
    """Set the server URL."""
    self._server_url = value
```

### Challenge 5: Import Path Problems

**Problem**: The proper importing of the `CantaloupeProxy` class in configuration.

**Solution**: Ensure the proper import path is used in `invenio.cfg`:

```python
IIIF_PROXY_CLASS = "zenodo_rdm.iiif.proxy:CantaloupeProxy"
```

## How-To Guide

### How to Configure the IIIF Proxy

1. In `invenio.cfg`, add or modify the following settings:

```python
# Enable IIIF server
IIIF_SERVER_ENABLED = True
IIIF_PREVIEW_ENABLED = True

# Set Cantaloupe server URL
RDM_IIIF_SERVER_URL = "http://localhost:8182"

# Set our custom proxy class
IIIF_PROXY_CLASS = "zenodo_rdm.iiif.proxy:CantaloupeProxy"

# Add PDF to supported formats
RDM_IIIF_MANIFEST_FORMATS = ["jpeg", "jpg", "png", "tiff", "tif", "pdf"]
```

### How to Use the IIIF API for PDFs

1. **Base URL Format**:
   ```
   /api/iiif/record:<record_id>:<filename>/<region>/<size>/<rotation>/<quality>.<format>?page=<page_number>
   ```

2. **Example for Full Page**:
   ```
   /api/iiif/record:123:document.pdf/full/800,/0/default.jpg?page=1
   ```

3. **Example for Region of a Page**:
   ```
   /api/iiif/record:123:document.pdf/100,100,300,300/full/0/default.jpg?page=2
   ```

4. **Get PDF Info**:
   ```
   /api/iiif/record:123:document.pdf/info.json?page=1
   ```

### How to Test the Implementation

You can use the provided Makefile targets to test the implementation:

```bash
# Test the CantaloupeProxy with a specific PDF file
make -f scripts/AlA/Makefile test-cantaloupe-proxy RECORD=123 FILE=document.pdf MANIFEST=1

# Test with a specific page
make -f scripts/AlA/Makefile test-cantaloupe-proxy RECORD=123 FILE=document.pdf PAGE=2 MANIFEST=1
```

## Testing Your Implementation

### Basic Functionality Testing

1. **Test URL Generation**:
   ```python
   proxy = CantaloupeProxy()
   url = proxy.build_cantaloupe_url("123", "document.pdf", page=1)
   print(url)  # Should output a valid Cantaloupe URL
   ```

2. **Test PDF Info Retrieval**:
   ```python
   proxy = CantaloupeProxy()
   info = proxy.get_pdf_info("123", "document.pdf")
   print(info)  # Should output the PDF metadata
   ```

3. **Test Manifest Generation**:
   ```bash
   make -f scripts/AlA/Makefile test-cantaloupe-proxy RECORD=123 FILE=document.pdf MANIFEST=1
   ```

### Integration Testing

1. **Test in Browser**:
   Open a browser and navigate to:
   ```
   http://localhost:5000/api/iiif/record:123:document.pdf/full/800,/0/default.jpg?page=1
   ```

2. **Test with Universal Viewer**:
   ```
   http://localhost:5000/api/iiif/record:123:document.pdf/manifest
   ```

## Testing Before Installation

Before installing the IIIF implementation to site-packages, you can test it to ensure it works correctly. We've provided a comprehensive test suite that verifies the core functionality.

### Running the Test Suite

Execute the test runner script:

```bash
python test/run_iiif_tests.py
```

This script runs all the IIIF component tests and reports any issues. It tests:

1. **Basic component functionality**: URL generation, path handling, PDF detection
2. **Flask integration**: Server URL configuration, request proxying
3. **Schema and serializer functionality**: Metadata enhancement

### What the Tests Verify

The test suite verifies:

- **CantaloupeProxy class**:
  - Server URL configuration (both direct and from Flask config)
  - PDF file detection
  - File path generation for both PDF and PTIF files
  - URL generation with various parameters
  - Request proxying logic

- **ZenodoIIIFManifestV2Schema class**:
  - Metadata enhancement with creators, resource type, and keywords
  - Proper formatting of metadata values

- **Flask Integration**:
  - Proper behavior within Flask application context
  - Correct handling of request routing
  - URL pattern recognition

### Test Components

The test suite consists of the following components:

1. **test_iiif_components.py**: Tests basic functionality without Flask context
2. **test_iiif_flask_integration.py**: Tests components within a Flask application context
3. **run_iiif_tests.py**: Main runner script that executes all tests

### Sample Test Output

A successful test run should look like:

```
=== Running IIIF Component Tests ===

Verifying IIIF module imports...
✅ All IIIF modules imported successfully

Running test_iiif_components...
test_build_cantaloupe_url (test_iiif_components.TestCantaloupeProxy) ... ok
test_get_file_path (test_iiif_components.TestCantaloupeProxy) ... ok
test_is_pdf (test_iiif_components.TestCantaloupeProxy) ... ok
test_server_url (test_iiif_components.TestCantaloupeProxy) ... ok
test_get_metadata (test_iiif_components.TestZenodoIIIFManifestV2Schema) ... ok

Running test_iiif_flask_integration...
test_get_pdf_info_in_context (test_iiif_flask_integration.TestCantaloupeProxyWithFlask) ... ok
test_server_url_from_config (test_iiif_flask_integration.TestCantaloupeProxyWithFlask) ... ok
test_should_proxy_custom_endpoint (test_iiif_flask_integration.TestCantaloupeProxyWithFlask) ... ok
test_should_proxy_standard_endpoint (test_iiif_flask_integration.TestCantaloupeProxyWithFlask) ... ok
test_iiif_image_api_route (test_iiif_flask_integration.TestProxyIntegration) ... ok
test_iiif_info_route (test_iiif_flask_integration.TestProxyIntegration) ... ok

✅ All IIIF tests passed! The implementation is ready for installation.
```

If any tests fail, you should address the issues before installing the implementation.

### Common Test Failures

1. **Import Errors**: Make sure the site/zenodo_rdm/iiif directory exists with all the required files
2. **URL Generation Issues**: Check for changes in the URL structure or parameters
3. **Path Resolution Problems**: Verify the file path generation logic for PDFs and PTIFs
4. **Flask Context Issues**: Ensure Flask-dependent code works correctly within an application context

### Manual Testing

In addition to the automated tests, you can manually test the implementation by:

1. Running a minimal Flask application with the CantaloupeProxy:
   ```python
   from flask import Flask
   from zenodo_rdm.iiif.proxy import CantaloupeProxy
   
   app = Flask(__name__)
   app.config['RDM_IIIF_SERVER_URL'] = 'http://localhost:8182'
   
   @app.route('/test-proxy/<path:record_id>/<path:filename>')
   def test_proxy(record_id, filename):
       proxy = CantaloupeProxy()
       info = proxy.get_pdf_info(record_id, filename)
       return info or {"error": "Failed to get info"}
   
   if __name__ == '__main__':
       app.run(debug=True)
   ```

2. Testing with a real PDF file:
   ```bash
   # Place a PDF in the Cantaloupe source directory
   cp document.pdf /path/to/cantaloupe/images/private/123/
   
   # Test info.json
   curl http://localhost:8182/iiif/2/images%2Fprivate%2F123%2Fdocument.pdf/info.json
   
   # Test image API
   curl http://localhost:8182/iiif/2/images%2Fprivate%2F123%2Fdocument.pdf/full/,800/0/default.jpg?page=1
   ```

By thoroughly testing the implementation before installation, you can ensure it works correctly and avoid any issues after deployment.

## Debugging Tips

### 1. Check Cantaloupe Logs

Cantaloupe logs can provide valuable information about why requests might be failing:

```bash
docker-compose logs cantaloupe
```

### 2. Use the Flask Debug Toolbar

Enable the Flask Debug Toolbar in your development environment:

```python
DEBUG_TB_ENABLED = True
```

### 3. Add Debugging Output to CantaloupeProxy

Add debug logging to the `CantaloupeProxy` class:

```python
current_app.logger.debug(f"Proxying request to {url}")
```

### 4. Test Direct Cantaloupe Access

Test if Cantaloupe itself is working correctly:

```bash
curl http://localhost:8182/iiif/2/images/private/123/document.pdf/info.json
```

## Performance Considerations

1. **Caching**: Cantaloupe has built-in caching that can significantly improve performance:
   ```
   # In Cantaloupe's configuration:
   cache.server.source=FilesystemCache
   cache.server.derivative=FilesystemCache
   ```

2. **Image Size Limits**: Be aware of image size limits to prevent memory issues:
   ```python
   # In invenio.cfg:
   IIIF_IMAGE_SIZE_LIMIT = 4000  # Maximum dimension in pixels
   ```

3. **Connection Pooling**: Consider using connection pooling for requests to Cantaloupe:
   ```python
   session = requests.Session()
   response = session.get(url)
   ```

By following this guide, you should now have a good understanding of the PDF IIIF integration in Zenodo RDM, how it works, and how to maintain and extend it. If you encounter any issues not covered here, please refer to the source code or raise an issue on GitHub. 
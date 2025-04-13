# Integrating Cantaloupe for PDF Support in Zenodo RDM

## Overview

This document explains the process of integrating Cantaloupe image server with Zenodo RDM to support PDF files through the IIIF (International Image Interoperability Framework) protocol. By the end of this guide, you'll understand how to:

1. Extend the existing IIIF implementation to support PDFs
2. Configure and test the Cantaloupe integration
3. Troubleshoot common issues

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [The IIIF Stack: IIPImage vs. Cantaloupe](#the-iiif-stack-iipimage-vs-cantaloupe)
- [Implementation Steps](#implementation-steps)
- [Key Files and Their Purposes](#key-files-and-their-purposes)
- [Technical Deep Dive](#technical-deep-dive)
- [Common Challenges and Solutions](#common-challenges-and-solutions)
- [Testing Your Implementation](#testing-your-implementation)
- [URL Patterns and Examples](#url-patterns-and-examples)
- [How To: Commands Reference](#how-to-commands-reference)

## Architecture Overview

```
┌─────────────────┐        ┌─────────────────┐       ┌─────────────────┐
│                 │        │                 │       │                 │
│  Web Browser    │───────▶│   Zenodo RDM    │──────▶│   Cantaloupe    │
│                 │        │   Application   │       │   Image Server  │
└─────────────────┘        └─────────────────┘       └─────────────────┘
                                   │                         │
                                   ▼                         ▼
                           ┌─────────────────┐       ┌─────────────────┐
                           │                 │       │                 │
                           │  IIIF Resource  │       │  Storage:       │
                           │  & Manifests    │       │  - PTIF Images  │
                           │                 │       │  - PDF Files    │
                           └─────────────────┘       └─────────────────┘
```

When a user requests a PDF through IIIF:

1. The request arrives at Zenodo RDM
2. Our `CantaloupeProxy` class handles the request
3. It forwards the request to the Cantaloupe server
4. Cantaloupe accesses and renders the PDF
5. The response is sent back to the user

## The IIIF Stack: IIPImage vs. Cantaloupe

### Original Stack: IIPImage

```
┌─────────────────┐
│  Invenio RDM    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  IIPImageProxy  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  IIPImage       │
│  Server         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PTIF Images    │
│  Only           │
└─────────────────┘
```

### Enhanced Stack: Cantaloupe

```
┌─────────────────┐
│  Invenio RDM    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ CantaloupeProxy │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Cantaloupe     │
│  Server         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PTIF Images    │
│  & PDF Files    │
└─────────────────┘
```

## Implementation Steps

### 1. Understanding the Existing Implementation

First, we needed to understand how the existing IIIF integration works in Zenodo RDM. The key components are:

- **IIIFResource**: Defines routes and endpoints for IIIF requests
- **IIIFProxy**: Abstract class for proxying requests to an image server
- **IIPServerProxy**: Default implementation using IIPImage server

The main discovery was in `/.venv/lib/python3.9/site-packages/invenio_rdm_records/resources/iiif.py`:

```python
class IIIFProxy(ABC):
    """IIIF Proxy interface."""

    def should_proxy(self):
        """Check if the curent request should be proxied."""
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

The existing implementation includes a default `IIPServerProxy` class that proxies requests to the IIPImage server. It handles only PTIF (Pyramid TIFF) image formats and uses a specific file path structure for storing images.

### 2. Creating a CantaloupeProxy Class

We created a `CantaloupeProxy` class that extends `IIIFProxy` to handle both PTIF images and PDF files:

```python
from invenio_rdm_records.resources.iiif import IIIFProxy

class CantaloupeProxy(IIIFProxy):
    """Proxy for Cantaloupe image server with PDF support."""
    
    def proxy_request(self):
        """Proxy the current request to Cantaloupe server."""
        # Implementation that forwards requests to Cantaloupe
        # ...
```

### 3. Extending Functionality for PDFs

Our implementation added several key methods:

- **build_cantaloupe_url**: Creates URLs with IIIF parameters
- **get_pdf_info**: Retrieves PDF metadata
- **stream_image**: Streams image responses
- **generate_pdf_manifest**: Creates IIIF manifests for PDFs

### 4. Configuring the Proxy in Zenodo RDM

We updated the configuration to use our `CantaloupeProxy`:

```python
# in site/zenodo_rdm/config.py
class ZenodoIIIFResourceConfig(IIIFResourceConfig):
    # Use our custom resource class
    resource_cls = ZenodoIIIFResource
    
    # Use our Cantaloupe proxy class for handling PDF files
    proxy_cls = CantaloupeProxy
```

And in `invenio.cfg`:

```python
# Point to Cantaloupe server
RDM_IIIF_SERVER_URL = "http://localhost:8182"

# Use our CantaloupeProxy class
IIIF_PROXY_CLASS = "zenodo_rdm.iiif.proxy:CantaloupeProxy"

# Add PDF to supported formats
RDM_IIIF_MANIFEST_FORMATS = ["jpeg", "jpg", "png", "tiff", "tif", "pdf"]
```

## Key Files and Their Purposes

| File Path | Purpose |
|-----------|---------|
| `/site/zenodo_rdm/iiif/proxy.py` | Contains our `CantaloupeProxy` implementation |
| `/site/zenodo_rdm/iiif/resource.py` | Extends Invenio's `IIIFResource` for Zenodo |
| `/site/zenodo_rdm/iiif/schema.py` | Defines manifest schema with enhanced metadata |
| `/site/zenodo_rdm/iiif/serializers.py` | Handles serialization of IIIF manifests |
| `/site/zenodo_rdm/iiif/__init__.py` | Exports the `CantaloupeProxy` class |
| `/site/zenodo_rdm/config.py` | Configures the IIIF resource and proxy |
| `/invenio.cfg` | Global configuration for IIIF and Cantaloupe |
| `/test/test_cantaloupe_proxy.py` | Tests for the `CantaloupeProxy` class |
| `/test/test_cantaloupe_basic.py` | Basic tests for Cantaloupe functionality |
| `/scripts/AlA/Makefile` | Contains targets for testing Cantaloupe |

## Technical Deep Dive

### IIIF Proxy Architecture

The Invenio RDM framework provides an extensible architecture for IIIF implementation. Here's how it works:

1. **Request Handling Flow**:
   ```
   HTTP Request → IIIFResource → IIIFProxy (via proxy_pass decorator) → Image Server
   ```

2. **The Proxy Interface (`IIIFProxy`)**:
   - Located in `invenio_rdm_records/resources/iiif.py`
   - Defines an abstract interface for image server proxies
   - Has three key methods:
     - `should_proxy()`: Determines if a request should be proxied
     - `proxy_request()`: Abstract method to implement the actual proxying
     - `__call__()`: Entry point that handles routing

3. **Integration Points**:
   - Proxies are registered via the `proxy_cls` configuration parameter
   - The `proxy_pass` decorator in `IIIFResource` calls the proxy

### How CantaloupeProxy Extends the Framework

Our `CantaloupeProxy` implementation extends the base framework in several ways:

1. **Dual Format Support**:
   - Handles both PTIF images (for backward compatibility) and PDF files
   - Uses different path structures for each format type

2. **Extended URL Patterns**:
   - Supports standard Invenio IIIF URL patterns
   - Adds custom URL patterns for direct PDF access: `/api/iiif/record:<recid>:<filename>/...`

3. **Property-Based URL Configuration**:
   - Implements `server_url` as a property to allow dynamic configuration
   - Falls back to the `RDM_IIIF_SERVER_URL` configuration if not explicitly set

4. **PDF-Specific Features**:
   - Page selection via URL parameters
   - PDF metadata retrieval
   - IIIF manifest generation for PDFs

### Request Flow for PDF Files

For a PDF request, here's how the flow works:

1. **Request Arrives**:
   ```
   GET /api/iiif/record:202:document.pdf/full/full/0/default.jpg?page=2
   ```

2. **Routing in `should_proxy()`**:
   ```python
   def should_proxy(self):
       # First check standard endpoints
       standard_endpoints = super().should_proxy()
       if standard_endpoints:
           return True
           
       # Then check our custom pattern
       if request.path.startswith('/api/iiif/record:'):
           return self.is_iiif_request(request.path)
       
       return False
   ```

3. **Parameter Extraction in `proxy_request()`**:
   - Extracts record ID, filename from the URL
   - Extracts IIIF parameters (region, size, rotation, quality, format)
   - Extracts page number for PDFs

4. **URL Construction in `build_cantaloupe_url()`**:
   ```python
   url = f"{base_url}/iiif/2/{urllib.parse.quote(file_path)}/{region}/{size}/{rotation}/{quality}.{format}"
   ```

5. **Request to Cantaloupe**:
   - Forwards the request to the Cantaloupe server
   - Adds necessary parameters, including the page number
   - Streams the response back to the client

### Manifest Generation

For PDF manifest generation, we implemented a custom method:

```python
def generate_pdf_manifest(self, record_id, filename, base_url, ...):
    # Get PDF info from Cantaloupe
    pdf_info = self.get_pdf_info(record_id, filename)
    
    # Create manifest structure
    manifest = {
        "@context": "http://iiif.io/api/presentation/2/context.json",
        "@id": f"{id_prefix}/manifest.json",
        "@type": "sc:Manifest",
        # ...
    }
    
    # Create a canvas for each page
    for page_num in range(1, num_pages + 1):
        canvas = {
            "@id": f"{id_prefix}/canvas/p{page_num}",
            "@type": "sc:Canvas",
            # ...
        }
        manifest["sequences"][0]["canvases"].append(canvas)
    
    return manifest
```

This produces a IIIF manifest that viewers like Mirador can use to navigate PDF pages.

## Common Challenges and Solutions

### Challenge 1: Import Path Issues

**Problem:** 
```
Could not import CantaloupeProxy: No module named 'site.zenodo_rdm'; 'site' is not a package
```

**Solution:**
Install the site package in development mode:
```bash
cd site && pip install -e .
```

### Challenge 2: Proxy Configuration

**Problem:** The proxy wasn't being registered properly in the IIIF resource.

**Solution:** 
Update both `ZenodoIIIFResourceConfig` and `invenio.cfg` to specify the proxy class:

```python
# in site/zenodo_rdm/config.py
class ZenodoIIIFResourceConfig(IIIFResourceConfig):
    proxy_cls = CantaloupeProxy

# in invenio.cfg
IIIF_PROXY_CLASS = "zenodo_rdm.iiif.proxy:CantaloupeProxy"
```

### Challenge 3: File Path Structure

**Problem:** Cantaloupe couldn't find PDF files because the path structure was incorrect.

**Solution:**
Implement proper path handling in `_get_file_path`:

```python
def _get_file_path(self, record_id, filename):
    if self._is_pdf(filename):
        # Path for PDFs
        return f"images/private/{record_id}/{filename}"
    else:
        # Legacy PTIF structure
        recid_str = str(record_id)
        ch1 = recid_str[0:2].ljust(2, '_')
        ch2 = recid_str[2:4].ljust(2, '_')
        tail = recid_str[4:].ljust(1, '_')
        base_name = os.path.splitext(filename)[0]
        return f"{ch1}/{ch2}/{tail}/{base_name}.ptif"
```

### Challenge 4: Integrating with Existing Code

**Problem:** Our implementation needed to work with the existing IIIF framework without breaking it.

**Solution:**
Extend the base `IIIFProxy` class and implement the required methods while maintaining backward compatibility:

```python
def should_proxy(self):
    # First check Invenio RDM's standard endpoints
    standard_endpoints = super().should_proxy()
    if standard_endpoints:
        return True
        
    # Then check our custom URL pattern if needed
    if request.path.startswith('/api/iiif/record:'):
        return self.is_iiif_request(request.path)
    
    return False
```

### Challenge 5: Property vs. Method for Server URL

**Problem:** Accessing the server URL needed to be flexible to handle both direct setting and configuration parameters.

**Solution:**
Implement `server_url` as a property:

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

## Testing Your Implementation

### Basic Functionality Testing

Use the provided Makefile targets to test PDF functionality:

```bash
# Test basic PDF functionality
make -f scripts/AlA/Makefile test-cantaloupe RECORD=202 FILE=history00871.pdf

# Test page selection 
make -f scripts/AlA/Makefile test-cantaloupe-pages RECORD=202 FILE=history00871.pdf PAGES=1,2,3

# Test the CantaloupeProxy class
make -f scripts/AlA/Makefile test-cantaloupe-proxy RECORD=202 FILE=history00871.pdf MANIFEST=1
```

### What's Being Tested?

1. **test-cantaloupe**: Tests basic PDF access through Cantaloupe 
2. **test-cantaloupe-pages**: Tests PDF page selection functionality
3. **test-cantaloupe-proxy**: Tests the CantaloupeProxy class, including manifest generation

### Expected Output

Successful test execution should show output similar to:

```
Testing CantaloupeProxy with PDF file history00871.pdf in record 202
Testing URL generation...
Generated URL for page 1: http://localhost:8182/iiif/2/images%2Fprivate%2F202%2Fhistory00871.pdf/full/full/0/default.jpg?page=1
...
Testing PDF info retrieval...
Successfully retrieved info.json: {
  "@context": "http://iiif.io/api/image/2/context.json",
  "@id": "...",
  "protocol": "http://iiif.io/api/image",
  "width": 1800,
  "height": 2400,
  ...
}
Testing manifest generation...
Successfully generated manifest and saved to ./manifest.json
All tests passed successfully!
```

## URL Patterns and Examples

### Legacy PTIF Image URL Pattern

```
/iiif/<record_id>/full/full/0/default.jpg
```

### PDF URL Patterns

#### Basic Pattern

```
/api/iiif/record:<record_id>:<filename>/<region>/<size>/<rotation>/<quality>.<format>?page=<page_number>
```

#### Examples

1. **Get info.json for a PDF**:
   ```
   /api/iiif/record:202:document.pdf/info.json
   ```

2. **Render a specific page as JPEG**:
   ```
   /api/iiif/record:202:document.pdf/full/full/0/default.jpg?page=2
   ```

3. **Create a thumbnail from a page**:
   ```
   /api/iiif/record:202:document.pdf/full/200,/0/default.jpg?page=1
   ```

4. **Crop a region from a page**:
   ```
   /api/iiif/record:202:document.pdf/100,100,400,400/full/0/default.jpg?page=3
   ```

## How To: Commands Reference

### Installation

Install the site package for development:

```bash
cd site && pip install -e .
```

### Testing

Run basic tests:

```bash
# Test basic functionality
python test/test_cantaloupe_basic.py --record 202 --file document.pdf

# Test with Makefile
make -f scripts/AlA/Makefile test-cantaloupe RECORD=202 FILE=document.pdf

# Test specific pages
make -f scripts/AlA/Makefile test-cantaloupe-pages RECORD=202 FILE=document.pdf PAGES=1,2,3

# Test proxy with manifest generation
make -f scripts/AlA/Makefile test-cantaloupe-proxy RECORD=202 FILE=document.pdf MANIFEST=1
```

### Debugging

Check Cantaloupe server directly:

```bash
# Check if Cantaloupe server is running
curl http://localhost:8182/iiif/2

# Check a specific PDF info
curl http://localhost:8182/iiif/2/images%2Fprivate%2F202%2Fdocument.pdf/info.json

# Get a specific page from a PDF
curl http://localhost:8182/iiif/2/images%2Fprivate%2F202%2Fdocument.pdf/full/full/0/default.jpg?page=1 -o test.jpg
```

### Finding Files in the Project

```bash
# Find all IIIF-related files
find . -name "*iiif*" | grep -v __pycache__

# Find proxy implementations
grep -r "class.*Proxy" --include="*.py" .

# Examine IIIF configuration
grep -r "IIIF_" --include="*.py" --include="*.cfg" .
```

### Key Configuration Options

```python
# In invenio.cfg

# Server URL
RDM_IIIF_SERVER_URL = "http://localhost:8182"

# Proxy class
IIIF_PROXY_CLASS = "zenodo_rdm.iiif.proxy:CantaloupeProxy"

# Supported formats (including PDF)
RDM_IIIF_MANIFEST_FORMATS = ["jpeg", "jpg", "png", "tiff", "tif", "pdf"]

# Enable IIIF server
IIIF_SERVER_ENABLED = True

# Enable IIIF preview
IIIF_PREVIEW_ENABLED = True
```

## Conclusion

By following this guide, you should be able to understand and implement PDF support via Cantaloupe in your Zenodo RDM instance. The integration enables viewing PDFs through the IIIF protocol, which allows for page-by-page viewing, zooming, and other interactive features provided by IIIF viewers.

Remember to test your implementation thoroughly to ensure it works properly with your specific setup.

## References

- [IIIF Image API 2.1](https://iiif.io/api/image/2.1/)
- [IIIF Presentation API 2.1](https://iiif.io/api/presentation/2.1/)
- [Cantaloupe Image Server](https://cantaloupe-project.github.io/)
- [Invenio RDM Documentation](https://inveniordm.docs.cern.ch/) 
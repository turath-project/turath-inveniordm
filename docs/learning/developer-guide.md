# Developer Guide: IIIF and InvenioRDM Integration

## Overview

This guide provides step-by-step instructions for developers working on integrating IIIF (International Image Interoperability Framework) with InvenioRDM. It covers essential development tasks, common pitfalls, and practical solutions based on our experiences.

## Prerequisites

- Basic understanding of IIIF concepts (manifests, canvases, image services)
- Familiarity with InvenioRDM (installation, configuration)
- Python programming knowledge
- Understanding of web protocols (HTTP/HTTPS)
- Basic knowledge of SSL/TLS certificates

## Setup Development Environment

### 1. Install Required Software

```bash
# Clone the repository
git clone https://github.com/your-organization/turath-inveniordm.git
cd turath-inveniordm

# Install dependencies
pip install -r requirements.txt

# Set up SSL certificates for development
openssl genrsa -out key.pem 2048
openssl req -new -x509 -key key.pem -out cert.pem -days 365 -subj "/CN=localhost"
```

### 2. Configure InvenioRDM

Ensure InvenioRDM is configured to run with HTTPS:

```bash
# Start InvenioRDM with HTTPS
invenio run --https --cert ./cert.pem --key ./key.pem
```

## Developing a IIIF Server for Integration

### Creating a Basic IIIF Server

Here's a minimal implementation of a IIIF server with proper CORS and HTTPS support:

```python
# iiif_test_server.py
import http.server
import ssl
import json
import os
from urllib.parse import urlparse

class IIIFRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self._add_cors_headers()
        
        try:
            super().do_GET()
        except FileNotFoundError:
            self.send_error(404, "File not found")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self._add_cors_headers()
        self.end_headers()
    
    def _add_cors_headers(self):
        origin = self.headers.get('Origin')
        if origin:
            self.send_header('Access-Control-Allow-Origin', origin)
        else:
            self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Origin, Authorization')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Max-Age', '3600')
        self.send_header('Cross-Origin-Resource-Policy', 'cross-origin')

# Run the server
server_address = ('localhost', 8443)
httpd = http.server.HTTPServer(server_address, IIIFRequestHandler)

# Configure SSL
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain('cert.pem', 'key.pem')
httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)

print(f"Server running at https://{server_address[0]}:{server_address[1]}/")
httpd.serve_forever()
```

### Enhanced IIIF Server with Dynamic Manifest Generation

For more advanced use cases, you might want to generate manifests dynamically:

```python
# Enhanced iiif_test_server.py
import http.server
import ssl
import json
import os
from urllib.parse import urlparse, parse_qs

class IIIFRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        # Handle manifest requests
        if parsed_path.path == '/manifest' or parsed_path.path == '/manifest.json':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self._add_cors_headers()
            self.end_headers()
            
            # Generate dynamic manifest
            manifest = self._generate_manifest()
            self.wfile.write(json.dumps(manifest).encode())
            return
        
        # Handle info.json requests for IIIF image API
        if parsed_path.path.endswith('/info.json'):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self._add_cors_headers()
            self.end_headers()
            
            # Create info.json response
            image_id = parsed_path.path.split('/')[-2]
            info = {
                "@context": "http://iiif.io/api/image/2/context.json",
                "@id": f"https://{self.headers.get('Host', 'localhost:8443')}/image/{image_id}",
                "protocol": "http://iiif.io/api/image",
                "width": 800,
                "height": 1200,
                "profile": ["http://iiif.io/api/image/2/level1.json"]
            }
            self.wfile.write(json.dumps(info).encode())
            return
        
        # Handle other requests
        try:
            super().do_GET()
        except FileNotFoundError:
            self.send_error(404, "File not found")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self._add_cors_headers()
        self.end_headers()
    
    def _add_cors_headers(self):
        origin = self.headers.get('Origin')
        if origin:
            self.send_header('Access-Control-Allow-Origin', origin)
        else:
            self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Origin, Authorization')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Max-Age', '3600')
        self.send_header('Cross-Origin-Resource-Policy', 'cross-origin')
    
    def _generate_manifest(self):
        """Generate a IIIF manifest dynamically"""
        host = self.headers.get('Host', 'localhost:8443')
        
        return {
            "@context": "http://iiif.io/api/presentation/2/context.json",
            "@id": f"https://{host}/manifest",
            "@type": "sc:Manifest",
            "label": "Dynamic Test Manifest",
            "metadata": [
                {
                    "label": "Title",
                    "value": "Dynamic IIIF Manifest for InvenioRDM"
                }
            ],
            "sequences": [
                {
                    "@id": f"https://{host}/sequence/normal",
                    "@type": "sc:Sequence",
                    "canvases": [
                        {
                            "@id": f"https://{host}/canvas/p1",
                            "@type": "sc:Canvas",
                            "label": "Page 1",
                            "width": 800,
                            "height": 1200,
                            "images": [
                                {
                                    "@type": "oa:Annotation",
                                    "motivation": "sc:painting",
                                    "resource": {
                                        "@id": f"https://{host}/image/p1/full/full/0/default.jpg",
                                        "@type": "dctypes:Image",
                                        "format": "image/jpeg",
                                        "width": 800,
                                        "height": 1200,
                                        "service": {
                                            "@context": "http://iiif.io/api/image/2/context.json",
                                            "@id": f"https://{host}/image/p1",
                                            "profile": "http://iiif.io/api/image/2/level1.json"
                                        }
                                    },
                                    "on": f"https://{host}/canvas/p1"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
```

## Creating IIIF Manifests for InvenioRDM

### Basic Manifest Template

Here's a template for a IIIF manifest that works well with InvenioRDM:

```json
{
  "@context": "http://iiif.io/api/presentation/2/context.json",
  "@id": "https://YOUR_SERVER:PORT/manifest/BOOK_ID",
  "@type": "sc:Manifest",
  "label": "BOOK_TITLE",
  "metadata": [
    {
      "label": "Title",
      "value": "BOOK_TITLE"
    },
    {
      "label": "Author",
      "value": "AUTHOR_NAME"
    },
    {
      "label": "Publication Date",
      "value": "PUBLICATION_DATE"
    }
  ],
  "description": "BOOK_DESCRIPTION",
  "attribution": "YOUR_ORGANIZATION",
  "license": "https://creativecommons.org/licenses/by/4.0/",
  "sequences": [
    {
      "@id": "https://YOUR_SERVER:PORT/sequence/BOOK_ID",
      "@type": "sc:Sequence",
      "canvases": [
        {
          "@id": "https://YOUR_SERVER:PORT/canvas/BOOK_ID/p1",
          "@type": "sc:Canvas",
          "label": "Page 1",
          "width": WIDTH,
          "height": HEIGHT,
          "images": [
            {
              "@type": "oa:Annotation",
              "motivation": "sc:painting",
              "resource": {
                "@id": "https://YOUR_SERVER:PORT/image/BOOK_ID/p1/full/full/0/default.jpg",
                "@type": "dctypes:Image",
                "format": "image/jpeg",
                "width": WIDTH,
                "height": HEIGHT,
                "service": {
                  "@context": "http://iiif.io/api/image/2/context.json",
                  "@id": "https://YOUR_SERVER:PORT/image/BOOK_ID/p1",
                  "profile": "http://iiif.io/api/image/2/level1.json"
                }
              },
              "on": "https://YOUR_SERVER:PORT/canvas/BOOK_ID/p1"
            }
          ]
        }
      ]
    }
  ]
}
```

### Dynamic Manifest Generation

For books with many pages, it's better to generate manifests programmatically:

```python
def generate_manifest(book_id, book_metadata, pages, base_url="https://localhost:8443"):
    """
    Generate a IIIF manifest for a book with multiple pages
    
    Parameters:
    - book_id: Unique identifier for the book
    - book_metadata: Dict containing title, author, date, etc.
    - pages: List of page information (width, height, file paths)
    - base_url: Base URL for the IIIF server
    """
    
    # Create metadata entries
    metadata_entries = []
    for key, value in book_metadata.items():
        if key not in ['title', 'description']:  # These have special places in the manifest
            metadata_entries.append({
                "label": key.capitalize(),
                "value": value
            })
    
    # Create canvases for each page
    canvases = []
    for i, page in enumerate(pages, 1):
        canvas = {
            "@id": f"{base_url}/canvas/{book_id}/p{i}",
            "@type": "sc:Canvas",
            "label": f"Page {i}",
            "width": page['width'],
            "height": page['height'],
            "images": [
                {
                    "@type": "oa:Annotation",
                    "motivation": "sc:painting",
                    "resource": {
                        "@id": f"{base_url}/image/{book_id}/p{i}/full/full/0/default.jpg",
                        "@type": "dctypes:Image",
                        "format": "image/jpeg",
                        "width": page['width'],
                        "height": page['height'],
                        "service": {
                            "@context": "http://iiif.io/api/image/2/context.json",
                            "@id": f"{base_url}/image/{book_id}/p{i}",
                            "profile": "http://iiif.io/api/image/2/level1.json"
                        }
                    },
                    "on": f"{base_url}/canvas/{book_id}/p{i}"
                }
            ]
        }
        canvases.append(canvas)
    
    # Create the full manifest
    manifest = {
        "@context": "http://iiif.io/api/presentation/2/context.json",
        "@id": f"{base_url}/manifest/{book_id}",
        "@type": "sc:Manifest",
        "label": book_metadata.get('title', f"Book {book_id}"),
        "metadata": metadata_entries,
        "description": book_metadata.get('description', ""),
        "attribution": book_metadata.get('attribution', ""),
        "license": book_metadata.get('license', "https://creativecommons.org/licenses/by/4.0/"),
        "sequences": [
            {
                "@id": f"{base_url}/sequence/{book_id}",
                "@type": "sc:Sequence",
                "canvases": canvases
            }
        ]
    }
    
    return manifest
```

### Manifest Generation within `upload_book.py`

The current workflow utilizes the `scripts/upload_book.py` script to generate a static IIIF manifest *during* the upload process.

*   **Process Summary:**
    1.  After uploading files (PDF, HOCR), the script queries Cantaloupe for page dimensions.
    2.  It calculates scale factors if HOCR is present.
    3.  It constructs the manifest JSON, linking to Cantaloupe images, proxied annotation/search services, and Invenio-hosted HOCR/PDF files.
    4.  **Crucially:** It saves this generated manifest as `manifest.json` and uploads it with that specific key.
*   **Key Learnings & Fixes:**
    *   **Manifest Naming Bug:** A previous version uploaded the manifest with a temporary name, breaking internal `@id` links. This was fixed by ensuring the file is uploaded as `manifest.json`.
    *   **Dependencies:** This process relies on Cantaloupe being accessible *by the script* during generation.
    *   **Discovery:** The viewer needs to know to look for `/files/manifest.json` for the record.
*   **Link Testing:**
    *   When testing manifest links with `curl` against the Invenio API:
        *   Use `/api/records/{id}/files/manifest.json/content` to get the manifest content.
        *   Use `/api/records/{id}/files/{filename}` to check file metadata (like for `manifest.json` or `001.hocr`).
        *   Use `/api/records/{id}/files/{filename}/content` to download file content (like the PDF).
        *   Testing the manifest's internal `@id` (`.../files/manifest.json`) or canvas `@id` (`.../files/manifest.json/canvas/...`) against the file metadata API endpoint will likely result in a 404, as the API doesn't parse the JSON content for sub-paths.

For full details, see `docs/learning/manifest_generation_approaches.md` and `docs/learning/book_upload_and_manifest_process.md`.

## Integrating with InvenioRDM

### Adding IIIF Manifest URL to Record Metadata

When creating records in InvenioRDM, add the IIIF manifest URL to the metadata:

```python
def prepare_metadata(book_info, iiif_manifest_url):
    """Prepare metadata for InvenioRDM record creation"""
    metadata = {
        "title": book_info.get('title', "Untitled Book"),
        "publication_date": book_info.get('publication_date', "2023-01-01"),
        "resource_type": {"id": "publication-book"},
        "creators": [
            {
                "person_or_org": {
                    "name": author,
                    "type": "personal"
                },
                "role": {"id": "author"}
            } for author in book_info.get('authors', ["Unknown Author"])
        ],
        "languages": [{"id": book_info.get('language', 'eng')}],
        "identifiers": [
            {
                "scheme": "other",
                "identifier": book_info.get('identifier', "unknown")
            }
        ],
        "formats": ["application/pdf"],
        # Custom field for IIIF manifest URL
        "custom": {
            "iiif_manifest": iiif_manifest_url
        }
    }
    return metadata
```

### Configuring InvenioRDM to Display IIIF Viewer

Ensure your InvenioRDM configuration displays IIIF viewers for records with manifest URLs:

```python
# In invenio.cfg

# Enable IIIF viewer
IIIF_VIEWER_ENABLED = True

# Configure viewer
IIIF_VIEWER_CONFIG = {
    "manifest_field": "custom.iiif_manifest",
    "viewer": "mirador",  # or 'universalviewer'
    "options": {
        "showTitle": True,
        "allowFullscreen": True
    }
}
```

## Troubleshooting Common Issues

### 1. CORS Errors

**Problem**: The browser console shows errors like `Access to fetch at 'https://...' from origin 'https://...' has been blocked by CORS policy`.

**Solution**:
- Ensure your IIIF server sends proper CORS headers for all responses
- Check that `Access-Control-Allow-Origin` includes the domain of your InvenioRDM instance
- Make sure `OPTIONS` requests are handled correctly

### 2. Mixed Content Errors

**Problem**: The browser blocks HTTP content loaded from an HTTPS page.

**Solution**:
- Convert all URLs in your IIIF manifest to use HTTPS
- Ensure your IIIF server supports HTTPS
- Update any hardcoded URLs in your code to use HTTPS

### 3. Certificate Validation Errors

**Problem**: The browser doesn't trust your self-signed certificate.

**Solution**:
- For development, manually accept the certificate in your browser
- For production, use a proper certificate from a trusted authority like Let's Encrypt
- Ensure certificate chain is complete and properly configured

### 4. Manifest Loading Issues

**Problem**: The IIIF viewer in InvenioRDM doesn't load the manifest.

**Solution**:
- Check the browser console for specific errors
- Validate your manifest using a tool like [IIIF Validator](https://iiif.io/api/presentation/validator/)
- Ensure the manifest URL is correctly stored in the record metadata
- Check that the URL is accessible from the browser (not just the server)

## Best Practices

1. **Always use HTTPS**: Both InvenioRDM and your IIIF server should use HTTPS.

2. **Validate manifests**: Use the IIIF Validator to check your manifests.

3. **Use dynamic URL generation**: Avoid hardcoding URLs in manifests.

4. **Implement proper error handling**: Log errors and provide fallbacks.

5. **Test in multiple browsers**: Chrome, Firefox, Safari, and Edge handle CORS differently.

6. **Set up monitoring**: Track failures and errors in your IIIF server.

7. **Document your API**: Provide clear documentation for others using your IIIF server.

## Conclusion

Integrating IIIF with InvenioRDM provides powerful capabilities for displaying and interacting with digital objects. By following this guide, you should be able to successfully set up a development environment, create IIIF manifests, and integrate them with InvenioRDM while avoiding common pitfalls.

Remember that the most important aspects are ensuring proper HTTPS support, configuring CORS correctly, and validating your manifests. With these foundations in place, you can build sophisticated digital library experiences for your users. 
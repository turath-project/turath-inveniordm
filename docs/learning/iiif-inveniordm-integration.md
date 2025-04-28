# IIIF Integration with InvenioRDM: Lessons Learned

## Introduction

This document summarizes the challenges and solutions encountered when integrating IIIF (International Image Interoperability Framework) manifests with InvenioRDM. It focuses particularly on cross-origin resource sharing (CORS) issues and protocol mismatches between HTTP and HTTPS servers.

## Core Challenges

1. **Protocol Mismatch**: InvenioRDM runs on HTTPS (`https://127.0.0.1:5000`), while dependent services like Cantaloupe might run on HTTP (`http://localhost:8182`). Modern browsers enforce strict security policies that prevent HTTPS pages from loading HTTP resources.

2. **CORS Restrictions**: The IIIF viewer (Mirador) embedded in InvenioRDM makes cross-origin requests to IIIF Image servers (Cantaloupe) and potentially annotation/search services (if proxied). These requests are blocked by default due to browser security policies unless the *target* server sends the correct `Access-Control-Allow-Origin` headers.

3. **Mixed Content Blocking**: Browsers block "mixed content" - when an HTTPS page (InvenioRDM) tries to load resources (images, manifests, annotations) over insecure HTTP connections.

4. **Service URL Context**: IIIF manifests must contain absolute URLs. These URLs need to be correct *from the perspective of the client (browser)* loading the viewer. This means using publicly accessible URLs (like `https://localhost/...` via the Nginx proxy) rather than internal Docker service names (`http://annotation-service:5002/...`).

5. **Manifest Discovery & Linking:** How does InvenioRDM know which manifest to display for a given record? How are services like annotations and search linked within the manifest?

6. **Data Access for Services:** How do separate services (Cantaloupe, Annotation, Search) access the necessary files (PDFs, HOCR) associated with an InvenioRDM record?

## Solutions Implemented (Current System)

### 1. Nginx Reverse Proxy for HTTPS & Service Access

*   The `frontend` (Nginx) service runs on HTTPS (port 443) using a self-signed certificate locally.
*   It acts as the single public entry point (`https://localhost`).
*   It proxies requests for `/annotations/` and `/search/` (and `/autocomplete/`) to the internal HTTP Annotation and Search services (`http://annotation-service:5002`, `http://search-service:5001`).
*   This solves the **protocol mismatch** for annotation/search services from the browser's perspective, as the browser only talks HTTPS to Nginx.
*   **Challenge:** Requires correct Nginx configuration (`docker/nginx/nginx.conf`) with proper `location` blocks and `proxy_pass` directives (without trailing slashes for these services) placed *before* the general InvenioRDM `location /` block.

### 2. Static Manifest Generation (`upload_book.py`)

*   The `upload_book.py` script generates a static `manifest.json` file during the upload process.
*   **Service Linking:** This manifest is constructed with URLs pointing to the **Nginx proxy** for annotations and search (e.g., `https://localhost/annotations/...`).
*   **Image Linking:** It links images to the **Cantaloupe server** directly (e.g., `http://localhost:8182/...`).
*   **HOCR Linking:** It links HOCR files using the InvenioRDM file API URL (`https://127.0.0.1:5000/api/records/.../files/XXX.hocr`).
*   **Upload & Discovery:** The manifest is uploaded to the record with the key `manifest.json`. InvenioRDM needs to be configured (likely via `IIIF_VIEWER_CONFIG` in `invenio.cfg` or implicitly) to look for this specific file (`/files/manifest.json`) to display in the viewer.
*   **Challenge:** This fixed a bug where the manifest was uploaded with a temporary name, breaking internal links.

### 3. CORS Headers (Handled by Services/Proxy)

*   **Cantaloupe:** Assumed to have CORS headers configured appropriately (needs verification if cross-origin issues arise with images).
*   **Annotation/Search Services:** The Flask applications were configured to include basic CORS headers (`Access-Control-Allow-Origin: *` or specific origins via environment variable).
*   **Nginx:** The Nginx proxy configuration *could* add/modify CORS headers, but typically it's better handled by the upstream service unless Nginx needs to enforce specific policies.
*   **InvenioRDM:** Also sends CORS headers for its API endpoints.

### 4. Data Sharing via Host Bind Mounts

*   To solve **data access for services**:
    *   **Cantaloupe:** The `upload_book.py` script copies the primary PDF (named `{record_id}_{filename}.pdf`) to a host directory (`./cantaloupe-files`) which is bind-mounted into the Cantaloupe container (`/opt/cantaloupe/images`). Cantaloupe is configured to look for files in this path.
    *   **Annotation/Search:** The `upload_book.py` script copies HOCR files (if included in the upload) to a structured path within a host directory (`./hocr_mount/books/{book_id}/hocr/`). This directory is bind-mounted into the annotation and search service containers (`/hocr_data`). The services read files from `/hocr_data/books/{book_id}/hocr/`.
*   **Challenge:** Requires the host directories (`./cantaloupe-files`, `./hocr_mount`) to exist and for the script to have write permissions. The script needs the `--hocr-mount-point` argument for the HOCR copy step.

### 5. Handling HTTP Cantaloupe Link (Mixed Content)

*   **Problem:** The generated static manifest links images to Cantaloupe using `http://localhost:8182/...`, but InvenioRDM is served over HTTPS (`https://localhost`). This causes a **mixed content** error in the browser, preventing images from loading in the viewer.
*   **Solution (Not Yet Implemented):** Requires one of the following:
    1.  **Run Cantaloupe on HTTPS:** Modify the Cantaloupe service (`docker-compose.yml`) and configuration to use HTTPS (requires certificate management for the container).
    2.  **Proxy Cantaloupe via Nginx:** Add a new `location` block in Nginx (e.g., `/iiif/`) to proxy requests to `http://cantaloupe:8182`. Update the manifest generation in `upload_book.py` to use `https://localhost/iiif/...` URLs.
    3.  **(Less Ideal)** Configure the browser or InvenioRDM security policy (CSP) to allow mixed content (generally discouraged).
*   **Current Status:** Image loading in the IIIF viewer within InvenioRDM is likely **broken** due to this mixed content issue.

### 6. Self-Signed Certificates

*   Local development uses self-signed certificates for InvenioRDM (via `invenio run --https`) and potentially Nginx.
*   Clients (browsers, `curl`, Python `requests`) need to be configured to trust or ignore these certificates.
    *   Browser: Manually accept the certificate warning.
    *   `curl`: Use the `-k` flag.
    *   `upload_book.py`: Use the `--no-verify-ssl` flag.

## Common Errors and Their Solutions

### Error: "Fetch API cannot load due to access control checks"

**Problem**: The IIIF server isn't sending proper CORS headers.

**Solution**: Update your IIIF server to send appropriate CORS headers as shown above.

### Error: "Mixed Content: The page was loaded over HTTPS, but requested an insecure resource"

**Problem**: The manifest contains HTTP URLs while InvenioRDM is using HTTPS.

**Solution**: Convert all URLs in the manifest to use HTTPS, and ensure your IIIF server supports HTTPS.

### Error: "net::ERR_CERT_AUTHORITY_INVALID"

**Problem**: The browser doesn't trust the self-signed certificate.

**Solution**: For testing, manually accept the certificate by visiting the IIIF server URL directly in the browser and clicking "Advanced" -> "Proceed to [site] (unsafe)". In production, use a proper SSL certificate.

## Example Setup

### Test IIIF Server with HTTPS and CORS Support

```python
# iiif_test_server.py
import http.server
import ssl
import json
import os
from urllib.parse import urlparse, parse_qs

class IIIFRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        # Add CORS headers for all responses
        origin = self.headers.get('Origin')
        
        # Handle requests for manifest.json
        if parsed_path.path == '/public_manifest' or parsed_path.path == '/public_manifest.json':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*' if not origin else origin)
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS, HEAD')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Origin, Authorization')
            self.send_header('Cross-Origin-Resource-Policy', 'cross-origin')
            self.end_headers()
            
            # Read and modify the manifest to use correct host and port
            with open('public_manifest.json', 'r') as f:
                manifest = json.load(f)
            
            # Update manifest URLs to match server
            host = self.headers.get('Host', 'localhost:8443')
            protocol = 'https'
            
            # Replace all URLs in the manifest with the correct protocol and host
            self._update_urls_in_manifest(manifest, protocol, host)
            
            self.wfile.write(json.dumps(manifest).encode())
            return
        
        # Handle other requests
        try:
            super().do_GET()
        except FileNotFoundError:
            self.send_error(404, "File not found")
    
    def do_OPTIONS(self):
        # Handle preflight CORS requests
        self.send_response(200)
        origin = self.headers.get('Origin')
        self.send_header('Access-Control-Allow-Origin', '*' if not origin else origin)
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Origin, Authorization')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Max-Age', '3600')
        self.send_header('Cross-Origin-Resource-Policy', 'cross-origin')
        self.end_headers()
    
    def end_headers(self):
        # Add CORS headers to all responses
        origin = self.headers.get('Origin')
        if origin:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Timing-Allow-Origin', origin)
        super().end_headers()
    
    def _update_urls_in_manifest(self, obj, protocol, host):
        """Recursively update all URLs in a manifest to use the specified protocol and host"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == '@id' and isinstance(value, str) and (value.startswith('http://') or value.startswith('https://')):
                    parsed = urlparse(value)
                    path = parsed.path
                    obj[key] = f"{protocol}://{host}{path}"
                elif isinstance(value, (dict, list)):
                    self._update_urls_in_manifest(value, protocol, host)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    self._update_urls_in_manifest(item, protocol, host)

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

### Example IIIF Manifest (HTTPS Compatible)

```json
{
  "@context": "http://iiif.io/api/presentation/2/context.json",
  "@id": "https://localhost:8443/public_manifest",
  "@type": "sc:Manifest",
  "label": "Test Book Manifest",
  "metadata": [
    {
      "label": "Title",
      "value": "Test Book for InvenioRDM Integration"
    },
    {
      "label": "Author",
      "value": "Turath Digital Library"
    }
  ],
  "description": "A test IIIF manifest for verifying integration with InvenioRDM",
  "attribution": "Turath Digital Library",
  "logo": "https://localhost:8443/logo",
  "license": "https://creativecommons.org/licenses/by/4.0/",
  "sequences": [
    {
      "@id": "https://localhost:8443/sequence/normal",
      "@type": "sc:Sequence",
      "canvases": [
        {
          "@id": "https://localhost:8443/canvas/p1",
          "@type": "sc:Canvas",
          "label": "Page 1",
          "width": 800,
          "height": 1200,
          "images": [
            {
              "@type": "oa:Annotation",
              "motivation": "sc:painting",
              "resource": {
                "@id": "https://localhost:8443/image/p1/full/full/0/default.jpg",
                "@type": "dctypes:Image",
                "format": "image/jpeg",
                "width": 800,
                "height": 1200,
                "service": {
                  "@context": "http://iiif.io/api/image/2/context.json",
                  "@id": "https://localhost:8443/image/p1",
                  "profile": "http://iiif.io/api/image/2/level1.json"
                }
              },
              "on": "https://localhost:8443/canvas/p1"
            }
          ]
        }
      ]
    }
  ]
}
```

## How-To Guide

### Starting a Secure IIIF Test Server

1. Generate self-signed certificates:
   ```bash
   openssl genrsa -out key.pem 2048
   openssl req -new -x509 -key key.pem -out cert.pem -days 365 -subj "/CN=localhost"
   ```

2. Start the IIIF test server:
   ```bash
   python scripts_experimenting/iiif_test_server.py
   ```

3. Check if the server is running:
   ```bash
   curl -k https://localhost:8443/public_manifest
   ```

### Testing in InvenioRDM

1. Start InvenioRDM:
   ```bash
   invenio run --https --cert ./cert.pem --key ./key.pem
   ```

2. Create a record with a IIIF manifest URL pointing to your HTTPS IIIF server.

3. View the record in InvenioRDM, and the IIIF viewer should load without CORS or mixed content errors.

## Troubleshooting

1. **Checking CORS Headers**: Use browser developer tools (Network tab) to check if the IIIF server is returning the correct CORS headers.

2. **Testing HTTPS Directly**: Directly visit the HTTPS IIIF server URL in your browser to check if the certificate is accepted.

3. **Verifying Manifest URLs**: Ensure all URLs in the manifest are using HTTPS with the correct host and port.

4. **Browser Console Errors**: Check the browser console for specific errors related to CORS, mixed content, or certificate issues.

## Conclusion

Integrating IIIF with InvenioRDM requires proper handling of HTTPS and CORS. The key points to remember are:

1. Always use HTTPS for both InvenioRDM and your IIIF server
2. Configure proper CORS headers on your IIIF server
3. Ensure all URLs in the IIIF manifest use HTTPS
4. For development, use self-signed certificates and accept them in your browser

By following these guidelines, you can successfully integrate IIIF viewers with InvenioRDM and avoid common issues related to cross-origin resource sharing and mixed content. 
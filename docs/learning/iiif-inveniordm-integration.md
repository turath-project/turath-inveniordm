# IIIF Integration with InvenioRDM: Lessons Learned

## Introduction

This document summarizes the challenges and solutions encountered when integrating IIIF (International Image Interoperability Framework) manifests with InvenioRDM. It focuses particularly on cross-origin resource sharing (CORS) issues and protocol mismatches between HTTP and HTTPS servers.

## Core Challenges

1. **Protocol Mismatch**: InvenioRDM runs on HTTPS (`https://127.0.0.1:5000`), while many IIIF servers run on HTTP. Modern browsers enforce strict security policies that prevent HTTPS pages from loading HTTP resources.

2. **CORS Restrictions**: The IIIF viewer (Mirador) embedded in InvenioRDM makes cross-origin requests to IIIF servers, which are blocked by default due to browser security policies.

3. **Mixed Content Blocking**: Browsers block "mixed content" - when HTTPS pages load resources over insecure HTTP connections.

4. **Service URL Context**: IIIF manifests must have service URLs that match the protocol (HTTP/HTTPS) of the requesting application.

## Solutions

### 1. Run IIIF Server with HTTPS

The primary solution is to ensure your IIIF server uses HTTPS. This eliminates the protocol mismatch issue.

```python
# Example using the Python http.server with SSL
import http.server
import ssl

server_address = ('localhost', 8443)
httpd = http.server.HTTPServer(server_address, http.server.SimpleHTTPRequestHandler)

# Configure SSL
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain('cert.pem', 'key.pem')  # Self-signed certificates
httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)

print(f"Server running at https://{server_address[0]}:{server_address[1]}/")
httpd.serve_forever()
```

### 2. Configure Proper CORS Headers

IIIF servers must send appropriate CORS headers to allow cross-origin requests from InvenioRDM.

```python
class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def send_response_only(self, code, message=None):
        super().send_response_only(code, message)
        
    def end_headers(self):
        # CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')  # Allow requests from any origin
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Origin, Authorization')
        self.send_header('Cross-Origin-Resource-Policy', 'cross-origin')
        super().end_headers()
        
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
```

### 3. Update Manifest URLs to Use HTTPS

Ensure all URLs in the IIIF manifest use HTTPS, including image services, canvases, and sequences.

Before:
```json
"@id": "http://localhost:9443/public_manifest",
"service": {
  "@context": "http://iiif.io/api/image/2/context.json",
  "@id": "http://localhost:9443/image/p1",
  "profile": "http://iiif.io/api/image/2/level1.json"
}
```

After:
```json
"@id": "https://localhost:8443/public_manifest",
"service": {
  "@context": "http://iiif.io/api/image/2/context.json",
  "@id": "https://localhost:8443/image/p1",
  "profile": "http://iiif.io/api/image/2/level1.json"
}
```

### 4. Generate Self-Signed Certificates for Testing

For local development, generate self-signed certificates:

```bash
# Generate private key
openssl genrsa -out key.pem 2048

# Generate certificate
openssl req -new -x509 -key key.pem -out cert.pem -days 365 -subj "/CN=localhost"
```

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
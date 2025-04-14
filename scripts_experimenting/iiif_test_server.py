#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple HTTPS server that simulates a minimal IIIF service.
Used to test if InvenioRDM IIIF viewers can access external IIIF services.
"""

import ssl
import json
import os
import sys
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleIIIFHandler(BaseHTTPRequestHandler):
    """Handler for IIIF service requests."""
    
    def do_GET(self):
        """Handle GET requests with appropriate IIIF content."""
        # Get the server's port for URL construction
        server_port = self.server.server_port
        
        # Use the same hostname the client used to connect
        host_header = self.headers.get('Host', '')
        if ':' in host_header:
            client_hostname = host_header.split(':')[0]
        else:
            client_hostname = host_header if host_header else 'localhost'
            
        base_url = f"{'https' if not getattr(self.server, 'http_mode', False) else 'http'}://{client_hostname}:{server_port}"
        
        # Parse query parameters
        query_params = {}
        if '?' in self.path:
            path, query = self.path.split('?', 1)
            self.path = path  # Remove query from path
            for param in query.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    query_params[key] = value
        
        # Check for JSONP callback
        callback = query_params.get('callback', None)
        
        # Set CORS headers for all responses
        self.send_response(200)
        
        # Enhanced CORS headers for better cross-origin support
        origin = self.headers.get('Origin', '*')
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Origin, Authorization')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Max-Age', '3600')
        
        # Set appropriate Content-Type based on request
        if self.path.endswith('.jpg') or self.path.endswith('.jpeg'):
            self.send_header('Content-Type', 'image/jpeg')
        elif callback:
            self.send_header('Content-Type', 'application/javascript')
        else:
            self.send_header('Content-Type', 'application/json')
            
        # Set security headers for cross-origin resource sharing
        self.send_header('Cross-Origin-Resource-Policy', 'cross-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'unsafe-none')
        self.send_header('Timing-Allow-Origin', '*')
        self.end_headers()
        
        if self.path == '/':
            response = {
                "message": "IIIF Test Server is running",
                "service": "IIIF Test",
                "endpoints": {
                    "root": f"{base_url}/",
                    "search": f"{base_url}/search",
                    "annotations": f"{base_url}/annotations/test",
                    "public_manifest": f"{base_url}/public_manifest",
                    "test_manifest": f"{base_url}/test_manifest"
                }
            }
            self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))
        
        elif self.path == '/test_manifest':
            # Return the test manifest JSON
            try:
                with open('test_manifest.json', 'rb') as f:
                    manifest_data = json.load(f)
                    # Update URLs with current hostname
                    self._update_urls_in_manifest(manifest_data, base_url)
                    self.wfile.write(json.dumps(manifest_data, indent=2).encode('utf-8'))
            except FileNotFoundError:
                error = {
                    "error": "Manifest file not found",
                    "path": self.path,
                    "message": "The test_manifest.json file could not be found. Make sure it exists in the same directory as this script."
                }
                self.wfile.write(json.dumps(error, indent=2).encode('utf-8'))
        
        elif self.path == '/public_manifest':
            # Return the public manifest JSON with corrected hostname
            try:
                with open('public_manifest.json', 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                    
                # Update URLs with current hostname
                self._update_urls_in_manifest(manifest, base_url)
                
                self.wfile.write(json.dumps(manifest, indent=2).encode('utf-8'))
            except FileNotFoundError:
                error = {
                    "error": "Manifest file not found",
                    "path": self.path,
                    "message": "The public_manifest.json file could not be found. Make sure it exists in the same directory as this script."
                }
                self.wfile.write(json.dumps(error, indent=2).encode('utf-8'))
        
        elif self.path.startswith('/canvas/'):
            # Return a simple canvas description
            canvas_id = self.path.split('/')[-1]
            canvas = {
                "@context": "http://iiif.io/api/presentation/2/context.json",
                "@id": f"{base_url}{self.path}",
                "@type": "sc:Canvas",
                "label": f"Canvas {canvas_id}",
                "width": 800,
                "height": 600
            }
            self.wfile.write(json.dumps(canvas, indent=2).encode('utf-8'))
        
        elif self.path == '/search' or self.path.startswith('/search?'):
            # Return a simple search result
            search_result = {
                "@context": "http://iiif.io/api/search/0/context.json",
                "@id": f"{base_url}{self.path}",
                "@type": "sc:AnnotationList",
                "resources": [
                    {
                        "@type": "oa:Annotation",
                        "motivation": "sc:painting",
                        "resource": {
                            "@type": "cnt:ContentAsText",
                            "chars": "This is a test search result."
                        },
                        "on": f"{base_url}/canvas/page1"
                    }
                ]
            }
            self.wfile.write(json.dumps(search_result, indent=2).encode('utf-8'))
        
        elif self.path.startswith('/annotations/'):
            # Return a simple annotation
            page_id = self.path.split('/')[-1]
            annotation = {
                "@context": "http://iiif.io/api/presentation/2/context.json",
                "@id": f"{base_url}{self.path}",
                "@type": "sc:AnnotationList",
                "resources": [
                    {
                        "@type": "oa:Annotation",
                        "motivation": "sc:painting",
                        "resource": {
                            "@type": "cnt:ContentAsText",
                            "chars": f"This is a test annotation for {page_id}."
                        },
                        "on": f"{base_url}/canvas/{page_id}"
                    }
                ]
            }
            self.wfile.write(json.dumps(annotation, indent=2).encode('utf-8'))
        
        elif self.path.startswith('/autocomplete') or self.path.startswith('/autocomplete?'):
            # Return a simple autocomplete result
            autocomplete = {
                "@context": "http://iiif.io/api/search/0/context.json",
                "@id": f"{base_url}{self.path}",
                "@type": "search:TermList",
                "terms": [
                    {"match": "test", "url": f"{base_url}/search?q=test", "count": 1},
                    {"match": "example", "url": f"{base_url}/search?q=example", "count": 1}
                ]
            }
            self.wfile.write(json.dumps(autocomplete, indent=2).encode('utf-8'))
        
        elif self.path.startswith('/image/'):
            parts = self.path.strip('/').split('/')
            
            # Handle image info.json requests
            if len(parts) >= 2 and parts[-1] == 'info.json':
                image_id = parts[1]  # Extract image ID
                info = {
                    "@context": "http://iiif.io/api/image/2/context.json",
                    "@id": f"{base_url}/image/{image_id}",
                    "protocol": "http://iiif.io/api/image",
                    "width": 800,
                    "height": 1200,
                    "sizes": [
                        {"width": 800, "height": 1200},
                        {"width": 400, "height": 600},
                        {"width": 200, "height": 300}
                    ],
                    "tiles": [
                        {"width": 512, "height": 512, "scaleFactors": [1, 2, 4, 8]}
                    ],
                    "profile": ["http://iiif.io/api/image/2/level1.json"]
                }
                
                # If JSONP is requested, wrap the response
                if callback:
                    response_data = f"{callback}({json.dumps(info)});"
                    self.wfile.write(response_data.encode('utf-8'))
                else:
                    self.wfile.write(json.dumps(info, indent=2).encode('utf-8'))
            
            # Handle actual image requests by serving a blank placeholder image
            elif any(self.path.endswith(ext) for ext in ['.jpg', '.jpeg']):
                # Create a small blank JPEG image (1x1 pixel, white)
                blank_image = b'\xff\xd8\xff\xe0\x00\x10\x4a\x46\x49\x46\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00\xff\xdb\x00\x43\x00\x03\x02\x02\x03\x02\x02\x03\x03\x03\x03\x04\x03\x03\x04\x05\x08\x05\x05\x04\x04\x05\x0a\x07\x07\x06\x08\x0c\x0a\x0c\x0c\x0b\x0a\x0b\x0b\x0d\x0e\x12\x10\x0d\x0e\x11\x0e\x0b\x0b\x10\x16\x10\x11\x13\x14\x15\x15\x15\x0c\x0f\x17\x18\x16\x14\x18\x12\x14\x15\x14\xff\xdb\x00\x43\x01\x03\x04\x04\x05\x04\x05\x09\x05\x05\x09\x14\x0d\x0b\x0d\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x16\x00\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x01\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xb2\xc0\x07\xff\xd9'
                
                # Send a larger color JPEG instead - create a 100x100 color test pattern
                import io
                from PIL import Image, ImageDraw
                
                try:
                    # Extract image dimensions from path if present
                    width, height = 100, 100  # default size
                    
                    # Parse path to get dimensions if they exist
                    parts = self.path.split('/')
                    if 'full' not in parts:
                        for part in parts:
                            if ',' in part and not part.startswith('0,'):
                                try:
                                    dimensions = part.split(',')
                                    if dimensions[0]:
                                        width = int(dimensions[0])
                                    if len(dimensions) > 1 and dimensions[1]:
                                        height = int(dimensions[1])
                                    break
                                except (ValueError, IndexError):
                                    pass
                    
                    # Create a test image with the specified dimensions
                    img = Image.new('RGB', (width, height), color='white')
                    draw = ImageDraw.Draw(img)
                    
                    # Draw a grid pattern
                    for x in range(0, width, 10):
                        draw.line([(x, 0), (x, height)], fill='lightgray')
                    for y in range(0, height, 10):
                        draw.line([(0, y), (width, y)], fill='lightgray')
                    
                    # Draw border
                    draw.rectangle([0, 0, width-1, height-1], outline='black')
                    
                    # Add text with image info
                    draw.text((10, 10), f"Test {width}x{height}", fill='black')
                    draw.text((10, 30), self.path.split('/')[-1], fill='black')
                    
                    # Convert to JPEG and send
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=85)
                    self.wfile.write(buffer.getvalue())
                except Exception as e:
                    print(f"Error generating image: {e}")
                    # Fallback to blank image if PIL fails
                    self.wfile.write(blank_image)
            else:
                # We're just testing, so return placeholder data
                response = {
                    "service": "IIIF Image API",
                    "path": self.path,
                    "message": "This would normally return image data",
                    "status": "OK"
                }
                
                # If JSONP is requested, wrap the response
                if callback:
                    response_data = f"{callback}({json.dumps(response)});"
                    self.wfile.write(response_data.encode('utf-8'))
                else:
                    self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))
        
        else:
            # For any other endpoint
            response = {
                "service": "IIIF Test Server",
                "path": self.path,
                "message": "Unknown endpoint",
                "status": "OK"
            }
            self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))

    def _update_urls_in_manifest(self, obj, base_url):
        """Update all URLs in a manifest to use the current hostname."""
        def update_urls_recursive(data):
            if isinstance(data, dict):
                for k, v in list(data.items()):
                    if isinstance(v, str) and (v.startswith('http://') or v.startswith('https://')):
                        if 'localhost' in v or '127.0.0.1' in v:
                            # Extract the path part of the URL
                            path = v.split('/', 3)[-1] if len(v.split('/', 3)) >= 4 else ''
                            data[k] = f"{base_url}/{path}"
                    elif isinstance(v, (dict, list)):
                        update_urls_recursive(v)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, (dict, list)):
                        update_urls_recursive(item)
        
        update_urls_recursive(obj)
        return obj

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        # Get the origin header (used for CORS)
        origin = self.headers.get('Origin', '*')
        
        self.send_response(200)
        # Enhanced CORS headers for better cross-origin support
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Origin, Authorization')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Max-Age', '3600')
        # Set security headers for cross-origin resource sharing
        self.send_header('Cross-Origin-Resource-Policy', 'cross-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'unsafe-none')
        self.send_header('Vary', 'Origin')
        self.end_headers()

def create_self_signed_cert():
    """Create a self-signed certificate for HTTPS."""
    try:
        from OpenSSL import crypto
    except ImportError:
        print("OpenSSL module not found. Installing...")
        os.system(f"{sys.executable} -m pip install pyOpenSSL")
        from OpenSSL import crypto
    
    # Create a key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2048)
    
    # Create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C = "US"
    cert.get_subject().ST = "State"
    cert.get_subject().L = "City"
    cert.get_subject().O = "Turath Digital Library"
    cert.get_subject().OU = "IIIF Services"
    cert.get_subject().CN = "localhost"
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365*24*60*60)  # Valid for 1 year
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')
    
    # Write the certificate and key to files
    with open('server.key', 'wb') as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
    with open('server.crt', 'wb') as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    
    print("Created self-signed certificate: server.crt")
    print("Created private key: server.key")
    
    return ('server.crt', 'server.key')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run a IIIF test server")
    parser.add_argument('--http', action='store_true', help='Run in HTTP mode instead of HTTPS')
    parser.add_argument('--port', type=int, help='Port to run the server on (default: 8443 for HTTPS, 8090 for HTTP)')
    return parser.parse_args()

def run_server(port=None, https=True):
    """Run the IIIF test server."""
    # Set default ports
    if port is None:
        port = 8443 if https else 8090
    
    # Change to the script directory to find files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Make sure the public_manifest.json exists
    if not os.path.exists('public_manifest.json'):
        try:
            # Copy from parent directory if exists there
            if os.path.exists('../public_manifest.json'):
                import shutil
                shutil.copy('../public_manifest.json', 'public_manifest.json')
                print("Copied public_manifest.json from parent directory.")
            else:
                # Create a minimal manifest
                with open('public_manifest.json', 'w') as f:
                    json.dump({
                        "@context": "http://iiif.io/api/presentation/2/context.json",
                        "@id": f"{'https' if https else 'http'}://localhost:{port}/public_manifest",
                        "@type": "sc:Manifest",
                        "label": "Test Public Manifest",
                        "sequences": [{
                            "@id": f"{'https' if https else 'http'}://localhost:{port}/sequence/normal",
                            "@type": "sc:Sequence",
                            "canvases": [{
                                "@id": f"{'https' if https else 'http'}://localhost:{port}/canvas/p1",
                                "@type": "sc:Canvas",
                                "label": "Test Page",
                                "width": 800,
                                "height": 1200,
                                "images": [{
                                    "@type": "oa:Annotation",
                                    "motivation": "sc:painting",
                                    "resource": {
                                        "@id": f"{'https' if https else 'http'}://localhost:{port}/image/p1/full/full/0/default.jpg",
                                        "@type": "dctypes:Image",
                                        "format": "image/jpeg",
                                        "width": 800,
                                        "height": 1200,
                                        "service": {
                                            "@context": "http://iiif.io/api/image/2/context.json",
                                            "@id": f"{'https' if https else 'http'}://localhost:{port}/image/p1",
                                            "profile": "http://iiif.io/api/image/2/level1.json"
                                        }
                                    },
                                    "on": f"{'https' if https else 'http'}://localhost:{port}/canvas/p1"
                                }]
                            }]
                        }]
                    }, f, indent=2)
                print("Created default public_manifest.json")
        except Exception as e:
            print(f"Warning: Could not create public_manifest.json: {e}")
    
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimpleIIIFHandler)
    
    # Set HTTP mode flag
    httpd.http_mode = not https
    
    protocol = "HTTPS" if https else "HTTP"
    host = f"https://localhost:{port}" if https else f"http://localhost:{port}"
    
    if https:
        # Create SSL certificate if it doesn't exist
        if not (os.path.exists('server.crt') and os.path.exists('server.key')):
            try:
                create_self_signed_cert()
            except Exception as e:
                print(f"Error creating self-signed certificate: {str(e)}")
                print("Falling back to HTTP mode.")
                return run_server(port=port, https=False)
        
        # Configure SSL
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile='server.crt', keyfile='server.key')
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    
    print(f"Starting {protocol} IIIF test server on 0.0.0.0:{port}")
    print(f"Access at: {host}/")
    print(f"Public manifest URL: {host}/public_manifest")
    
    if https:
        print("\nIMPORTANT: Since this server uses a self-signed certificate,")
        print("you'll need to accept the security warning in your browser.")
        print(f"First visit https://localhost:{port}/ and accept the warning.")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        httpd.server_close()

if __name__ == '__main__':
    args = parse_args()
    run_server(port=args.port, https=not args.http) 
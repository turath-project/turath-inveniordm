#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enhanced HTTP server that simulates a simple IIIF service.
Used to test IIIF connectivity from InvenioRDM.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os

class IIIFTestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Set CORS headers for all responses
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        # Route based on path
        if self.path == '/':
            self.wfile.write(b'{"message": "Hi from IIIF test server!"}')
        elif self.path == '/test_manifest':
            # Return the test manifest JSON
            try:
                with open('test_manifest.json', 'rb') as f:
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self.wfile.write(b'{"error": "Manifest file not found"}')
        elif self.path.startswith('/annotations/'):
            # Return a simple annotation list
            annotations = {
                "@context": "http://iiif.io/api/presentation/2/context.json",
                "@id": "http://localhost:8090" + self.path,
                "@type": "sc:AnnotationList",
                "resources": [
                    {
                        "@type": "oa:Annotation",
                        "motivation": "sc:painting",
                        "resource": {
                            "@type": "cnt:ContentAsText",
                            "format": "text/plain",
                            "chars": "This is a test annotation from the test server."
                        },
                        "on": "http://localhost:8090/canvas/test"
                    }
                ]
            }
            self.wfile.write(json.dumps(annotations).encode('utf-8'))
        elif self.path.startswith('/search'):
            # Return a simple search result
            search_result = {
                "@context": "http://iiif.io/api/search/0/context.json",
                "@id": "http://localhost:8090" + self.path,
                "@type": "sc:AnnotationList",
                "resources": [
                    {
                        "@type": "oa:Annotation",
                        "motivation": "sc:painting",
                        "resource": {
                            "@type": "cnt:ContentAsText",
                            "chars": "This is a test search result."
                        },
                        "on": "http://localhost:8090/canvas/test"
                    }
                ]
            }
            self.wfile.write(json.dumps(search_result).encode('utf-8'))
        elif self.path.startswith('/autocomplete'):
            # Return a simple autocomplete result
            autocomplete = {
                "@context": "http://iiif.io/api/search/0/context.json",
                "@id": "http://localhost:8090" + self.path,
                "@type": "search:TermList",
                "terms": [
                    {"match": "test", "url": "http://localhost:8090/search?q=test", "count": 1}
                ]
            }
            self.wfile.write(json.dumps(autocomplete).encode('utf-8'))
        else:
            # For any other path, return info about the request
            response = {
                "message": "Test IIIF service response",
                "path": self.path,
                "method": "GET",
                "service": "IIIF Test Server"
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))

    def do_OPTIONS(self):
        # Handle preflight requests for CORS
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def run_server(port=8090):
    # Change to the script directory to find the manifest file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Bind to all interfaces, not just localhost
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, IIIFTestHandler)
    print(f"Starting enhanced IIIF test server on 0.0.0.0:{port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server() 
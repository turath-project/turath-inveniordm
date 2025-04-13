#!/usr/bin/env python3
"""
Simple HTTP server to serve the IIIF viewer HTML page, handling CORS issues.
"""

import http.server
import socketserver
import os

PORT = 3000

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler with CORS headers."""
    
    def end_headers(self):
        """Add CORS headers to every response."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        self.end_headers()

def serve():
    """Start the HTTP server."""
    print(f"Starting HTTP server on port {PORT}...")
    print(f"Open http://localhost:{PORT}/iiif_viewer.html in your browser")
    
    with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
        try:
            print(f"Server running at http://localhost:{PORT}/")
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped by user")
            httpd.server_close()

if __name__ == "__main__":
    serve() 
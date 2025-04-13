#!/usr/bin/env python
"""
Comprehensive IIIF Integration Test Suite

This script performs a full end-to-end test of the IIIF integration:
1. Starts the test server in the background
2. Tests all IIIF endpoints and features
3. Provides a detailed test summary
4. Stops the test server on completion

Usage:
    python scripts/AlA/test_integration_all.py
"""

import os
import sys
import json
import time
import signal
import requests
import subprocess
import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("test-integration")

# Default values
server_url = "http://127.0.0.1:5002"
record_id = "202"
filename = "test.pdf"
server_process = None
test_results = {
    "server_connection": {"status": False, "details": "Not tested"},
    "record_access": {"status": False, "details": "Not tested"},
    "manifest_generation": {"status": False, "details": "Not tested"},
    "pdf_access": {"status": False, "details": "Not tested"},
    "image_access": {"status": False, "details": "Not tested"},
    "page_navigation": {"status": False, "details": "Not tested"},
    "iiif_configuration": {"status": False, "details": "Not tested"}
}

def start_test_server():
    """Start the test IIIF server in the background."""
    logger.info("Starting test IIIF server...")
    
    # Get absolute path to script
    script_path = Path(os.path.dirname(os.path.abspath(__file__))) / "run_iiif_server.py"
    
    # Make sure script exists and is executable
    if not script_path.exists():
        logger.error(f"❌ Test server script not found at {script_path}")
        return False
    
    # Ensure script is executable
    try:
        os.chmod(script_path, 0o755)
    except Exception as e:
        logger.error(f"❌ Could not make script executable: {e}")
    
    # Start server as subprocess
    try:
        global server_process
        server_process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait a moment for server to start
        logger.info("Waiting for server to start...")
        time.sleep(3)
        
        # Check if process is running
        if server_process.poll() is not None:
            stderr = server_process.stderr.read().decode('utf-8')
            logger.error(f"❌ Server failed to start: {stderr}")
            return False
        
        logger.info("✅ Test server started successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Error starting test server: {e}")
        return False

def stop_test_server():
    """Stop the test IIIF server."""
    global server_process
    if server_process:
        logger.info("Stopping test server...")
        try:
            # First try graceful termination
            server_process.terminate()
            # Wait a bit for graceful shutdown
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # If it didn't respond to terminate, force kill
                server_process.kill()
            
            logger.info("✅ Test server stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping test server: {e}")

def test_server_connection():
    """Test connection to the server."""
    logger.info(f"Testing connection to server: {server_url}")
    
    try:
        response = requests.get(server_url, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Successfully connected to server")
            test_results["server_connection"]["status"] = True
            test_results["server_connection"]["details"] = f"Connected to {server_url}, status 200"
            return True
        else:
            logger.error(f"❌ Error connecting to server: {response.status_code}")
            test_results["server_connection"]["details"] = f"Failed with status {response.status_code}"
            return False
    except Exception as e:
        logger.error(f"❌ Error connecting to server: {e}")
        test_results["server_connection"]["details"] = f"Exception: {str(e)}"
        return False

def test_record_access():
    """Test access to the record API."""
    url = urljoin(server_url, f"/api/records/{record_id}")
    logger.info(f"Testing record access: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Successfully accessed record API")
            try:
                record_data = response.json()
                title = record_data.get('metadata', {}).get('title', 'Unknown')
                logger.info(f"Record title: {title}")
                
                # Extract file information
                files = record_data.get('files', {}).get('entries', [])
                file_info = []
                for file in files:
                    file_info.append(f"{file.get('key')} ({file.get('size')} bytes)")
                    logger.info(f"File: {file.get('key')} ({file.get('size')} bytes, {file.get('mimetype')})")
                
                test_results["record_access"]["status"] = True
                test_results["record_access"]["details"] = f"Title: {title}, Files: {', '.join(file_info)}"
                return record_data
            except Exception as e:
                logger.error(f"❌ Error parsing record data: {e}")
                test_results["record_access"]["details"] = f"Failed to parse JSON: {str(e)}"
                return None
        else:
            logger.error(f"❌ Error accessing record: {response.status_code}")
            test_results["record_access"]["details"] = f"Failed with status {response.status_code}"
            return None
    except Exception as e:
        logger.error(f"❌ Error accessing record: {e}")
        test_results["record_access"]["details"] = f"Exception: {str(e)}"
        return None

def test_manifest_generation():
    """Test IIIF manifest generation for a PDF file."""
    url = urljoin(server_url, f"/api/iiif/manifest/{record_id}")
    logger.info(f"Testing manifest generation: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Successfully generated manifest")
            try:
                manifest = response.json()
                
                # Check for required manifest fields
                required_fields = ["@context", "@id", "@type", "sequences"]
                missing_fields = [field for field in required_fields if field not in manifest]
                
                if missing_fields:
                    logger.warning(f"⚠️ Manifest missing required fields: {', '.join(missing_fields)}")
                    test_results["manifest_generation"]["details"] = f"Missing fields: {', '.join(missing_fields)}"
                else:
                    logger.info("✅ Manifest contains all required fields")
                    test_results["manifest_generation"]["status"] = True
                
                # Get number of canvases (pages)
                canvas_count = 0
                if "sequences" in manifest and manifest["sequences"]:
                    canvases = manifest["sequences"][0].get("canvases", [])
                    canvas_count = len(canvases)
                    logger.info(f"Manifest contains {canvas_count} canvas(es) (pages)")
                    
                    # Print canvas IDs
                    for i, canvas in enumerate(canvases[:3]):  # Show first 3 canvases
                        logger.info(f"Canvas {i+1} ID: {canvas.get('@id', 'Unknown')}")
                        
                        # Check for images in canvas
                        if "images" in canvas and canvas["images"]:
                            image = canvas["images"][0]
                            resource = image.get("resource", {})
                            image_url = resource.get("@id", "Unknown")
                            logger.info(f"  Image URL: {image_url}")
                        else:
                            logger.warning(f"  ⚠️ Canvas {i+1} has no images")
                else:
                    logger.warning("⚠️ Manifest has no canvases/pages")
                
                test_results["manifest_generation"]["details"] = f"Contains {canvas_count} pages"
                return manifest
            except Exception as e:
                logger.error(f"❌ Error parsing manifest: {e}")
                test_results["manifest_generation"]["details"] = f"Failed to parse JSON: {str(e)}"
                return None
        else:
            logger.error(f"❌ Error generating manifest: {response.status_code}")
            test_results["manifest_generation"]["details"] = f"Failed with status {response.status_code}"
            return None
    except Exception as e:
        logger.error(f"❌ Error generating manifest: {e}")
        test_results["manifest_generation"]["details"] = f"Exception: {str(e)}"
        return None

def test_image_access():
    """Test accessing images through the IIIF API."""
    logger.info("=== Testing Image Access ===")
    
    # Get the manifest to extract image URLs
    manifest = test_manifest_generation()
    if not manifest:
        logger.error("❌ Cannot test image access without manifest")
        test_results["image_access"]["details"] = "No manifest available"
        return False
    
    # Try to find image URLs in the manifest
    image_urls = []
    if "sequences" in manifest and manifest["sequences"]:
        canvases = manifest["sequences"][0].get("canvases", [])
        for canvas in canvases:
            if "images" in canvas and canvas["images"]:
                image = canvas["images"][0]
                resource = image.get("resource", {})
                image_url = resource.get("@id", "")
                if image_url:
                    image_urls.append(image_url)
    
    if not image_urls:
        logger.error("❌ No image URLs found in manifest")
        test_results["image_access"]["details"] = "No image URLs in manifest"
        return False
    
    # Test the first image URL
    success_count = 0
    for i, url in enumerate(image_urls[:3]):  # Test up to 3 images
        logger.info(f"Testing image access ({i+1}/{len(image_urls)}): {url}")
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', 'unknown')
                logger.info(f"✅ Successfully accessed image {i+1}. Content type: {content_type}")
                success_count += 1
            else:
                logger.error(f"❌ Error accessing image {i+1}: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error accessing image {i+1}: {e}")
    
    if success_count > 0:
        test_results["image_access"]["status"] = True
        test_results["image_access"]["details"] = f"Successfully accessed {success_count}/{min(3, len(image_urls))} images"
        return True
    else:
        test_results["image_access"]["details"] = "Failed to access any images"
        return False

def test_page_navigation():
    """Test navigating through PDF pages."""
    logger.info("=== Testing PDF Page Navigation ===")
    
    # Get page count from manifest
    manifest = test_manifest_generation()
    page_count = 3  # Default
    
    if manifest and "sequences" in manifest and manifest["sequences"]:
        canvases = manifest["sequences"][0].get("canvases", [])
        page_count = len(canvases)
    
    # Test accessing different pages
    success_count = 0
    
    for page in range(1, page_count + 1):
        url = urljoin(server_url, f"/api/iiif/image/{record_id}/{filename}")
        params = {
            "page": page,
            "region": "full",
            "size": "full"
        }
        
        logger.info(f"Testing access to page {page}/{page_count}: {url}")
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', 'unknown')
                logger.info(f"✅ Successfully accessed page {page}. Content type: {content_type}")
                success_count += 1
            else:
                logger.error(f"❌ Error accessing page {page}: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error accessing page {page}: {e}")
    
    if success_count == page_count:
        test_results["page_navigation"]["status"] = True
        test_results["page_navigation"]["details"] = f"Successfully accessed all {page_count} pages"
        return True
    elif success_count > 0:
        test_results["page_navigation"]["status"] = True
        test_results["page_navigation"]["details"] = f"Accessed {success_count}/{page_count} pages"
        return True
    else:
        test_results["page_navigation"]["details"] = "Failed to access any pages"
        return False

def test_pdf_access():
    """Test direct access to the PDF file."""
    logger.info("=== Testing Direct PDF Access ===")
    
    pdf_url = urljoin(server_url, f"/files/{filename}")
    logger.info(f"Testing PDF access: {pdf_url}")
    
    try:
        # Use HEAD request to avoid downloading the entire file
        response = requests.head(pdf_url, timeout=10)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', 'unknown')
            content_length = response.headers.get('Content-Length', 'unknown')
            logger.info(f"✅ Successfully accessed PDF. Content type: {content_type}")
            logger.info(f"  Content length: {content_length} bytes")
            test_results["pdf_access"]["status"] = True
            test_results["pdf_access"]["details"] = f"Type: {content_type}, Size: {content_length} bytes"
            
            # Try downloading a small portion to verify content
            range_response = requests.get(pdf_url, headers={'Range': 'bytes=0-1023'}, timeout=10)
            if range_response.status_code == 206:
                logger.info("✅ Successfully downloaded partial PDF content")
            
            return True
        else:
            logger.error(f"❌ Error accessing PDF: {response.status_code}")
            test_results["pdf_access"]["details"] = f"Failed with status {response.status_code}"
            return False
    except Exception as e:
        logger.error(f"❌ Error accessing PDF: {e}")
        test_results["pdf_access"]["details"] = f"Exception: {str(e)}"
        return False

def test_iiif_configuration():
    """Test IIIF configuration by examining the manifest content."""
    logger.info("=== Testing IIIF Configuration ===")
    
    manifest = test_manifest_generation()
    if not manifest:
        logger.error("❌ Cannot test IIIF configuration without manifest")
        test_results["iiif_configuration"]["details"] = "No manifest available"
        return False
    
    # Check context
    context = manifest.get('@context', '')
    if 'http://iiif.io/api/presentation/' in str(context):
        logger.info(f"✅ Manifest uses IIIF Presentation API context: {context}")
        test_results["iiif_configuration"]["status"] = True
    else:
        logger.warning(f"⚠️ Manifest does not use standard IIIF context: {context}")
    
    # Check if the manifest includes a PDF profile or mimetype
    has_pdf_references = False
    
    # Check sequences and canvases for PDF references
    if "sequences" in manifest and manifest["sequences"]:
        for sequence in manifest["sequences"]:
            for canvas in sequence.get("canvases", []):
                for image in canvas.get("images", []):
                    resource = image.get("resource", {})
                    format = resource.get("format", "")
                    if "pdf" in format.lower():
                        has_pdf_references = True
                        logger.info(f"✅ Found PDF reference in canvas: {format}")
    
    if not has_pdf_references:
        logger.warning("⚠️ No PDF references found in manifest")
    
    test_results["iiif_configuration"]["details"] = f"Context: {context}, PDF references: {'Yes' if has_pdf_references else 'No'}"
    return test_results["iiif_configuration"]["status"]

def print_test_summary():
    """Print a summary of all test results."""
    logger.info("\n" + "="*80)
    logger.info("               IIIF INTEGRATION TEST SUMMARY                ")
    logger.info("="*80)
    logger.info(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Server URL: {server_url}")
    logger.info(f"Record ID: {record_id}")
    logger.info(f"Filename: {filename}")
    logger.info("-"*80)
    
    # Count successes
    success_count = sum(1 for test in test_results.values() if test["status"])
    total_count = len(test_results)
    
    # Print results in table format
    logger.info(f"{'TEST':<25} | {'STATUS':<10} | {'DETAILS'}")
    logger.info("-"*80)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result["status"] else "❌ FAIL"
        details = result["details"]
        # Format test name for better readability
        formatted_name = " ".join(word.capitalize() for word in test_name.split("_"))
        logger.info(f"{formatted_name:<25} | {status:<10} | {details}")
    
    logger.info("-"*80)
    logger.info(f"Overall Result: {success_count}/{total_count} tests passed")
    
    if success_count == total_count:
        logger.info("✅ ALL TESTS PASSED - IIIF integration is working correctly")
    elif success_count > total_count / 2:
        logger.info("⚠️ PARTIAL SUCCESS - IIIF integration is partially working")
    else:
        logger.info("❌ TESTS FAILED - IIIF integration is not working correctly")
    
    logger.info("="*80)

def main():
    """Main function to run all tests."""
    logger.info("=== IIIF Integration Test Suite ===")
    
    try:
        # Start test server
        if not start_test_server():
            logger.error("❌ Failed to start test server - aborting tests")
            return False
        
        # Wait for server to be fully ready
        time.sleep(2)
        
        # Run all tests
        test_server_connection()
        test_record_access()
        test_manifest_generation()
        test_image_access()
        test_page_navigation()
        test_pdf_access()
        test_iiif_configuration()
        
        # Print test summary
        print_test_summary()
        
        return True
    
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        return False
    
    except Exception as e:
        logger.error(f"Error during tests: {e}")
        return False
    
    finally:
        # Always stop the server
        stop_test_server()

if __name__ == "__main__":
    main() 
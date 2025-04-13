# IIIF Implementation Code Examples

This document provides comprehensive code examples for implementing IIIF functionality in Zenodo-RDM, including scripts, command outputs, and debugging techniques.

## Image Conversion Scripts

### Single File Converter - `convert_to_ptif.py`

This is the complete code for converting a single image file to PTIF format:

```python
#!/usr/bin/env python3
"""
Script to convert an image file to PTIF format for IIIF support.
"""

import os
import sys
import subprocess
import shutil
import json
import time

def check_dependencies():
    """Check if required tools are installed."""
    try:
        # Check kdu_compress
        subprocess.run(["kdu_compress", "-v"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("❌ Error: kdu_compress not found. Please install kakadu tools.")
        return False

def convert_to_ptif(input_file, output_file=None):
    """Convert an image file to PTIF format using kakadu."""
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file {input_file} does not exist.")
        return False
    
    if output_file is None:
        # Use the same name but with .ptif extension
        base, _ = os.path.splitext(input_file)
        output_file = f"{base}.ptif"
    
    print(f"Converting {input_file} to {output_file}...")
    
    # Run kdu_compress command
    try:
        result = subprocess.run([
            "kdu_compress",
            "-i", input_file,
            "-o", output_file,
            "-rate", "2.4,1.48331273,.91673033,.56657224,.35016049,.21641118,.13374944,.08266171",
            "-jp2_space", "sRGB",
            "-quiet"
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Check if output file was created and has content
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            print(f"✅ Successfully converted to {output_file}")
            print(f"   File size: {os.path.getsize(output_file)} bytes")
            return True
        else:
            print(f"❌ Error: Output file {output_file} was not created or is empty.")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during conversion: {e.stderr.decode() if e.stderr else str(e)}")
        return False

def check_iipserver_env():
    """Check the IIPServer environment and filesystem prefix."""
    print("IIPServer environment: ")
    
    try:
        # Run docker-compose command to check environment variables
        result = subprocess.run([
            "docker-compose", "exec", "iipserver", "env"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Get the output
        output = result.stdout.decode()
        
        # Parse the output to find the filesystem prefix
        prefix = "/images/public"  # Default value
        for line in output.split('\n'):
            if "FILESYSTEM_PREFIX" in line:
                prefix = line.split('=')[1].strip()
                break
        
        print(f"Using IIPServer filesystem prefix: {prefix}")
        return prefix
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error checking IIPServer environment: {e}")
        print("Using default prefix: /images/public")
        return "/images/public"

def copy_to_iipserver(ptif_file, record_id=None):
    """Copy the PTIF file to the IIPServer's accessible location."""
    if not os.path.exists(ptif_file):
        print(f"❌ Error: PTIF file {ptif_file} does not exist.")
        return None
    
    # Get the filename without path
    filename = os.path.basename(ptif_file)
    
    # Create a target filename for IIPServer
    if record_id:
        # Use a naming convention that works with IIPServer's configuration
        base_name = os.path.splitext(filename)[0]
        target_filename = f"private_{record_id}_{base_name}.ptif"
    else:
        target_filename = filename
    
    # Get the IIPServer filesystem prefix
    prefix = check_iipserver_env()
    
    # Copy the file to /tmp first to ensure Docker has access
    tmp_file = f"/tmp/{os.path.basename(ptif_file)}"
    shutil.copy(ptif_file, tmp_file)
    print(f"Copied {ptif_file} to {tmp_file}")
    
    try:
        # Copy the file to IIPServer container
        result = subprocess.run([
            "docker-compose", "exec", "iipserver", 
            "cp", tmp_file, f"{prefix}/{target_filename}"
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"✅ Successfully copied {filename} to IIPServer at {prefix}/{target_filename}")
        
        # Return the target filename for IIIF URL construction
        return target_filename
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error copying file to IIPServer: {e}")
        return None

def verify_iiif_url(ptif_filename):
    """Print the IIIF URL for testing."""
    iiif_url = f"http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/{ptif_filename}/info.json"
    
    print("\nTo verify IIIF functionality, use the following URLs:")
    print(f"Metadata: {iiif_url}")
    print(f"Thumbnail: http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/{ptif_filename}/full/200,/0/default.jpg")
    print(f"Image region: http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/{ptif_filename}/0,0,100,100/full/0/default.jpg")

def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} INPUT_FILE [RECORD_ID]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    record_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Convert the file to PTIF format
    output_file = f"{os.path.splitext(input_file)[0]}.ptif"
    if not convert_to_ptif(input_file, output_file):
        sys.exit(1)
    
    # Copy the PTIF file to IIPServer
    ptif_filename = copy_to_iipserver(output_file, record_id)
    if not ptif_filename:
        sys.exit(1)
    
    # Print IIIF URLs for testing
    verify_iiif_url(ptif_filename)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Batch Processor - `batch_convert.py`

This is the complete code for batch-processing all images in a record:

```python
#!/usr/bin/env python3
"""
Batch script to convert all images in a Zenodo-RDM record to PTIF format for IIIF support.
"""

import os
import sys
import requests
import json
import subprocess
import shutil
import time
from urllib3.exceptions import InsecureRequestWarning

# Import our single file conversion script
from convert_to_ptif import convert_to_ptif, copy_to_iipserver

# Disable SSL warnings for local testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def get_record_files(record_id):
    """Get all files from a record."""
    print(f"Getting files for record {record_id}...")
    
    try:
        # Get record data
        url = f"https://127.0.0.1:5000/api/records/{record_id}"
        response = requests.get(url, verify=False)
        
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            print(response.text)
            return None
        
        data = response.json()
        
        # Extract all image files
        files = data.get('files', [])
        image_files = []
        
        for file in files:
            key = file.get('key', '')
            size = file.get('size', 0)
            
            if key.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
                image_files.append({
                    'key': key,
                    'size': size
                })
        
        print(f"Found {len(image_files)} image files")
        return image_files
    
    except Exception as e:
        print(f"Error getting record files: {e}")
        return None

def download_file(record_id, filename, output_dir):
    """Download a file from a record."""
    print(f"Downloading {filename}...")
    
    try:
        # Get file download link
        url = f"https://127.0.0.1:5000/api/records/{record_id}/files/{filename}/content"
        
        # Download the file with stream=True to handle large files
        response = requests.get(url, verify=False, stream=True)
        
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            print(response.text)
            return None
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save the file
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Downloaded to {output_path}")
        return output_path
    
    except Exception as e:
        print(f"Error downloading file: {e}")
        return None

def verify_iiif_manifest(record_id):
    """Check if the IIIF manifest for this record exists and is valid."""
    manifest_url = f"https://127.0.0.1:5000/api/iiif/record/{record_id}/manifest"
    
    try:
        headers = {"Accept": "application/json"}
        response = requests.get(manifest_url, headers=headers, verify=False)
        
        if response.status_code != 200:
            print(f"❌ IIIF manifest not accessible: HTTP {response.status_code}")
            return False
        
        manifest = response.json()
        
        # Check for sequences and canvases
        sequences = manifest.get('sequences', [])
        if not sequences:
            print("❌ Manifest does not contain any sequences")
            return False
        
        sequence = sequences[0]
        canvases = sequence.get('canvases', [])
        if not canvases:
            print("❌ Sequence does not contain any canvases")
            return False
        
        print(f"✅ IIIF manifest accessible with {len(canvases)} images")
        return True
    
    except Exception as e:
        print(f"Error checking IIIF manifest: {e}")
        return False

def batch_convert(record_id):
    """Convert all images in a record to PTIF format."""
    # Get files from the record
    image_files = get_record_files(record_id)
    if not image_files:
        print("No image files found or error occurred.")
        return False
    
    # Create a temporary directory for downloaded files
    temp_dir = f"temp_record_{record_id}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Process each image file
        success_count = 0
        failed_count = 0
        
        for idx, file_info in enumerate(image_files):
            filename = file_info['key']
            print(f"\n[{idx+1}/{len(image_files)}] Processing {filename}...")
            
            # Download the file
            download_path = download_file(record_id, filename, temp_dir)
            if not download_path:
                print(f"❌ Failed to download {filename}")
                failed_count += 1
                continue
            
            # Convert to PTIF
            ptif_path = f"{os.path.splitext(download_path)[0]}.ptif"
            if not convert_to_ptif(download_path, ptif_path):
                print(f"❌ Failed to convert {filename} to PTIF")
                failed_count += 1
                continue
            
            # Copy to IIPServer
            base_name = os.path.splitext(os.path.basename(filename))[0]
            ptif_filename = copy_to_iipserver(ptif_path, record_id)
            if not ptif_filename:
                print(f"❌ Failed to copy {filename} to IIPServer")
                failed_count += 1
                continue
            
            # Success
            success_count += 1
        
        # Summarize results
        print(f"\nConversion complete: {success_count} successful, {failed_count} failed")
        
        # Verify the IIIF manifest is now accessible
        print("\nChecking IIIF manifest...")
        verify_iiif_manifest(record_id)
        
        print("\nTo test IIIF functionality, open the following URL in your browser:")
        print(f"https://127.0.0.1:5000/records/{record_id}")
        
        return success_count > 0
    
    finally:
        # Clean up
        print(f"\nCleaning up temporary directory {temp_dir}...")
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} RECORD_ID")
        sys.exit(1)
    
    record_id = sys.argv[1]
    if batch_convert(record_id):
        print(f"\n✅ Successfully processed record {record_id}")
        sys.exit(0)
    else:
        print(f"\n❌ Failed to process record {record_id}")
        sys.exit(1)
```

## Custom IIIF Viewer

### HTML Viewer - `iiif_viewer.html`

This is the complete code for the custom IIIF viewer:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IIIF Image Viewer</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/openseadragon@3.1.0/build/openseadragon/openseadragon.min.css">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }
        .viewer-container {
            width: 100%;
            height: 600px;
            border: 1px solid #ddd;
            margin: 20px 0;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"], select {
            width: 100%;
            padding: 8px;
            box-sizing: border-box;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        .thumbnail-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 20px;
        }
        .thumbnail {
            width: 150px;
            cursor: pointer;
            border: 1px solid #ddd;
            transition: transform 0.2s;
        }
        .thumbnail:hover {
            transform: scale(1.05);
            border-color: #4CAF50;
        }
        .info-panel {
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 4px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>IIIF Image Viewer</h1>
        
        <div class="form-group">
            <label for="record-id">Record ID:</label>
            <input type="text" id="record-id" value="202">
        </div>
        
        <div class="form-group">
            <label for="image-filename">Image Filename (without extension):</label>
            <input type="text" id="image-filename" value="page-001">
        </div>
        
        <button id="load-image">Load Image</button>
        
        <div id="viewer" class="viewer-container"></div>
        
        <div class="info-panel">
            <h3>Image Information</h3>
            <pre id="image-info">Loading...</pre>
        </div>
        
        <h3>Thumbnails for Record 202</h3>
        <div class="thumbnail-grid" id="thumbnails">
            <p>Loading thumbnails...</p>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/openseadragon@3.1.0/build/openseadragon/openseadragon.min.js"></script>
    <script>
        // Initialize the viewer
        let viewer = OpenSeadragon({
            id: "viewer",
            prefixUrl: "https://cdn.jsdelivr.net/npm/openseadragon@3.1.0/build/openseadragon/images/",
            preserveViewport: true,
            visibilityRatio: 1,
            minZoomLevel: 1,
            defaultZoomLevel: 1,
            sequenceMode: false,
            tileSources: []
        });
        
        // Function to load an image using IIIF
        function loadImage(recordId, filename) {
            const infoUrl = `http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/private_${recordId}_${filename}.ptif/info.json`;
            
            // Update the viewer
            viewer.open(infoUrl);
            
            // Fetch and display image info
            fetch(infoUrl)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    document.getElementById('image-info').textContent = JSON.stringify(data, null, 2);
                })
                .catch(error => {
                    document.getElementById('image-info').textContent = `Error loading image info: ${error.message}`;
                });
        }
        
        // Event listener for the load button
        document.getElementById('load-image').addEventListener('click', function() {
            const recordId = document.getElementById('record-id').value;
            const filename = document.getElementById('image-filename').value;
            loadImage(recordId, filename);
        });
        
        // Function to load thumbnails for a record
        function loadThumbnails(recordId) {
            const thumbnailContainer = document.getElementById('thumbnails');
            thumbnailContainer.innerHTML = '';
            
            // List of page numbers for record 202 (hardcoded for demo)
            const pages = Array.from({length: 28}, (_, i) => i + 1).map(num => 
                String(num).padStart(3, '0')
            );
            
            pages.forEach(page => {
                const thumbnailUrl = `http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/private_${recordId}_page-${page}.ptif/full/150,/0/default.jpg`;
                const img = document.createElement('img');
                img.src = thumbnailUrl;
                img.alt = `Page ${page}`;
                img.className = 'thumbnail';
                img.onclick = function() {
                    document.getElementById('image-filename').value = `page-${page}`;
                    loadImage(recordId, `page-${page}`);
                };
                thumbnailContainer.appendChild(img);
            });
        }
        
        // Load initial image and thumbnails when page loads
        window.onload = function() {
            const recordId = document.getElementById('record-id').value;
            const filename = document.getElementById('image-filename').value;
            loadImage(recordId, filename);
            loadThumbnails(recordId);
        };
    </script>
</body>
</html>
```

### Python HTTP Server - `serve_viewer.py`

This is the complete code for the Python HTTP server:

```python
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
```

## Testing and Verification Examples

### Checking IIPServer Configuration

```bash
# Command
docker-compose exec iipserver env | grep -i filesystem

# Sample Output
FILESYSTEM_PREFIX=/images/public
```

### Checking IIPServer Directory Structure

```bash
# Command
docker-compose exec iipserver ls -la /images/

# Sample Output
total 4
drwxr-xr-x 1 root root 4096 Apr  4 23:02 .
drwxr-xr-x 1 root root 4096 Apr  4 23:02 ..
drwxr-xr-x 2 root root 4096 Apr  4 23:02 private
drwxr-xr-x 2 root root 4096 Apr  4 23:02 public
```

### Testing IIIF Access

```bash
# Command to get IIIF metadata
curl "http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/private_202_page-001.ptif/info.json" | jq

# Sample Output
{
  "@context": "http://iiif.io/api/image/3/context.json",
  "protocol": "http://iiif.io/api/image",
  "width": 1982,
  "height": 2831,
  "sizes": [
    {
      "width": 123,
      "height": 176
    },
    {
      "width": 247,
      "height": 353
    },
    {
      "width": 495,
      "height": 707
    },
    {
      "width": 991,
      "height": 1415
    }
  ],
  "tiles": [
    {
      "width": 256,
      "height": 256,
      "scaleFactors": [
        1,
        2,
        4,
        8,
        16
      ]
    }
  ],
  "id": "http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/private_202_page-001.ptif",
  "type": "ImageService3",
  "profile": "level2",
  "maxWidth": 5000,
  "maxHeight": 5000,
  "extraQualities": [
    "color",
    "gray",
    "bitonal"
  ],
  "extraFormats": [
    "webp"
  ],
  "extraFeatures": [
    "regionByPct",
    "sizeByForcedWh",
    "sizeByWh",
    "sizeAboveFull",
    "sizeUpscaling",
    "rotationBy90s",
    "mirroring"
  ],
  "service": [
    {
      "@context": "http://iiif.io/api/annex/services/physdim/1/context.json",
      "profile": "http://iiif.io/api/annex/services/physdim",
      "physicalScale": 0.00333333,
      "physicalUnits": "in"
    }
  ]
}

# Command to download a thumbnail
curl "http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/private_202_page-001.ptif/full/200,/0/default.jpg" --output page-001-thumbnail.jpg

# Sample Output
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  5974  100  5974    0     0   5974      0  0:00:01 --:--:--  0:00:01 3916k
```

### Checking IIIF Manifest Endpoint

```bash
# Command
curl -H "Accept: application/json" "https://127.0.0.1:5000/api/iiif/record/202/manifest" -k | jq

# Sample Error Output
{
  "status": 406,
  "message": "Invalid 'Accept' header. Expected one of: application/ld+json"
}

# Command with different header
curl -H "Accept: application/ld+json" "https://127.0.0.1:5000/api/iiif/record/202/manifest" -k | jq

# Sample Error Output
{
  "status": 406,
  "message": "Invalid 'Accept' header. Expected one of: application/json"
}
```

## Debugging and Troubleshooting Examples

### Checking if a File Exists in IIPServer

```bash
# Command
docker-compose exec iipserver ls -la /images/public/private_202_page-001.ptif

# Sample Output for Existing File
-rw-r--r-- 1 root root 438444 Apr  5 00:15 /images/public/private_202_page-001.ptif

# Sample Output for Missing File
ls: cannot access '/images/public/private_202_page-001.ptif': No such file or directory
```

### Verifying the PTIF Conversion

```bash
# Command to check file type
file temp_record_202/page-001.ptif

# Sample Output
temp_record_202/page-001.ptif: TIFF image data, big-endian, direntries=20, height=2831, bps=0, compression=none, PhotometricIntepretation=RGB, width=1982
```

### Testing Image Conversion Directly

```bash
# Command
kdu_compress -i data/images/private/202/page-001.tif -o test_output.ptif -rate 2.4,1.48331273,.91673033,.56657224,.35016049,.21641118,.13374944,.08266171 -jp2_space sRGB

# Sample Output
Kakadu Core-8.0 (c) 2017 Kakadu Software Pty Ltd
Produced by data/images/private/202/page-001.tif
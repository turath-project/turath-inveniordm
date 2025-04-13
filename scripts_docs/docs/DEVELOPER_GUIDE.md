# Zenodo RDM Developer Guide

This guide explains the process of adapting the CERN Zenodo RDM application for local development environments. It covers the key modifications made, why they were necessary, and how to further adapt the application for your needs.

## Understanding the Project Architecture

Zenodo RDM is built on the InvenioRDM framework, a modern repository platform for managing and publishing research data. Here's a high-level overview of the architecture:

```
┌───────────────────────────────────────────┐
│              Web Browser                  │
└───────────────┬───────────────────────────┘
                │
┌───────────────▼───────────────────────────┐
│           Nginx (Frontend)                │
└─┬─────────────────────────┬───────────────┘
  │                         │
┌─▼──────────────┐  ┌───────▼──────────┐
│    Web UI      │  │      API         │
└─┬──────────────┘  └───────┬──────────┘
  │                         │
┌─▼─────────────────────────▼──────────────┐
│        InvenioRDM Framework               │
└─┬─────────────┬──────────┬───────────────┘
  │             │          │
┌─▼───────┐  ┌──▼────┐  ┌──▼──────┐  ┌──────────┐
│PostgreSQL│  │Redis  │  │RabbitMQ │  │OpenSearch│
└─────────┘  └───────┘  └─────────┘  └──────────┘
```

## Key Modifications for Local Development

### 1. Docker Images & Registry Changes

**Problem:** The original Zenodo RDM project uses CERN's private Docker registry which is not accessible for local development.

**Solution:** Replace all Docker image references to use publicly available images from Docker Hub.

#### Before:
```yaml
# Original docker-services.yml
services:
  cache:
    image: registry.cern.ch/docker.io/library/redis
    # ...
  db:
    image: registry.cern.ch/docker.io/library/postgres:12.4
    # ...
```

#### After:
```yaml
# Modified docker-services.yml
services:
  cache:
    image: redis:latest
    # ...
  db:
    image: postgres:12.4
    # ...
```

### 2. Dockerfile Simplification

**Problem:** The original Dockerfile contains CERN-specific dependencies and configurations.

**Solution:** Simplify the Dockerfile to use a standard Alpine Linux base image and only include essential dependencies.

#### Before:
```dockerfile
FROM registry.cern.ch/inveniosoftware/almalinux:1

# XRootD
ARG xrootd_version="5.5.5"
# Repo required to find all the releases of XRootD
RUN dnf config-manager --add-repo https://cern.ch/xrootd/xrootd.repo
RUN if [ ! -z "$xrootd_version" ] ; then XROOTD_V="-$xrootd_version" ; else XROOTD_V="" ; fi && \
    echo "Will install xrootd version: $XROOTD_V (latest if empty)" && \
    dnf install -y xrootd"$XROOTD_V" python3-xrootd"$XROOTD_V"
# ...
```

#### After:
```dockerfile
FROM python:3.9-alpine

# Install system dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    libxml2-dev \
    libxslt-dev \
    jpeg-dev \
    git \
    curl \
    nodejs \
    npm \
    bash
    
# Install additional dependencies
RUN pip install pipenv
# ...
```

### 3. HTTP vs HTTPS for Local Development

**Problem:** The original application forces HTTPS, which requires certificates that are difficult to set up locally.

**Solution:** Modify the security settings to allow HTTP for local development.

#### Before:
```python
# invenio.cfg
APP_DEFAULT_SECURE_HEADERS = {
    # ...
    "force_https": True,
    "session_cookie_secure": True,
    "strict_transport_security": True,
    # ...
}
```

#### After:
```python
# invenio.cfg
APP_DEFAULT_SECURE_HEADERS = {
    # ...
    "force_https": False,  # Changed to False for local development
    "session_cookie_secure": False,  # Changed to False for local development
    "strict_transport_security": False,  # Changed to False for local development
    # ...
}
```

### 4. Service URLs and Endpoints

**Problem:** All services were configured to use HTTPS URLs.

**Solution:** Update service URLs to use HTTP and appropriate ports for local access.

#### Before:
```python
# Environment variables in docker-services.yml
- "INVENIO_SITE_UI_URL=https://127.0.0.1"
- "INVENIO_SITE_API_URL=https://127.0.0.1/api"
```

#### After:
```python
# Environment variables in docker-services.yml
- "INVENIO_SITE_UI_URL=http://127.0.0.1:5000"
- "INVENIO_SITE_API_URL=http://127.0.0.1:5000/api"
```

### 5. Port Exposure and Mapping

**Problem:** Docker Compose files didn't expose all necessary ports for local development.

**Solution:** Expose all required service ports with appropriate host mappings.

#### Before:
```yaml
# Original docker-compose.yml with minimal port exposure
services:
  db:
    extends:
      file: docker-services.yml
      service: db
  # No explicit port mapping
```

#### After:
```yaml
# Modified docker-compose.yml with explicit port mappings
services:
  db:
    extends:
      file: docker-services.yml
      service: db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### 6. Missing Dependencies

**Problem:** The application had missing dependencies when running locally.

**Solution:** Add required dependencies like `greenlet` to the Pipfile.

#### Before:
```
# Original Pipfile missing some dependencies
[packages]
# ... existing dependencies
```

#### After:
```
# Updated Pipfile with additional dependencies
[packages]
# ... existing dependencies
greenlet = ">=1.0.0"  # Required by SQLAlchemy with asyncio support
```

## Step-by-Step Project Modification Walkthrough

### Step 1: Examining the Original Configuration

First, we analyzed all configuration files to understand dependencies and service relationships:

1. **Dockerfile**: Contains build instructions and dependencies
2. **docker-services.yml**: Defines service configurations
3. **docker-compose.yml**: Orchestrates services together
4. **.invenio**: Contains project configuration
5. **invenio.cfg**: Application configuration settings

### Step 2: Identifying CERN-Specific Components

We identified all CERN-specific components that would need modification:

- Docker registry references
- XRootD dependencies
- Kerberos authentication
- HTTPS requirements
- Authentication providers

### Step 3: Creating Local Configuration Alternatives

For each identified component, we created local alternatives:

1. **Docker Images**: Replaced with public Docker Hub equivalents
2. **Authentication**: Simplified to use local authentication
3. **Protocol**: Changed from HTTPS to HTTP
4. **Dependencies**: Used Alpine-compatible packages

### Step 4: Updating Port Mappings

Ensured all services had proper port mappings for local access:

```yaml
services:
  cache:
    ports:
      - "6379:6379"
  db:
    ports:
      - "5432:5432"
  mq:
    ports:
      - "15672:15672"
      - "5672:5672"
  search:
    ports:
      - "9200:9200"
      - "9300:9300"
```

### Step 5: Creating Local Environment File

Added a `.env` file to set local paths:

```
INSTANCE_PATH=./data
```

### Step 6: Updating Documentation

Updated README.md and created detailed installation guides.

## Common Development Tasks

### Adding a New Dependency

When you need to add a new Python dependency:

```bash
# Add to Pipfile with pipenv
pipenv install package-name

# Update the lock file
pipenv lock

# Reinstall dependencies
invenio-cli install
```

### Modifying Configuration

To change application configuration:

1. Edit `local.cfg` with your changes
2. Restart the services:
   ```bash
   invenio-cli run
   ```

### Accessing Service Logs

To see logs for debugging:

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs -f db
```

### Accessing Database

Connect to PostgreSQL database:

```bash
docker-compose exec db psql -U zenodo -d zenodo
```

### Rebuilding After Changes

After modifying Docker-related files:

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

## Common Git and GitHub Issues

When working with this repository, you may encounter several Git and GitHub issues. Here are solutions to the most common problems:

### Branch Naming Issues

**Problem:** Git error "src refspec main does not match any" when trying to push.

**Cause:** This happens when you try to push to a branch (like `main`) that doesn't exist locally. The repository may be using `master` as the default branch name.

**Solution:**

1. Check your current branch:
   ```bash
   git branch
   ```

2. Either push to the correct branch name:
   ```bash
   # If your local branch is 'master'
   git push -u origin master
   ```

3. Or rename your branch to match the expected name:
   ```bash
   # Rename from 'master' to 'main'
   git branch -m master main
   git push -u origin main
   ```

### Large File Issues

**Problem:** HTTP 400 errors or "remote: error: File X is Y MB; this exceeds GitHub's file size limit of 100 MB" when pushing.

**Cause:** GitHub has a hard limit of 100MB per file and will reject pushes containing larger files.

**Solution:**

1. Identify large files:
   ```bash
   find . -type f -size +50M
   ```

2. Add these files to your `.gitignore`:
   ```bash
   echo "path/to/large/file" >> .gitignore
   ```

3. Remove them from Git tracking (if they're already tracked):
   ```bash
   git rm --cached path/to/large/file
   ```

4. Commit the change:
   ```bash
   git commit -m "Remove large files from tracking"
   ```

### Virtual Environment Issues

**Problem:** Repository size becomes too large when `.venv` directory is included.

**Cause:** Virtual environments contain compiled binaries and numerous dependencies that shouldn't be in Git.

**Solution:**

1. Always include `.venv/` in your `.gitignore`:
   ```bash
   echo ".venv/" >> .gitignore
   ```

2. If already committed, remove it from tracking:
   ```bash
   git rm -r --cached .venv/
   git commit -m "Remove virtual environment from Git tracking"
   ```

### HTTPS vs SSH Authentication

If you encounter authentication issues when pushing to GitHub:

```bash
# Change to SSH authentication (more reliable than HTTPS)
git remote set-url origin git@github.com:username/repository.git

# Verify the change
git remote -v
```

### Important Files to Exclude from Git

For Zenodo RDM specifically, these files/directories should never be committed:

```
# Virtual environments
.venv/
env/
venv/

# Generated files
__pycache__/
*.pyc
node_modules/

# User data
data/
instance/

# Generated assets
static/
app_data/static/
app_data/images/
app_data/files/
```

Ensure your `.gitignore` file contains these entries to prevent repository bloat and GitHub errors.

## Understanding the Dependency Stack

Zenodo RDM has a complex dependency stack:

```
┌───────────────────────────┐
│     Zenodo RDM            │
└───────────┬───────────────┘
            │
┌───────────▼───────────────┐
│     InvenioRDM             │
└───────────┬───────────────┘
            │
┌───────────▼───────────────┐
│     Invenio Framework      │
└───────────┬───────────────┘
            │
┌───────────▼───────────────┐
│     Flask                  │
└───────────────────────────┘
```

## Conclusion

By making these modifications, we've transformed a CERN-specific application into one that can be run locally on standard development environments. The main changes focused on:

1. Using publicly accessible Docker images
2. Simplifying authentication and security
3. Exposing services for local access
4. Adding missing dependencies
5. Creating documentation for local development

These modifications maintain the core functionality while making the application accessible to a wider audience of developers. 

I'll investigate the Mirador previewer functionality, focusing on tile generation, conversion, and manifest creation. Let me start by exploring the directories to understand the system structure.

Ran tool
Let me check the site directory, which is likely to contain the core functionality:

Ran tool
Let's look at the `zenodo_rdm` directory to find the Mirador previewer implementation:

Ran tool
I see two key directories that are likely related to Mirador:
1. `previewer/` - Probably contains the Mirador previewer implementation
2. `iiif/` - Likely handles the IIIF (International Image Interoperability Framework) functionality, which Mirador uses

Let's first check the previewer directory:

Ran tool
Now let's look at the IIIF directory:

Ran tool
Let's also check if there's any Mirador-related JavaScript in the assets directory:

Ran tool

Search files...
Let's look more into the IIIF functionality and how the tiles are generated:

Read file: site/zenodo_rdm/previewer/image_previewer.py
Let's look at the tile processor code:

Search files...
Let's search for the Mirador manifest generation code:

Search files...
Let's look for the TilesProcessor code to understand the tile generation process:

Search files...
Let's search for the IIIF URLs and canvas generation:

Search files...
Let's check for additional files related to TilesProcessor and IIIF implementation:

Ran tool
Let's look for some of the IIIF-related routes:

Search files...
Let's search for the actual asset loading for Mirador:

Search files...
Let's look for the JavaScript that initializes Mirador:

Ran tool
Let's check the main.js file to see how Mirador is initialized:

Read file: static/js/mirador3-dist/main.js
Let's look for the asset definitions to understand how the JavaScript is loaded for Mirador:

Search files...
Based on my investigation, let me provide a summary of how the Mirador previewer works in this system:

# Mirador Previewer in Zenodo RDM

## Overview
The Mirador previewer is used to display images and PDFs using the IIIF (International Image Interoperability Framework) protocol. It enables advanced viewing features like zooming, panning, and annotations for supported file types.

## Key Components

### 1. Tile Generation Process
- **TilesProcessor**: Processes images to create pyramid tiled IIIF-compatible image tiles (`.ptif` files)
- The processing is handled by `generate_iiif_tiles.py` script which:
  - Takes a record ID as input
  - Loads the record
  - Uses `TilesProcessor` to create tiles for each supported image file
  - Uses `ImageMetadataExtractor` to extract image dimensions for proper display
  - Tiles are stored in a dedicated volume (`image_tiles`)

### 2. Supported File Types
- Defined in `IIIF_TILES_VALID_EXTENSIONS` and `MIRADOR_PREVIEW_EXTENSIONS` in `invenio.cfg`:
  - `.jp2` (JPEG 2000)
  - `.jpeg`/`.jpg`
  - `.pdf`
  - `.png`
  - `.tif`/`.tiff`

### 3. Manifest Generation
- For each record with supported files, a IIIF manifest is created
- The manifest contains metadata about the images and their relationship
- Manifest is available at `/api/iiif/{uuid}/manifest`
- Canvas information for each image at `/api/iiif/{uuid}/canvas/{filename}`

### 4. Preview Flow (`image_previewer.py`)
The preview functionality follows these steps:
1. Check if the file is supported and tiles have been generated
2. If tile generation is complete (`tile_status == "finished"`):
   - Load the Mirador viewer with:
     - Canvas URL (`iiif_canvas_url`)
     - Manifest URL (`iiif_manifest_url`)
     - Configuration options (`mirador_cfg`)
     - Any annotations
3. If tiles are not ready or being processed:
   - Show a simple IIIF image preview using a direct URL
   - Display an appropriate message ("Zoom will be available shortly")
4. Handle special cases:
   - If image metadata is missing/invalid
   - If the file is too large
   - If the image dimensions are too small for tiling

### 5. Mirador JavaScript Library
- Mirador 3 is loaded from `/static/js/mirador3-dist/`
- Configuration options are passed from the backend to control viewer behavior
- Supports annotations with `.wadm` files

### 6. IIIF URL Structure and Routing
- NGINX is configured to route IIIF requests:
  - Manifest/canvas requests are routed to the API server
  - Image tile requests are routed to the IIPServer (specialized image server)
- URL pattern examples:
  - `/api/iiif/record:{id}/manifest` - For manifest
  - `/api/iiif/record:{id}:{filename}/info.json` - For image info
  - `/api/iiif/record:{id}:{filename}/{region}/{size}/{rotation}/{quality}.{format}` - For image tiles

### 7. Infrastructure Components
- **IIPServer**: Handles IIIF image requests (runs in a Docker container)
- **API Server**: Generates manifests and handles metadata
- **Shared volumes**: For storing and accessing image tiles

The system supports fallback options for files in different states, including:
- Draft files (show a message that zoom is not available)
- Processing files (show a message that zoom will be available shortly)
- Failed processing (fallback to simple preview)

This architecture enables high-performance image viewing with advanced features while managing the complexity of large image files.

## Mirador IIIF Image Previewer

This section explains the Mirador IIIF image previewer system, its components, and provides a detailed testing procedure.

### Understanding Mirador Previewer Architecture

Zenodo RDM includes a sophisticated image viewing system based on the [IIIF (International Image Interoperability Framework)](https://iiif.io/) standard and the [Mirador viewer](https://projectmirador.org/). This system enables high-quality zooming, panning, and annotation of image files.

#### System Components:

1. **TilesProcessor**: Processes images to create pyramid-tiled IIIF-compatible image tiles (`.ptif` files)
2. **IIPServer**: A specialized image server that delivers IIIF-compatible image tiles
3. **IIIF API**: Generates manifests and canvas information for IIIF viewing
4. **Mirador Viewer**: A JavaScript library that consumes IIIF endpoints to display images

#### File Processing Flow:

```
File Upload → Metadata Extraction → Tile Generation → Manifest Creation → Serving via IIIF → Display in Mirador
```

#### Supported File Types:
- JPG/JPEG
- PNG
- TIFF/TIF
- JP2 (JPEG 2000)
- PDF

### Configuration

Key configuration parameters are defined in `invenio.cfg`:

```python
IIIF_TILES_VALID_EXTENSIONS = [
    "jp2", "jpeg", "jpg", "pdf", "png", "tif", "tiff",
]

IIIF_TILES_GENERATION_ENABLED = True

IIIF_TILES_STORAGE_BASE_PATH = "images/"  # relative to the instance path

MIRADOR_PREVIEW_EXTENSIONS = [
    "pdf", "png", "jp2", "jpeg", "jpg", "png", "tif", "tiff",
]

# Mirador viewer configuration
MIRADOR_PREVIEW_CONFIG = {
    "window": {
        "allowClose": False,
        "allowFullscreen": True,
        # ... additional config options
    },
    # ... more settings
}
```

### IIIF URL Structure

The system uses the following URL patterns:

1. **Manifest URL**: `/api/iiif/{uuid}/manifest`
2. **Canvas URL**: `/api/iiif/{uuid}/canvas/{filename}`
3. **Image Tile URL**: `/api/iiif/record:{id}:{filename}/{region}/{size}/{rotation}/{quality}.{format}`

### Testing the Mirador Previewer

Follow these steps to thoroughly test the Mirador previewer functionality:

#### Phase 1: Environment Setup and Component Verification

1. **Verify Docker Services**
   ```bash
   # Check that all required services are running
   docker-compose ps
   
   # Make sure the IIPServer container is running
   docker-compose logs iipserver
   ```

2. **Verify Storage Volumes**
   ```bash
   # Check the mounted volumes for image tiles
   docker-compose exec worker ls -la /opt/invenio/var/instance/images/
   ```

#### Phase 2: File Upload and Processing Testing

1. **Upload Test Files**
   - Upload various image files (JPG, PNG, TIFF) of different sizes through the web UI
   - Upload PDF files that should be previewable
   - Record the IDs of the uploaded files for later testing

2. **Monitor Tile Generation Process**
   ```bash
   # Check the worker logs to see tile generation in progress
   docker-compose logs -f worker
   
   # You should see messages about TilesProcessor being called
   ```

3. **Verify Tile Generation**
   ```bash
   # Check if PTIF files were created for your uploaded images
   docker-compose exec worker ls -la /opt/invenio/var/instance/images/
   ```

#### Phase 3: IIIF API Testing

1. **Test Manifest Generation**
   ```bash
   # Replace {record_id} with the ID of a record containing images
   curl -H "Accept: application/json" http://localhost:5001/api/iiif/record:{record_id}/manifest
   ```

   This should return a JSON IIIF manifest with canvas information.

2. **Test Image Info Endpoint**
   ```bash
   # Replace {record_id} and {filename} with appropriate values
   curl -H "Accept: application/json" http://localhost:5001/api/iiif/record:{record_id}:{filename}/info.json
   ```

   This should return tile information including sizes, formats, and available scaling options.

3. **Test Direct Image Requests**
   ```bash
   # Get a full-size image
   curl -o test_full.jpg http://localhost:5001/api/iiif/record:{record_id}:{filename}/full/full/0/default.jpg
   
   # Get a thumbnail
   curl -o test_thumb.jpg http://localhost:5001/api/iiif/record:{record_id}:{filename}/full/200,/0/default.jpg
   
   # Get a specific region
   curl -o test_region.jpg http://localhost:5001/api/iiif/record:{record_id}:{filename}/100,100,500,500/full/0/default.jpg
   ```

#### Phase 4: Browser-based Mirador Testing

1. **Test Basic Viewer Loading**
   - Open a record with processed image files in the browser
   - Click on an image to open the previewer
   - Verify that the Mirador viewer loads correctly
   - Test zoom in/out, panning, and rotation features

2. **Test Status Messages**
   - Upload a new image and immediately try to preview it
   - You should see a message that "Zoom will be available shortly"
   - Once processing is complete, refresh and verify that the full viewer loads

3. **Test Annotations (if available)**
   - If you have `.wadm` annotation files, upload them alongside the images
   - Check if the annotation panel appears in the Mirador viewer
   - Test creating and viewing annotations

#### Phase 5: Testing Edge Cases

1. **Test Very Large Images**
   - Upload images larger than the configured `PREVIEWER_MAX_IMAGE_SIZE_BYTES` (15MB by default)
   - Check if appropriate fallback behavior is triggered

2. **Test Metadata Extraction**
   - Upload images with various metadata (EXIF, etc.)
   - Check if dimensions and other metadata are correctly extracted

3. **Test Error Handling**
   - Upload a corrupt image file
   - Check how the system handles the error
   - Verify that appropriate error messages are displayed

### Debugging Common Issues

1. **Images Not Processing**
   - Check worker logs for errors
   - Verify that the `IIIF_TILES_GENERATION_ENABLED` setting is `True`
   - Ensure the file extension is in `IIIF_TILES_VALID_EXTENSIONS`

2. **Mirador Viewer Not Loading**
   - Inspect browser console for JavaScript errors
   - Check if the Mirador JavaScript files are being correctly loaded
   - Verify that IIIF endpoints are accessible

3. **IIIF URLs Not Working**
   - Check NGINX configuration for the IIIF route patterns
   - Verify that the IIPServer is running and accessible
   - Check if the PTIFs were generated correctly

### Advanced Implementation and Practical Testing Guide

This section provides practical guidance for implementing and thoroughly testing the Mirador IIIF image previewer system.

#### IIIF Server Configuration

For effective tile serving, the IIPServer must be properly configured:

1. **Performance Tuning**
   ```bash
   # In docker-services.yml for the IIPServer container
   environment:
     - "CORS=*"  # Allow cross-origin requests
     - "VERBOSITY=6"  # Debug level (1-6)
     - "LOGFILE=/tmp/iipserver.log"
     - "MAX_IMAGE_CACHE_SIZE=10"  # Cache size in GB
     - "MAX_CVT=30000"  # Max image dimension for dynamic conversion
     - "FILESYSTEM_PREFIX=/images/"  # Base path for image files
   ```

2. **Monitoring IIPServer Health**
   ```bash
   # Check IIPServer logs for performance issues
   docker-compose exec iipserver cat /tmp/iipserver.log
   
   # Check resource usage
   docker stats iipserver
   ```

#### Deep Dive into PTIF File Inspection

Pyramid TIFF (PTIF) files store multiple resolutions of the same image in a hierarchical structure:

```bash
# Install TIFF tools
apt-get install libtiff-tools

# Examine a PTIF file structure
docker-compose exec worker tiffinfo /opt/invenio/var/instance/images/12/34/5_/filename.ptif

# Extract a specific resolution level
docker-compose exec worker tiffcrop -z 1:2 /path/to/file.ptif -o /tmp/extract.tif
```

#### Manifest Inspection and Validation

1. **Using IIIF Validators**
   
   Install the IIIF Validator to check manifest conformance:
   ```bash
   pip install iiif-validator
   
   # Save a manifest for testing
   curl -H "Accept: application/json" \
     http://localhost:5001/api/iiif/record:{record_id}/manifest > manifest.json
   
   # Validate the manifest
   iiif-validator.py --version=2.0 manifest.json
   ```

2. **Understanding Manifest Structure**

   Key components to check in a manifest:
   - `@context`: Should be "http://iiif.io/api/presentation/2/context.json"
   - `@id`: Should match your manifest URL
   - `@type`: Should be "sc:Manifest"
   - `sequences`: Contains the list of canvases
   - Each canvas should have width, height, and image URL

#### End-to-End Testing with Automation

Create a test script for validating the full IIIF workflow:

```python
#!/usr/bin/env python3
"""Test script for validating IIIF functionality."""
import requests
import os
import json
import time
from PIL import Image
import io

# Configuration
BASE_URL = "http://localhost:5001"
RECORD_ID = "your_record_id"  # Replace with a real record ID
IMAGE_FILENAME = "your_image.jpg"  # Replace with a real image filename

# Test 1: Manifest availability
manifest_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}/manifest"
response = requests.get(manifest_url, headers={"Accept": "application/json"})
assert response.status_code == 200, f"Manifest not available: {response.status_code}"
manifest = response.json()

# Test 2: Canvas structure
canvas_found = False
for sequence in manifest.get("sequences", []):
    for canvas in sequence.get("canvases", []):
        if IMAGE_FILENAME in canvas.get("@id", ""):
            canvas_found = True
            print(f"Canvas found for {IMAGE_FILENAME}")
            assert "width" in canvas, "Canvas missing width"
            assert "height" in canvas, "Canvas missing height"
            break
    if canvas_found:
        break
assert canvas_found, f"Canvas not found for {IMAGE_FILENAME}"

# Test 3: Image tile access
info_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}:{IMAGE_FILENAME}/info.json"
response = requests.get(info_url, headers={"Accept": "application/json"})
assert response.status_code == 200, f"Image info not available: {response.status_code}"
info = response.json()

# Test 4: Tile retrieval
tile_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}:{IMAGE_FILENAME}/full/200,/0/default.jpg"
response = requests.get(tile_url)
assert response.status_code == 200, f"Image tile not available: {response.status_code}"

# Verify we got an actual image
img = Image.open(io.BytesIO(response.content))
assert img.width <= 200, f"Image width exceeds requested size: {img.width}"
print(f"Successfully retrieved image tile: {img.width}x{img.height}")

print("All tests passed!")
```

Save this as `test_iiif.py` and run it with:
```bash
python test_iiif.py
```

#### Measuring Tile Generation Performance

To optimize tile generation, measure the processing time for different file types:

```bash
# Create a test script
cat > test_tile_performance.sh << 'EOF'
#!/bin/bash
echo "Testing IIIF tile generation performance"

# Function to time tile generation
test_file() {
  local file_id=$1
  local start_time=$(date +%s)
  echo "Processing $file_id..."
  
  # Use the generate_iiif_tiles.py script
  docker-compose exec -T worker python scripts/generate_iiif_tiles.py "$file_id"
  
  local end_time=$(date +%s)
  local duration=$((end_time - start_time))
  echo "Processing time for $file_id: $duration seconds"
}

# Test with different file IDs
test_file "record_id_with_jpg"
test_file "record_id_with_tiff"
test_file "record_id_with_pdf"

echo "Performance testing complete"
EOF

chmod +x test_tile_performance.sh
./test_tile_performance.sh
```

#### Troubleshooting Common Errors

1. **Missing PTIF Files**

   Cause: Tile generation failed or wasn't triggered.
   
   Solution:
   ```bash
   # Check if TilesProcessor is enabled
   grep IIIF_TILES_GENERATION_ENABLED invenio.cfg
   
   # Manually trigger tile generation for a record
   docker-compose exec worker python -c "
   from invenio_rdm_records.proxies import current_rdm_records_service
   from invenio_rdm_records.records.processors.tiles import TilesProcessor
   from invenio_records_resources.services.uow import UnitOfWork, RecordCommitOp
   
   record = current_rdm_records_service.record_cls.pid.resolve('your_record_id')
   with UnitOfWork() as uow:
       processor = TilesProcessor()
       processor(None, record, uow=uow)
       uow.register(RecordCommitOp(record))
       uow.commit()
   print('Tile generation triggered')
   "
   ```

2. **CORS Issues**

   If you're seeing CORS errors in the browser console:
   
   ```bash
   # Ensure IIPServer has proper CORS headers
   docker-compose restart iipserver
   
   # Check if NGINX is correctly forwarding CORS headers
   grep -r "add_header 'Access-Control-Allow-Origin'" docker/nginx/
   ```

3. **JavaScript Errors in Mirador**

   Check browser console for errors. Common issues:
   
   - Manifest not properly formatted (check against IIIF specification)
   - Canvas URLs incorrect (check URL routing in NGINX)
   - JavaScript files not loading (check network tab in browser developer tools)

#### Security Considerations

When deploying Mirador and IIIF in production:

1. **Access Control**
   - Implement proper authentication for private files
   - Add authorization checks in the IIIF endpoints

2. **Resource Limits**
   - Set maximum image dimensions to prevent DoS attacks
   - Implement rate limiting for IIIF endpoints

3. **Cache Headers**
   - Configure appropriate cache headers for tiles
   - Example NGINX configuration:
     ```
     location ~ /api/iiif/record:.+:.+/full/.+/.+/.+\..+ {
       # Long cache for static tiles
       add_header Cache-Control "public, max-age=31536000, immutable";
     }
     ```

By following this comprehensive testing and implementation guide, you can ensure that your Mirador IIIF previewer system is robust, performant, and correctly configured for your specific needs.

## IIPServer Testing Guide: Understanding the Core of IIIF Image Serving

This section provides an in-depth, step-by-step guide for understanding and testing the IIPServer component, which is the foundation of the Mirador IIIF image previewer system. By following this guide, you'll gain a clear understanding of how the IIPServer works and how to validate its functionality.

### What is IIPServer and Why Is It Important?

The IIPServer is a specialized image server designed specifically for serving high-resolution images using the IIIF (International Image Interoperability Framework) protocol. It's particularly important because:

- It handles the delivery of image tiles at different resolutions
- It can serve specific regions of images at different sizes and rotations
- It works with special Pyramid TIFF (PTIF) files that store multiple resolutions
- It provides the foundation for advanced image viewers like Mirador

In a nutshell, IIPServer is what allows users to smoothly zoom in and out of high-resolution images without loading the entire image at once.

### Understanding the Architecture with a Visual Map

```
┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
│                 │  Upload   │                 │ Processes │                 │
│  Web Browser    │─────────►│  Web Application │─────────►│ TilesProcessor  │
│  (User)         │           │  (Flask/Invenio)│           │                 │
└─────────────────┘           └─────────────────┘           └─────────────────┘
        │                              ▲                            │
        │                              │                            │
        │                              │                            ▼
        │                              │                    ┌─────────────────┐
        │                              │                    │                 │
        │      IIIF Image Request      │                    │  Pyramid TIFF   │
        └─────────────────────────────►│                    │  (.ptif) Files  │
                                       │                    │                 │
                                       │                    └─────────────────┘
                                       │                            ▲
                                       │                            │
                                 ┌─────────────────┐                │
                                 │                 │                │
                                 │    IIPServer    │────────────────┘
                                 │                 │    Reads Files
                                 └─────────────────┘
```

### Testing the IIPServer: Step by Step

The following guide will help you test just the IIPServer component to ensure it's properly configured, without requiring the full application stack.

#### Step 1: Verify IIPServer is Running

First, check if the IIPServer container is running:

```bash
docker-compose ps | grep iipserver
```

Example output:
```
zenodo-rdm-master-iipserver-1 iipsrv/iipsrv:latest "/bin/sh -c run" iipserver 18 minutes ago Up 18 minutes 8080/tcp, 0.0.0.0:9000->9000/tcp, 0.0.0.0:8080->80/tcp
```

This confirms that the IIPServer is running on ports 8080 and 9000.

#### Step 2: Check IIPServer Configuration

Inspect the IIPServer's environment variables to understand its configuration:

```bash
docker-compose exec iipserver env | grep -E "FILESYSTEM_PREFIX|CORS|VERBOSITY"
```

Example output:
```
FILESYSTEM_PREFIX=/images/public
CORS=*
VERBOSITY=5
```

This tells us:
- The server is looking for images in the `/images/public` directory
- CORS is enabled with `*` (allows requests from any origin)
- The verbosity level is set to 5 (for detailed logging)

#### Step 3: Understand Volume Mapping

View the Docker volume configuration to understand how the image files are mapped:

```bash
docker-compose config | grep -A5 "iipserver"
```

Example output showing volumes:
```
volumes:
  - type: bind
    source: /Users/username/Projects/zenodo-rdm-master/data/images
    target: /images
    bind:
      create_host_path: true
```

This means:
- Files in your local `./data/images` directory should be available inside the container at `/images`
- The IIPServer is configured to look in `/images/public` (a subdirectory of `/images`)

#### Step 4: Create a Test Directory Structure

The IIIF system uses a specific directory structure based on record IDs. Create a corresponding test directory:

```bash
mkdir -p ./data/images/public/10/0_/_
```

This creates a directory structure that mimics how the application would store image tiles for record ID "10".

#### Step 5: Create a Test Image

Generate a simple test image using ImageMagick:

```bash
convert -size 1000x1000 xc:white -fill blue \
  -draw "circle 500,500 500,400" \
  ./data/images/test_image.png
```

This creates a 1000×1000 pixel white image with a blue circle.

#### Step 6: Check Local Directory Structure

Verify that your test directories and image exist:

```bash
ls -la ./data/images/
ls -la ./data/images/public/10/0_/_
```

#### Step 7: Verify Image Accessibility in Container

Check if the IIPServer container can access your test image:

```bash
# First, try to find the image in the container
docker-compose exec iipserver find /images -name "test_image.png"
```

If no result is returned, there may be an issue with the volume mapping. In this case, you can copy the file directly into the container:

```bash
docker cp ./data/images/test_image.png zenodo-rdm-master-iipserver-1:/images/public/
```

#### Step 8: Test IIIF Endpoint Access

Try accessing the image via the IIIF protocol:

```bash
curl -I http://localhost:8080/iip?IIIF=/public/test_image.png/info.json
```

### Common Challenges and Solutions

Based on our testing, here are the main challenges you might encounter and how to address them:

#### 1. Volume Mapping Issues

**Problem**: Files created in the host directory don't appear in the container.

**Cause**: This can happen due to Docker volume caching, permission issues, or differing directory structures between container and host.

**Solution**:
- Restart the container after creating new files:
  ```bash
  docker-compose restart iipserver
  ```
- Copy files directly into the container:
  ```bash
  docker cp ./local/file.png container_name:/container/path/
  ```

#### 2. PTIF File Format Requirements

**Problem**: The IIPServer only works with specialized Pyramid TIFF (PTIF) files, not regular images.

**Cause**: PTIF files contain multiple resolutions of the same image in a hierarchical structure, which standard image formats don't provide.

**Solution**:
- Let the application's TilesProcessor handle the conversion
- For testing purposes, you can use the VIPS tool to create PTIF files:
  ```bash
  vips tiffsave input.jpg output.ptif --tile --pyramid --compression=none
  ```

#### 3. Directory Structure Complexity

**Problem**: The directory structure for IIIF images is complex and difficult to reproduce manually.

**Cause**: The system splits record IDs into parts to create a directory hierarchy, making manual creation error-prone.

**Solution**:
- Use the application's tools to generate the proper structure
- For testing, focus on the IIPServer's ability to access and serve files from its configured directories

#### 4. 404 Errors from IIPServer

**Problem**: IIPServer returns 404 Not Found errors when trying to access images.

**Cause**: This usually happens when:
- The image file doesn't exist
- The file isn't in the correct PTIF format
- The path is incorrect

**Solution**:
- Verify the file exists in the container with `docker-compose exec iipserver ls -la /path/to/file`
- Check that you're using the correct path in your IIIF URL
- Ensure the file is in a format the IIPServer can read (usually PTIF)

### Command Reference Guide

Here's a quick reference of the most useful commands for testing the IIPServer:

| Command | Purpose |
|---------|---------|
| `docker-compose ps \| grep iipserver` | Check if IIPServer is running |
| `docker-compose exec iipserver env` | View IIPServer environment variables |
| `docker-compose exec iipserver ls -la /images` | List files in the images directory |
| `docker-compose restart iipserver` | Restart the IIPServer container |
| `docker cp ./local/file.png container_name:/container/path/` | Copy a file directly into the container |
| `curl -I http://localhost:8080/iip?IIIF=/path/to/image.ptif/info.json` | Test an IIIF endpoint |
| `docker-compose logs iipserver` | View IIPServer logs |

### Understanding IIIF URL Structure

The IIIF Image API uses a specific URL structure:

```
http://server/iip?IIIF=/path/to/image.ptif/{region}/{size}/{rotation}/{quality}.{format}
```

Where:
- **region**: Part of the image to return (e.g., `full` or `x,y,width,height`)
- **size**: Dimensions of the returned image (e.g., `full`, `200,`, `^1000,`)
- **rotation**: Rotation in degrees (e.g., `0`, `90`, `180`)
- **quality**: Image quality (e.g., `default`, `color`, `gray`)
- **format**: Image format (e.g., `jpg`, `png`)

Example for a thumbnail:
```
http://localhost:8080/iip?IIIF=/public/example.ptif/full/200,/0/default.jpg
```

### When to Move Beyond IIPServer Testing

Testing just the IIPServer is valuable, but has limitations:

1. It's difficult to manually create valid PTIF files
2. The directory structure is complex and automatically generated
3. The IIIF manifests are created by the application

When you need to test the complete image viewing experience, including:
- Tile generation
- Manifest creation
- Mirador viewer functionality

You should use the full application stack:
```bash
docker-compose -f docker-compose.full.yml up -d
```

This will start all required services including the web application which handles file uploads, processing, and the actual Mirador viewer interface.

### Visual Debugging Guide

When troubleshooting IIPServer issues, check these components in order:

1. **Container Status**: Is the IIPServer container running?
2. **Volume Mapping**: Can the container see the files?
3. **File Format**: Are your files in the PTIF format?
4. **URL Structure**: Are your IIIF URLs correctly formatted?
5. **Error Messages**: What do the IIPServer logs show?

```
┌─────────────────┐
│  Check Container│
│     Status      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Check Volume    │
│    Mapping      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Verify File     │
│    Format       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Test IIIF URL   │
│    Structure    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Examine Error   │
│    Messages     │
└─────────────────┘
```

By following this testing guide, you'll gain a clear understanding of the IIPServer component, which is a critical piece of the Mirador IIIF image previewer system. This knowledge will help you debug issues and implement image viewing capabilities in your Zenodo RDM application.

## Developer Guide: IIIF PDF Support Implementation

## Introduction
This guide provides detailed technical information for developers working on the IIIF PDF support implementation in Zenodo RDM.

## Architecture Deep Dive

### 1. Cantaloupe Proxy Implementation
The `CantaloupeProxy` class in `proxy.py` extends the base `IIIFProxy` class to handle PDF files:

```python
class CantaloupeProxy(IIIFProxy):
    def __init__(self, server_url=None, base_path=None):
        self.server_url = server_url or current_app.config.get('IIIF_SERVER_URL')
        self.base_path = base_path or current_app.config.get('IIIF_BASE_PATH')
```

### 2. PDF Detection and Handling
The proxy implements PDF detection and special handling:

```python
def is_pdf(self, file_path):
    """Check if file is a PDF."""
    return file_path.lower().endswith('.pdf')

def get_pdf_info(self, record_id, filename):
    """Get PDF info from Cantaloupe."""
    file_path = self.get_file_path(record_id, filename)
    if not self.is_pdf(file_path):
        return None
    # Implementation details...
```

### 3. IIIF Manifest Generation
The manifest generation process involves several components:

```python
class ZenodoIIIFManifestV2Schema(Schema):
    """Schema for IIIF manifest with Zenodo-specific fields."""
    # Schema definition...

class ZenodoIIIFManifestV2JSONSerializer(Serializer):
    """Serializer for IIIF manifest."""
    # Serializer implementation...
```

## Implementation Challenges and Solutions

### 1. PDF Page Extraction
**Challenge**: Extracting individual pages from PDFs for IIIF viewing
**Solution**: Using Cantaloupe's PDF processor with proper configuration

```python
# Cantaloupe configuration
PDF_PROCESSOR = {
    'processor': 'PdfBoxProcessor',
    'processor_options': {
        'max_memory_bytes': '512m',
        'max_threads': '4'
    }
}
```

### 2. File Upload and Processing
**Challenge**: Ensuring files are fully processed before IIIF access
**Solution**: Implement file commit and verification steps

```python
# File upload process
1. Create file entry
2. Upload content
3. Commit file
4. Wait for processing
5. Verify completion
```

### 3. Metadata Validation
**Challenge**: Ensuring required metadata for IIIF manifests
**Solution**: Implement validation in schema

```python
class IIIFMetadataSchema(Schema):
    """Schema for IIIF metadata validation."""
    title = fields.Str(required=True)
    creator = fields.Str(required=True)
    # Additional fields...
```

## Code Examples

### 1. Creating a Record with PDF
```python
# Example using the upload_pdf.py script
python upload_pdf.py new path/to/file.pdf
```

### 2. Testing IIIF Endpoints
```python
# Example using check_iiif.py
python check_iiif.py <record_id>
```

### 3. Custom IIIF Implementation
```python
# Example of custom IIIF resource
class CustomIIIFResource(IIIFResource):
    def get_manifest(self, record_id):
        # Custom manifest generation
        pass
```

## Testing Strategy

### 1. Unit Tests
```python
def test_pdf_detection():
    proxy = CantaloupeProxy()
    assert proxy.is_pdf('test.pdf') == True
    assert proxy.is_pdf('test.jpg') == False

def test_manifest_generation():
    # Test manifest generation
    pass
```

### 2. Integration Tests
```python
def test_pdf_upload_and_iiif():
    # Test complete workflow
    pass
```

## Performance Considerations

### 1. Caching
```python
# Example caching implementation
@cache.memoize(timeout=3600)
def get_pdf_info(record_id, filename):
    # Implementation
    pass
```

### 2. Batch Processing
```python
# Example batch processing
def process_multiple_pdfs(pdf_files):
    # Implementation
    pass
```

## Security Considerations

### 1. Authentication
```python
# Example authentication check
def check_auth():
    if not current_user.is_authenticated:
        raise Unauthorized()
```

### 2. File Access Control
```python
# Example access control
def check_file_access(record_id, filename):
    # Implementation
    pass
```

## Monitoring and Logging

### 1. Error Logging
```python
# Example error logging
try:
    # Operation
except Exception as e:
    current_app.logger.error(f"Error processing PDF: {str(e)}")
```

### 2. Performance Monitoring
```python
# Example performance monitoring
@monitor.time()
def process_pdf(file_path):
    # Implementation
    pass
```

## Deployment Considerations

### 1. Configuration
```python
# Example configuration
IIIF_CONFIG = {
    'server_url': 'http://localhost:8182',
    'base_path': '/iiif',
    'cache_timeout': 3600
}
```

### 2. Scaling
- Use load balancing for Cantaloupe servers
- Implement caching for frequently accessed PDFs
- Consider CDN integration for static content

## Troubleshooting Guide

### 1. Common Issues
- PDF not rendering
- Slow performance
- Authentication errors

### 2. Debugging Tools
```python
# Example debugging code
def debug_pdf_processing(file_path):
    # Implementation
    pass
```

## Future Development

### 1. Planned Features
- Support for more document formats
- Enhanced caching
- Improved error handling

### 2. Performance Improvements
- Parallel processing
- Optimized caching
- CDN integration

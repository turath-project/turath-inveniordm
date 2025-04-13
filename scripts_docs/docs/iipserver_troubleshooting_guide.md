# IIPServer Troubleshooting Guide

This guide documents the process of diagnosing and troubleshooting issues with the IIPServer component of the IIIF implementation in Zenodo-RDM.

## Overview

IIPServer is a critical component in the IIIF workflow, responsible for serving image files in a format compatible with IIIF viewers like Mirador. When this component isn't functioning correctly, the entire IIIF viewing experience fails.

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│               │     │               │     │               │
│  User uploads │────>│ Worker converts│────>│ IIPServer     │
│  image files  │     │ to PTIF format│     │ serves images │
│               │     │               │     │               │
└───────────────┘     └───────────────┘     └───────────────┘
                                                   │
                                                   ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│               │     │               │     │               │
│  User views   │<────│ Mirador loads │<────│ IIIF Manifest │
│  in browser   │     │ manifest      │     │ references    │
│               │     │               │     │ IIPServer URLs│
└───────────────┘     └───────────────┘     └───────────────┘
```

## Common Problems & Solutions

### Problem 1: 500 Internal Server Error from IIPServer

**Symptoms:**
- Requests to IIPServer return 500 Internal Server Error
- Server logs show C++ assertion failures
- IIPServer container crashes

**Solution:**
1. Restart the IIPServer container:
   ```bash
   docker-compose restart iipserver
   ```
2. Check if the container is running:
   ```bash
   docker-compose ps | grep iipserver
   ```

### Problem 2: "File not found" or 404 Errors

**Symptoms:**
- Requests to IIPServer return 404 Not Found
- Error messages like "/images/public/file.ptif is neither a file nor part of an image sequence"

**Solution:**
1. Check if the image directories exist:
   ```bash
   docker-compose exec iipserver ls -la /images/
   docker-compose exec iipserver ls -la /images/public/
   ```
2. Create the required directories if they don't exist:
   ```bash
   docker-compose exec iipserver mkdir -p /images/public
   ```
3. Add test images to verify functionality:
   ```bash
   docker-compose cp test_image.png iipserver:/tmp/
   docker-compose exec iipserver cp /tmp/test_image.png /images/public/
   ```

### Problem 3: Volume Mounting Issues

**Symptoms:**
- Images exist on your host machine but aren't visible inside the container
- Volume directories appear empty inside the container

**Solution:**
1. Check the volume configuration in docker-compose.yml:
   ```yaml
   volumes:
     - ${INSTANCE_PATH:-./data}/images:/images
   ```
2. Verify that the local directory exists:
   ```bash
   ls -la data/images/
   ```
3. Manually copy files if needed:
   ```bash
   docker-compose cp data/images/test_image.png iipserver:/images/public/
   ```

### Problem 4: PTIF Conversion Missing

**Symptoms:**
- Regular images work but IIIF functionality fails
- No PTIF files found in the image directories

**Solution:**
1. Check if a worker service is configured for conversion:
   ```bash
   docker-compose ps | grep worker
   ```
2. Verify that conversion tools are installed in the appropriate container:
   ```bash
   docker-compose exec iipserver which vips
   ```
3. Set up a worker service or install conversion tools in the IIPServer container

## Step-by-Step Troubleshooting Process

### 1. Verify IIPServer is Running

```bash
# Check if the container is running
docker-compose ps | grep iipserver

# Expected output should show the container is "Up" and running
```

### 2. Check IIPServer Logs

```bash
# View the last 30 lines of logs
docker-compose logs iipserver | tail -n 30

# Look for errors like:
# - Assertion failures
# - File not found errors
# - Permission issues
```

### 3. Test Direct Access to IIPServer

```bash
# Test basic IIPServer connectivity
curl "http://localhost:8080/fcgi-bin/iipsrv.fcgi"

# Expected response: HTML content with IIPServer information
```

### 4. Check Image Directory Structure

```bash
# Check the root images directory
docker-compose exec iipserver ls -la /images/

# Check public directory
docker-compose exec iipserver ls -la /images/public/

# Check environment variables
docker-compose exec iipserver env | grep FILESYSTEM
```

### 5. Test with a Simple Image

```bash
# Copy a test image to the container
docker-compose cp test_image.png iipserver:/tmp/

# Create public directory if it doesn't exist
docker-compose exec iipserver mkdir -p /images/public

# Copy image to the public directory
docker-compose exec iipserver cp /tmp/test_image.png /images/public/

# Test direct access to the image
curl "http://localhost:8080/fcgi-bin/iipsrv.fcgi?FIF=/test_image.png&OBJ=Basic-Info"
```

### 6. Write and Run a Test Script

Create a Python script to test IIPServer functionality:

```python
#!/usr/bin/env python3
"""
Test script for IIPServer functionality.
"""

import requests

# Configuration
IIPSERVER_URL = "http://localhost:8080/fcgi-bin/iipsrv.fcgi"
TEST_IMAGE = "test_image.png"

# Test direct IIP access
direct_url = f"{IIPSERVER_URL}?FIF=/{TEST_IMAGE}"
print(f"Testing: {direct_url}")
response = requests.get(direct_url, timeout=10)
print(f"Status code: {response.status_code}")
print(f"Content type: {response.headers.get('Content-Type', 'unknown')}")

# Test image info
info_url = f"{IIPSERVER_URL}?FIF=/{TEST_IMAGE}&OBJ=Basic-Info"
print(f"\nTesting: {info_url}")
info_response = requests.get(info_url, timeout=10)
print(f"Status code: {info_response.status_code}")
print(f"Response: {info_response.text}")
```

Run the script with:
```bash
cd site
python tests/iiif/test_direct.py
```

## Common Error Messages Explained

### 1. "is neither a file nor part of an image sequence"

```
/images/public/test_image.ptif is neither a file nor part of an image sequence
```

**Meaning:** The file doesn't exist in the specified location, or the IIPServer can't read it.

**Checks:**
- Verify file existence: `docker-compose exec iipserver ls -la /images/public/`
- Check permissions: Files should be readable by the IIPServer user
- Ensure directory structure matches the `FILESYSTEM_PREFIX` environment variable

### 2. C++ Assertion Failures

```
terminate called after throwing an instance of 'std::out_of_range'
  what():  vector::_M_range_check: __n (which is 18446744073709551615) >= this->size() (which is 0)
```

**Meaning:** The IIPServer is trying to access image data in an invalid way, often due to corrupted or incompatible image formats.

**Checks:**
- Restart the IIPServer: `docker-compose restart iipserver`
- Try with a different image format
- Check that the image is not corrupted

### 3. "500 Internal Server Error"

```
HTTP/1.1 500 Internal Server Error
```

**Meaning:** The IIPServer encountered an unrecoverable error while processing the request.

**Checks:**
- Check the IIPServer logs: `docker-compose logs iipserver`
- Verify the server is still running: `docker-compose ps | grep iipserver`
- Restart the server if it crashed: `docker-compose restart iipserver`

## Checklist for Full IIIF Functionality

To achieve full IIIF functionality with IIPServer, ensure:

1. ✅ IIPServer container is running
2. ✅ Volume mounting is configured correctly
3. ✅ Image directories exist and have proper permissions
4. ✅ Test images are accessible via direct IIP protocol
5. ❌ PTIF conversion tools are installed
6. ❌ Worker service is configured for image processing
7. ❌ Record-specific directories are created for private images

## How to Use IIPImage Protocol Commands

IIPServer supports several protocol commands for accessing and manipulating images:

### Basic Image Access
```
http://localhost:8080/fcgi-bin/iipsrv.fcgi?FIF=/path/to/image.tif
```

### Get Image Information
```
http://localhost:8080/fcgi-bin/iipsrv.fcgi?FIF=/path/to/image.tif&OBJ=Basic-Info
```

### Get a Region of the Image
```
http://localhost:8080/fcgi-bin/iipsrv.fcgi?FIF=/path/to/image.tif&RGN=0,0,100,100&CVT=jpeg
```

### IIIF Image API 2.0 Format
```
http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/path/to/image.tif/full/full/0/default.jpg
```

### IIIF Info.json
```
http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/path/to/image.tif/info.json
```

## Conclusion

Diagnosing IIPServer issues is a critical step in ensuring the IIIF functionality works in Zenodo-RDM. By following this guide, you can identify and resolve common problems with the image serving component of the IIIF workflow.

Remember that IIPServer is just one part of the complete IIIF implementation. For full functionality, you'll also need to configure:
- PTIF conversion tools
- Worker services for asynchronous processing
- Manifest generation that properly references IIPServer URLs

## Related Documentation

- [IIIF Status Report](iiif_status_report.md)
- [IIIF Manual Testing Guide](iiif_manual_testing.md)
- [Image Conversion Process](image_conversion_process.md) 
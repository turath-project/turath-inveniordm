# Testing IIPServer: A Hands-On Guide to IIIF Image Serving

This document provides a thorough, step-by-step guide to understanding and testing the IIPServer component, which is the foundation of the Mirador IIIF image previewer system in Zenodo-RDM. By following this guide, you'll gain a clear understanding of how IIPServer works and the common issues you might encounter while testing it.

## Table of Contents

1. [What is IIPServer?](#what-is-iipserver)
2. [Architecture Overview](#architecture-overview)
3. [Step-by-Step Testing Guide](#step-by-step-testing-guide)
4. [Common Problems and Solutions](#common-problems-and-solutions)
5. [URL Structure Reference](#url-structure-reference)
6. [Command Reference](#command-reference)
7. [Troubleshooting Guide](#troubleshooting-guide)

## What is IIPServer?

IIPServer (IIP Image Server) is a specialized high-performance image server designed for delivering high-resolution images using the IIIF (International Image Interoperability Framework) protocol. It's a critical component in our image viewing system because:

- It handles the delivery of image tiles at different resolutions
- It can serve specific regions of images at different sizes and rotations
- It works with special Pyramid TIFF (PTIF) files that store multiple resolutions of the same image
- It provides the foundation for advanced image viewers like Mirador

In a nutshell, IIPServer is what allows users to smoothly zoom in and out of high-resolution images without loading the entire image at once.

## Architecture Overview

Understanding how IIPServer fits into the larger system is important for effective testing:

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

In this architecture:

1. Users upload images through the web application
2. The TilesProcessor converts images to Pyramid TIFF format
3. IIPServer serves these PTIF files via the IIIF protocol
4. The web browser displays the images using Mirador viewer

## Step-by-Step Testing Guide

### Step 1: Verify IIPServer Container is Running

First, check if the IIPServer container is running within your Docker environment:

```bash
docker-compose ps | grep iipserver
```

Example output:
```
zenodo-rdm-master-iipserver-1 iipsrv/iipsrv:latest "/bin/sh -c run" iipserver 18 minutes ago Up 18 minutes 8080/tcp, 0.0.0.0:9000->9000/tcp, 0.0.0.0:8080->80/tcp
```

This confirms the IIPServer is running properly with the correct port mappings (8080 and 9000).

### Step 2: Check IIPServer Configuration

To understand how the IIPServer is configured, examine its environment variables:

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

### Step 3: Understand Volume Mapping

Understanding how Docker volumes are mapped is crucial for testing. Check the Docker Compose configuration:

```bash
docker-compose config | grep -A10 "iipserver"
```

From the docker-compose.yml file, we can see:
```yaml
volumes:
  - ${INSTANCE_PATH:-./data}/images:/images # Default path if INSTANCE_PATH not defined
```

This means:
- Files in your local `./data/images` directory should be available inside the container at `/images`
- The IIPServer is configured to look in `/images/public` (a subdirectory of `/images`)

> **Important:** We discovered that the volume mapping can be different between development and production environments. In the full stack (docker-compose.full.yml), a named volume is used instead of a direct path mount.

### Step 4: Create Test Directory Structure

The IIIF system uses a specific directory structure for organizing images. Create a test directory that follows this pattern:

```bash
mkdir -p ./data/images/public/10/0_/_
```

This creates a directory structure that mimics how the application would store image tiles for record ID "10".

### Step 5: Create a Test Image

To test properly, you need a test image:

```bash
convert -size 1000x1000 xc:white -fill blue \
  -draw "circle 500,500 500,400" \
  ./data/images/test_image.png
```

Then copy it to the test directory:

```bash
cp ./data/images/test_image.png ./data/images/public/10/0_/_/test_image.png
```

### Step 6: Check Local Directory Structure

Verify that your test directories and images exist:

```bash
ls -la ./data/images/
ls -la ./data/images/public/10/0_/_
```

### Step 7: Verify Image Accessibility in Container

Check if the IIPServer container can access your test image:

```bash
docker-compose exec iipserver find /images -name "test_image.png"
```

If no result is returned, there may be an issue with the volume mapping. In this case, you can copy the file directly into the container:

```bash
docker cp ./data/images/test_image.png zenodo-rdm-master-iipserver-1:/images/public/
```

Verify the file is now accessible:

```bash
docker-compose exec iipserver ls -la /images/public/test_image.png
```

### Step 8: Test IIIF Endpoint Access

For IIPServer to work, you typically need a Pyramid TIFF file (PTIF), but we can test with a regular image first to validate the endpoint:

```bash
curl -I "http://localhost:8080/iiif/?IIIF=/test_image.png/info.json"
```

If you have a PTIF file:

```bash
curl -I "http://localhost:8080/iiif/?IIIF=/test_image.ptif/info.json"
```

## Common Problems and Solutions

During our testing, we encountered several issues. Here are the most common ones and their solutions:

### 1. Volume Mapping Issues

**Problem:** Files created in the host directory don't appear in the container.

**Symptoms:**
- `find` command in the container doesn't show files that exist in the host
- 404 errors when trying to access files via HTTP

**Causes:**
- Docker volume caching
- Permission issues
- Different directory structure between development and production

**Solutions:**
- Restart the container after creating new files:
  ```bash
  docker-compose restart iipserver
  ```
- Copy files directly into the container:
  ```bash
  docker cp ./local/file.png container_name:/container/path/
  ```
- Check Docker Compose configuration for correct volume mapping

### 2. PTIF File Format Requirements

**Problem:** The IIPServer returns errors when accessing non-PTIF files or improperly formatted PTIF files.

**Symptoms:**
- Error messages like: `is neither a file nor part of an image sequence`
- 404 errors when accessing seemingly valid files

**Causes:**
- PTIF files require a specific format with multiple resolution layers
- Regular image formats don't contain the pyramid structure needed

**Solutions:**
- Use the proper TilesProcessor from the application to create PTIF files
- Use tools like VIPS to manually create PTIF files:
  ```bash
  vips tiffsave input.jpg output.ptif --tile --pyramid --compression=none
  ```
- For testing purposes, understand that the full URL structure is needed

### 3. URL Structure Confusion

**Problem:** Incorrect URL structure leads to 404 errors even when files exist.

**Symptoms:**
- 404 errors when accessing files
- Error messages showing wrong file paths

**Causes:**
- IIIF URL structure is complex
- FILESYSTEM_PREFIX environment variable affects path resolution

**Solutions:**
- Use the correct endpoint format:
  ```
  http://localhost:8080/iiif/?IIIF=/filename.ptif/info.json
  ```
- Pay attention to the lack of "public" in the URL (since it's already in FILESYSTEM_PREFIX)
- When in doubt, check the error message to see what path the server is trying to access

### 4. Container Restart Required

**Problem:** Changes to files or configuration don't take effect immediately.

**Symptoms:**
- Updated files not visible
- Configuration changes not reflected in behavior

**Solutions:**
- Restart the IIPServer container:
  ```bash
  docker-compose restart iipserver
  ```

## URL Structure Reference

The IIIF protocol uses a specific URL structure:

```
http://server/iiif/?IIIF=/path/to/image.ptif/{region}/{size}/{rotation}/{quality}.{format}
```

Where:
- **region**: Part of the image to return (e.g., `full` or `x,y,width,height`)
- **size**: Dimensions of the returned image (e.g., `full`, `200,`, `^1000,`)
- **rotation**: Rotation in degrees (e.g., `0`, `90`, `180`)
- **quality**: Image quality (e.g., `default`, `color`, `gray`)
- **format**: Image format (e.g., `jpg`, `png`)

**Important:** For our IIPServer setup, we discovered through testing that the correct URL format is:

```
http://localhost:8080/iiif/?IIIF=/test_image.ptif/info.json
```

Note the addition of the question mark after "iiif/" and the removal of "public" from the path (since it's included in FILESYSTEM_PREFIX).

## Command Reference

Here's a quick reference of the most useful commands for testing the IIPServer:

| Command | Purpose |
|---------|---------|
| `docker-compose ps \| grep iipserver` | Check if IIPServer is running |
| `docker-compose exec iipserver env` | View IIPServer environment variables |
| `docker-compose exec iipserver ls -la /images/public` | List files in the public images directory |
| `docker-compose restart iipserver` | Restart the IIPServer container |
| `docker cp ./file.png container_name:/images/public/` | Copy a file directly into the container |
| `curl -I "http://localhost:8080/iiif/?IIIF=/image.ptif/info.json"` | Test an IIIF endpoint |
| `docker-compose logs --tail=50 iipserver` | View IIPServer logs |
| `docker-compose exec iipserver find /images -name "*.ptif"` | Find PTIF files in the container |

## Troubleshooting Guide

When problems occur, follow this systematic approach:

```
┌─────────────────┐
│  Check Container│
│     Status      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Verify Volume   │
│    Mapping      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Check File      │
│  Existence      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Test IIIF URL   │
│   Structure     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Examine IIPServer│
│     Logs        │
└─────────────────┘
```

### Step-by-Step Troubleshooting

1. **Check Container Status**
   ```bash
   docker-compose ps | grep iipserver
   ```
   Ensure status is "Up" and ports are correctly mapped.

2. **Verify Volume Mapping**
   ```bash
   docker-compose config | grep -A10 "iipserver"
   ```
   Make sure volumes are correctly mapped between host and container.

3. **Check File Existence in Container**
   ```bash
   docker-compose exec iipserver ls -la /images/public
   docker-compose exec iipserver find /images -name "test_image.ptif"
   ```
   Confirm files actually exist inside the container.

4. **Test IIIF URL Structure**
   ```bash
   curl -I "http://localhost:8080/iiif/?IIIF=/test_image.ptif/info.json"
   ```
   Try different URL formats if necessary.

5. **Examine IIPServer Logs**
   ```bash
   docker-compose logs --tail=50 iipserver
   ```
   Look for error messages that might explain issues.

## Key Lessons Learned

During our testing process, we learned several important lessons:

1. The IIPServer requires specially formatted PTIF files to function correctly
2. Volume mapping in Docker can be tricky and may require direct file copying
3. URL structure is critical and depends on the FILESYSTEM_PREFIX configuration
4. Testing isolated components (like IIPServer) is helpful but has limitations
5. For a full end-to-end test, the entire application stack is needed

## Conclusion

Testing the IIPServer component is an essential step in ensuring the proper functioning of the Mirador IIIF image previewer system. By following this guide, you should be able to validate that your IIPServer is correctly configured and can serve IIIF-compliant image requests.

Remember that for a complete test of the image viewing functionality, you'll need the full application stack with proper image processing to create valid PTIF files. However, the isolated IIPServer testing described in this guide is valuable for troubleshooting specific issues with the image serving component. 


Yes, I'm here! Let me continue investigating the IIIF manifest generation in the Zenodo-RDM codebase.

```bash
find /Users/alaaalbarazi/Projects/Turath/Coding/zenodo-rdm-master/.venv/lib/python3.9/site-packages/invenio_rdm_records -path "*iiif*" -type d
```
Let's look at the IIIF-related files in the invenio_rdm_records package:

```bash
find /Users/alaaalbarazi/Projects/Turath/Coding/zenodo-rdm-master/.venv/lib/python3.9/site-packages/invenio_rdm_records -path "*iiif*.py" -o -path "*manifest*.py" | grep -v __pycache__
```
Let's examine the IIIF resources and proxy class:

```bash
cat /Users/alaaalbarazi/Projects/Turath/Coding/zenodo-rdm-master/.venv/lib/python3.9/site-packages/invenio_rdm_records/resources/iiif.py
```
Now let's look at the IIIF manifest serializer to understand how the manifests are generated:

```bash
cat /Users/alaaalbarazi/Projects/Turath/Coding/zenodo-rdm-master/.venv/lib/python3.9/site-packages/invenio_rdm_records/resources/serializers/iiif/schema.py
```
Let's examine the IIIF service to understand how it interacts with the records and files:

```bash
cat /Users/alaaalbarazi/Projects/Turath/Coding/zenodo-rdm-master/.venv/lib/python3.9/site-packages/invenio_rdm_records/services/iiif/service.py
```
Finally, let's check how the serializers are registered for IIIF:

```bash
cat /Users/alaaalbarazi/Projects/Turath/Coding/zenodo-rdm-master/.venv/lib/python3.9/site-packages/invenio_rdm_records/resources/serializers/__init__.py
```

```bash
cat /Users/alaaalbarazi/Projects/Turath/Coding/zenodo-rdm-master/.venv/lib/python3.9/site-packages/invenio_rdm_records/resources/serializers/iiif/__init__.py
```

# IIIF Testing Guide for Zenodo-RDM

This guide provides detailed instructions for testing the IIIF (International Image Interoperability Framework) functionality in Zenodo-RDM.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Core Services Testing](#core-services-testing)
3. [IIPServer Testing](#iipserver-testing)
4. [IIIF Manifest Testing](#iiif-manifest-testing)
5. [Mirador Viewer Testing](#mirador-viewer-testing)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

Before testing IIIF functionality, ensure you have:

- A running Zenodo-RDM instance
- Docker and docker-compose installed
- IIPServer container running
- Python virtual environment activated

## Core Services Testing

The first step is to verify that the required services are running:

```bash
cd site
source ../.venv/bin/activate
IIPSERVER_URL=http://localhost:8080 WEB_URL=http://localhost:5000 python tests/iiif/test_core_services.py
```

This test checks if:
- The IIPServer is running at the specified URL
- The web server is running at the specified URL

## IIPServer Testing

Once core services are verified, test the basic functionality of the IIPServer:

```bash
cd site
source ../.venv/bin/activate
IIPSERVER_URL=http://localhost:8080 python tests/iiif/test_simple_iipserver.py
```

This test verifies:
- The IIPServer is running and accepting connections
- The FastCGI endpoint is available
- (Optional) The test image is accessible

### IIPServer Issues

If the IIPServer is not running or crashes, try:

```bash
docker-compose restart iipserver
docker-compose logs iipserver
```

If the test image is not accessible, verify:
- The file exists in the container: `docker-compose exec iipserver ls -la /images/public/`
- The file has correct permissions
- The file is in valid PTIF format

## IIIF Manifest Testing

To test IIIF manifest generation, you need:
1. A record with image files
2. The files converted to PTIF format
3. Authentication credentials

### Steps:

1. Create a test record with image files
2. Use the authenticated manifest test:

```bash
cd site
source ../.venv/bin/activate
RDM_TOKEN=<your-token> RECORD_ID=<record-id> python tests/iiif/test_authenticated_manifest.py
```

## Mirador Viewer Testing

Once manifests are correctly generated, test the Mirador viewer:

1. Create a record with multiple image files
2. Convert the files to PTIF format
3. Open the record page in a browser
4. Click on the IIIF button to open the Mirador viewer
5. Verify that images load correctly in the viewer
6. Test navigation between images
7. Test zoom functionality

## Troubleshooting

### IIPServer Issues

- **500 Internal Server Error**: The PTIF file might be corrupted or incompatible with the IIPServer version
- **403 Forbidden**: This is normal for the base URL, but not for the image URLs
- **Connection Error**: The IIPServer might be down

### Manifest Generation Issues

- **Missing PTIF Files**: Ensure the file conversion process completed successfully
- **Authentication Errors**: Verify your token has the correct permissions
- **Invalid Manifest Structure**: Check the manifest against the IIIF presentation API specification

### Mirador Viewer Issues

- **Images Don't Load**: Check the browser console for errors
- **Missing Navigation**: Verify the manifest includes a proper sequence
- **Zoom Issues**: Ensure the PTIF files were created correctly

## Testing Strategy

For reliable testing:

1. Start with core services tests
2. Progress to IIPServer tests
3. Test manifest generation with authentication
4. Finally, test the Mirador viewer

This layered approach helps isolate issues to specific components of the IIIF stack. 
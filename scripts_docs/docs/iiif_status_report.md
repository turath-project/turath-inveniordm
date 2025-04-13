# IIIF Status Report

This document summarizes the current status of the IIIF functionality in Zenodo-RDM, including identified issues and requirements for full implementation.

## Current Status

Our testing has confirmed:

- ✅ IIPServer is running and accessible
- ✅ IIPServer can successfully serve regular image files
- ✅ Volume mounting between host and container is working correctly
- ❌ Missing PTIF files required for IIIF functionality
- ❌ No worker service configured for PTIF conversion

## Diagnostic Findings

### 1. Server Functionality

The IIPServer itself is functioning correctly:
- Accessible at http://localhost:8080/fcgi-bin/iipsrv.fcgi
- Can serve regular image files placed in the `/images/public/` directory
- Responds to basic IIP protocol commands

### 2. Configuration and Environment

Environment variables are correctly set:
- `FILESYSTEM_PREFIX=/images/public`
- IIPServer container is correctly configured to serve from this location

### 3. Missing Components

Essential components not yet implemented:
- PTIF conversion tools (like vips) not available in the container
- No worker service configured to handle asynchronous conversion
- Missing directory structure for private record files

## Requirements for Full IIIF Functionality

To enable complete IIIF functionality in Zenodo-RDM, the following steps are necessary:

1. **Install PTIF Conversion Tools**
   - Add vips or similar tools to the IIPServer container
   - Or create a separate worker container with these tools

2. **Set Up Worker Service**
   - Configure a worker service in docker-compose.yml
   - Implement asynchronous processing of uploaded images
   - Ensure conversion to PTIF format for IIIF compatibility

3. **Configure Path Structure**
   - Ensure the converted PTIF files are placed in correct directories:
     - Public files: `/images/public/`
     - Record files: `/images/private/{record_id}/`

4. **Update Manifest Generation**
   - Ensure manifests correctly reference the IIPServer URLs
   - Verify proper authentication flow for private images

## Manual Testing Guide

For manual testing of the IIPServer without the full IIIF workflow:

1. Place test images in the appropriate directories:
   ```bash
   # Add public test image
   docker-compose exec iipserver mkdir -p /images/public
   docker-compose cp test_image.png iipserver:/images/public/
   ```

2. Test direct IIPServer access:
   ```bash
   curl "http://localhost:8080/fcgi-bin/iipsrv.fcgi?FIF=/test_image.png&OBJ=Basic-Info"
   ```

3. For record-specific images (once worker service is configured):
   ```bash
   # Images should be in record-specific directories
   docker-compose exec iipserver mkdir -p /images/private/record-id
   ```

## Conclusion

The IIPServer component is working correctly, but the complete IIIF workflow requires additional implementation of PTIF conversion tools and a worker service to process images asynchronously. With these additions, the system would be able to provide full IIIF functionality for viewing images in the Mirador viewer.

## Related Documentation

- [IIIF Manual Testing Guide](iiif_manual_testing.md)
- [Testing IIPServer](testing_iipserver.md)
- [Image Conversion Process](image_conversion_process.md) 
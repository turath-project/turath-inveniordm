# Cantaloupe IIIF Server Integration

This document explains how to test and use the Cantaloupe IIIF server that has been integrated into the project for image processing and delivery.

## Overview

The Cantaloupe IIIF server provides standardized image delivery according to the [IIIF Image API specification](https://iiif.io/api/image/3.0/). This allows for advanced image viewing capabilities such as deep zoom, rotation, and region selection.

**Note:** This setup is currently isolated for testing purposes and not yet integrated with the InvenioRDM workflow.

## Prerequisites

- Docker and Docker Compose installed
- Basic understanding of IIIF concepts

## Setup and Testing

### 1. Starting the Cantaloupe server

The Cantaloupe service is defined in `docker-compose.yml`. To start it:

```bash
docker-compose up -d cantaloupe
```

### 2. Testing with sample images

1. Create a test-images directory (if it doesn't exist):
   ```bash
   mkdir -p test-images
   ```

2. Add JPEG test images to this directory:
   ```bash
   # Option 1: Copy an existing image
   cp /path/to/your/image.jpg test-images/test.jpg
   
   # Option 2: Download a sample image
   curl -L -o test-images/sample.jpg https://upload.wikimedia.org/wikipedia/commons/b/b7/JPEG_example_flower.jpg
   ```

3. Verify the image format:
   ```bash
   file test-images/test.jpg
   ```
   Ensure it shows "JPEG image data" in the output.

### 3. Accessing images via IIIF

Once Cantaloupe is running, access your images using the IIIF URL pattern: 
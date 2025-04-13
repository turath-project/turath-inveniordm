# IIIF Implementation Details for Zenodo-RDM

This document provides in-depth details on implementing IIIF (International Image Interoperability Framework) functionality in Zenodo-RDM.

## Understanding the Architecture

Zenodo-RDM uses a multi-component architecture for IIIF implementation:

```
┌─────────────────────────────┐      ┌────────────────────┐     ┌─────────────────┐
│                             │      │                    │     │                 │
│  Zenodo-RDM Web Interface   │──────▶  Record Database   │     │  File Storage   │
│  (Flask/Invenio)            │      │  (PostgreSQL)      │     │  (S3/Local)     │
│                             │      │                    │     │                 │
└─────────────────────────────┘      └────────────────────┘     └────────┬────────┘
           │                                    │                         │
           │                                    │                         │
           ▼                                    ▼                         ▼
┌─────────────────────────────┐      ┌────────────────────┐     ┌─────────────────┐
│                             │      │                    │     │                 │
│  IIIF Presentation API      │◀─────▶  IIIF Image API    │◀────▶  PTIF Images    │
│  (Manifests)                │      │  (IIPServer)       │     │                 │
│                             │      │                    │     │                 │
└─────────────────────────────┘      └────────────────────┘     └─────────────────┘
           │                                    │
           │                                    │
           ▼                                    ▼
┌─────────────────────────────┐      ┌────────────────────┐
│                             │      │                    │
│  IIIF Viewer                │◀─────▶  Browser           │
│  (Mirador/OpenSeadragon)    │      │                    │
│                             │      │                    │
└─────────────────────────────┘      └────────────────────┘
```

## Key Components in Detail

### 1. IIPServer (IIIF Image Server)

IIPServer is a Fast CGI server that implements the IIIF Image API, enabling deep zoom functionality for high-resolution images.

**Technical Details:**
- Deployed as a Docker container in Zenodo-RDM
- Uses a FCGI protocol to serve image requests
- Configured to read images from `/images/public` directory
- Supports IIIF Image API version 3.0
- Handles image transformations (resizing, rotation, quality)

**Configuration Parameters:**
```
FILESYSTEM_PREFIX=/images/public
VERBOSITY=6
LOGFILE=/tmp/iipsrv.log
MAX_IMAGE_CACHE_SIZE=10
JPEG_QUALITY=90
MAX_CVT=5000
```

### 2. PTIF Format (Pyramid TIFF)

PTIF is a specialized TIFF format that stores the same image at multiple resolutions to enable efficient zooming.

**Technical Details:**
- Multi-resolution image format
- Contains several downsampled versions of the original image
- Typically created using Kakadu's `kdu_compress` tool
- Enables efficient region extraction without loading the entire image
- Reduces bandwidth and improves zoom performance

**File Structure:**
```
┌───────────────────────────────┐
│  TIFF Header                  │
├───────────────────────────────┤
│  Full Resolution Image Data   │
├───────────────────────────────┤
│  1/2 Resolution Image Data    │
├───────────────────────────────┤
│  1/4 Resolution Image Data    │
├───────────────────────────────┤
│  1/8 Resolution Image Data    │
├───────────────────────────────┤
│  ...                          │
├───────────────────────────────┤
│  Thumbnail Image Data         │
└───────────────────────────────┘
```

### 3. Single File Converter (`convert_to_ptif.py`)

This Python script converts a single image file to PTIF format and places it in the IIPServer's accessible location.

**Script Structure:**
```
┌──────────────────────────────┐
│  Check Dependencies          │
├──────────────────────────────┤
│  Get Input File & Record ID  │
├──────────────────────────────┤
│  Convert to PTIF             │
├──────────────────────────────┤
│  Check IIPServer Environment │
├──────────────────────────────┤
│  Copy File to IIPServer      │
├──────────────────────────────┤
│  Verify IIIF URLs            │
└──────────────────────────────┘
```

**Key Functions:**
- `check_dependencies()`: Ensures required tools are installed
- `convert_to_ptif()`: Runs the conversion command
- `check_iipserver_env()`: Checks the IIPServer configuration
- `copy_to_iipserver()`: Copies the file to the correct location
- `verify_iiif_url()`: Prints IIIF URLs for testing

### 4. Batch Processor (`batch_convert.py`)

This Python script processes all image files within a record, converting them to PTIF format and placing them in the IIPServer's accessible location.

**Script Structure:**
```
┌──────────────────────────────┐
│  Get Record ID               │
├──────────────────────────────┤
│  Fetch Record Files          │
├──────────────────────────────┤
│  Filter Image Files          │
├──────────────────────────────┤
│  Download Files              │
├──────────────────────────────┤
│  Convert Each File to PTIF   │
├──────────────────────────────┤
│  Copy Files to IIPServer     │
├──────────────────────────────┤
│  Verify IIIF Manifest        │
└──────────────────────────────┘
```

**Key Functions:**
- `get_record_files()`: Fetches metadata for all files in a record
- `download_file()`: Downloads a file from the record
- `batch_convert()`: Orchestrates the conversion process
- `verify_iiif_manifest()`: Checks if the IIIF manifest is accessible

### 5. IIIF Viewer (`iiif_viewer.html` and `serve_viewer.py`)

The viewer is built using OpenSeadragon, a JavaScript library for viewing zoomable images. It's served by a simple Python HTTP server.

**Viewer Components:**
```
┌──────────────────────────────┐
│  Image Input Controls        │
├──────────────────────────────┤
│  OpenSeadragon Viewer        │
├──────────────────────────────┤
│  Image Metadata Display      │
├──────────────────────────────┤
│  Thumbnail Gallery           │
└──────────────────────────────┘
```

**Key Features:**
- Dynamic loading of IIIF images by record ID and filename
- Thumbnail gallery for browsing all images in a record
- Image information display
- Zoom and pan controls

## Integration with Zenodo-RDM

### The Integration Gap

Zenodo-RDM includes built-in IIIF support, but there's a gap in the implementation:

1. Zenodo-RDM expects images to be converted to PTIF format
2. The conversion process is typically handled by a worker process
3. This worker process is not properly configured in our deployment

Without this conversion, IIIF functionality is broken even though the underlying components (IIPServer, viewer) are present.

### Integration Points

Our solution provides:

1. **Manual Conversion Tools**: Scripts to convert images to PTIF format
2. **IIPServer Configuration**: Proper file placement for IIPServer to serve images
3. **Custom Viewer**: Direct access to IIIF images without relying on Zenodo-RDM's manifest endpoint

### Future Integration

For a complete integration, the following would be necessary:

1. **Automatic Conversion**: Integrate the conversion process with Zenodo-RDM's file upload workflow
2. **Manifest Endpoint Fix**: Fix the issues with Zenodo-RDM's IIIF manifest endpoint
3. **Viewer Integration**: Integrate the custom viewer with Zenodo-RDM's user interface 
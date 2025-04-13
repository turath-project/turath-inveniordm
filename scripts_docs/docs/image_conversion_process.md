# From Images to IIIF: Understanding the Pyramid TIFF Conversion Process

This document provides a comprehensive explanation of how the Zenodo-RDM system converts regular image files (JPEG, PNG, etc.) into Pyramid TIFF (PTIF) files for use with the IIIF image server. This conversion is crucial for enabling responsive, high-resolution image viewing in the Mirador viewer.

## Table of Contents

1. [Overview of the Conversion Process](#overview-of-the-conversion-process)
2. [Key Components Involved](#key-components-involved)
3. [Step-by-Step Conversion Workflow](#step-by-step-conversion-workflow)
4. [PyVIPS: The Heart of the Conversion](#pyvips-the-heart-of-the-conversion)
5. [File Storage and Organization](#file-storage-and-organization)
6. [Testing the Conversion Process](#testing-the-conversion-process)
7. [Troubleshooting Common Issues](#troubleshooting-common-issues)

## Overview of the Conversion Process

When a user uploads an image to Zenodo-RDM, the system initiates a workflow to convert supported image formats (JPEG, PNG, TIFF, etc.) into Pyramid TIFF (PTIF) files. These PTIF files contain multiple resolution levels of the same image in a hierarchical structure, which allows the IIPServer to efficiently serve specific portions of images at different zoom levels.

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│                 │       │                 │       │                 │
│   Original      │──────►│  TilesProcessor │──────►│  PTIF File      │
│   Image File    │       │  (PyVIPS)       │       │  (.ptif)        │
│                 │       │                 │       │                 │
└─────────────────┘       └─────────────────┘       └─────────────────┘
                                   │                        │
                                   │                        │
                                   ▼                        ▼
                          ┌─────────────────┐      ┌─────────────────┐
                          │                 │      │                 │
                          │  Record Update  │      │  IIPServer      │
                          │  (Metadata)     │      │  (Image Serving)│
                          │                 │      │                 │
                          └─────────────────┘      └─────────────────┘
```

## Key Components Involved

The conversion process involves several key components:

1. **TilesProcessor**: A record processor that identifies image files eligible for conversion and initiates the process.

2. **PyVIPSImageConverter**: Uses the PyVIPS library (a Python binding for the libvips image processing library) to convert images to Pyramid TIFF format.

3. **LocalTilesStorage**: Manages the storage of PTIF files in a structured directory hierarchy.

4. **Celery Task System**: Handles asynchronous processing to prevent blocking the main application thread during conversion.

5. **Record Metadata**: Tracks the status of tile generation and links to the generated PTIF files.

## Step-by-Step Conversion Workflow

The conversion follows these steps:

### 1. Identifying Eligible Files

The `TilesProcessor` examines each file in the record and identifies those with extensions matching the configured list of valid extensions:

```python
@property
def valid_exts(self) -> list:
    """Return valid extensions for tiles generation from config/default."""
    return current_app.config.get(
        "IIIF_TILES_VALID_EXTENSIONS", ["tiff", "pdf", "jpeg", "png"]
    )
```

### 2. Initiating Conversion

For each eligible file, the processor:
- Creates a placeholder entry in the record's media files with a `.ptif` extension
- Sets the initial processing status
- Registers a Celery task to perform the actual conversion

```python
def _process_file(self, file_record, draft, record, file_type, uow=None):
    """Process a file record to kickoff pyramidal tiff generation."""
    if not self._can_process_file(file_record, draft, record):
        return
    
    # Create or update status file
    status_file = record.media_files.get(f"{file_record.key}.ptif")
    if status_file:
        has_file_changed = status_file.processor["source_file_id"] != str(
            file_record.file.id
        )
        if status_file.processor["status"] == "finished" and not has_file_changed:
            return
            
    # Initialize processing and register task
    status_file.processor = {
        "type": "image-tiles",
        "status": "init",
        "source_file_id": str(file_record.file.id),
        "props": {},
    }
    
    # Register the conversion task
    uow.register(
        TaskOp(
            generate_tiles,
            record_id=record["id"],
            file_key=file_record.key,
            file_type=file_type,
        )
    )
```

### 3. Asynchronous Conversion

The Celery task `generate_tiles` handles the actual conversion:

```python
@shared_task(ignore_result=True)
def generate_tiles(record_id, file_key, file_type):
    """Generate pyramidal TIFF."""
    record = current_rdm_records_service.record_cls.pid.resolve(record_id)
    status_file = record.media_files[file_key + ".ptif"]
    status_file.processor["status"] = "processing"
    status_file.commit()
    db.session.commit()

    conversion_state = tiles_storage.save(record, file_key, file_type)

    status_file.processor["status"] = "finished" if conversion_state else "failed"
    status_file.file.file_model.uri = str(
        tiles_storage._get_file_path(record, file_key)
    )
    status_file.commit()
    db.session.commit()
```

### 4. Storage and Path Generation

The `LocalTilesStorage` class manages where and how the PTIF files are stored:

```python
def _get_dir(self, record: RDMRecord) -> Path:
    """Get directory."""
    recid = record.pid.pid_value

    # Creates a directory structure based on the record ID
    # e.g., record ID "12345" becomes "12/34/5_"
    recid_parts = wrap(recid.ljust(4, "_"), 2)
    start_parts = recid_parts[:2]
    end_parts = recid_parts[2:]
    recid_path = "/".join(start_parts)
    if end_parts:
        recid_path += f"/{''.join(end_parts)}_"
    else:
        recid_path += "/_"

    path_partitions = recid_path.split("/")

    return (
        self.base_path / record.access.protection.files / Path(*path_partitions)
    ).absolute()
```

## PyVIPS: The Heart of the Conversion

The actual conversion from a standard image to a Pyramid TIFF is handled by the PyVIPS library via the `PyVIPSImageConverter` class:

```python
def convert(self, in_stream, out_stream):
    """Convert to ptifs."""
    if not HAS_VIPS:
        return

    try:
        source = self.fp_source(in_stream)
        target = self.fp_target(out_stream)

        image = pyvips.Image.new_from_source(source, "", access="sequential")
        image.tiffsave_target(target, tile=True, pyramid=True, **self.params)
        return True
    except Exception:
        current_app.logger.exception("Image processing with pyvips failed")
        return False
```

Key parameters for the conversion are:
- `tile=True`: Creates tiled TIFF files (rather than strip-based)
- `pyramid=True`: Creates a multi-resolution pyramid structure
- Additional parameters from configuration (default values):
  ```python
  default_params = {
      "compression": "jpeg",
      "Q": 90,
      "tile_width": 256,
      "tile_height": 256,
  }
  ```

## File Storage and Organization

The PTIF files are stored following a specific directory structure based on the record ID. This structure is important for both organization and performance reasons:

1. **Base Path**: Defined by `IIIF_TILES_STORAGE_BASE_PATH` (default: "images/")
2. **Access Level**: Public or restricted (based on record.access.protection.files)
3. **Record ID Partitioning**: The record ID is split into chunks to create a hierarchical structure

For example, a record with ID "12345" and public access would have its PTIF files stored at:
```
{instance_path}/images/public/12/34/5_/filename.ptif
```

## Testing the Conversion Process

To test the image conversion process, follow these steps:

### Prerequisites

1. Ensure PyVIPS is installed in your environment:
   ```bash
   pip install pyvips
   ```

2. Make sure libvips is installed on your system:
   - Ubuntu/Debian: `apt-get install libvips`
   - macOS: `brew install vips`

### Testing Using the Command Line

You can test the conversion process directly using the `generate_iiif_tiles.py` script:

```bash
# Ensure invenio is running in the virtual environment
source .venv/bin/activate

# Run the tile generation script for a specific record ID
python scripts/generate_iiif_tiles.py RECORD_ID
```

### Testing Through the Web Interface

1. Start the full application stack:
   ```bash
   docker-compose -f docker-compose.full.yml up -d
   ```

2. Upload a test image through the web interface (e.g., a high-resolution JPEG or PNG)

3. After uploading, check the processing status in the logs:
   ```bash
   docker-compose logs -f worker
   ```

4. Once processing is complete, verify that PTIF files were created:
   ```bash
   find ./data/images -name "*.ptif"
   ```

5. Test viewing the image through the IIIF API:
   ```bash
   curl -I http://localhost:5001/api/iiif/record:{record_id}:{filename}/info.json
   ```

### Inspecting PTIF Files

You can inspect the structure of a generated PTIF file using various tools:

1. **Using VIPS CLI**:
   ```bash
   vipsheader ./data/images/public/XX/YY/Z_/filename.ptif
   ```

2. **Using tiffinfo**:
   ```bash
   tiffinfo ./data/images/public/XX/YY/Z_/filename.ptif
   ```

## Troubleshooting Common Issues

### 1. PyVIPS Installation Problems

**Problem**: PyVIPS installation fails or the module cannot be imported.

**Solutions**:
- Ensure libvips is properly installed on your system
- Check for compatible versions between libvips and pyvips
- For development, consider using the Docker container which has libvips pre-installed

### 2. Conversion Fails for Specific Images

**Problem**: Some images fail to convert while others succeed.

**Solutions**:
- Check the file format and integrity of the original image
- Look for error messages in the logs:
  ```bash
  docker-compose logs worker | grep "Image processing with pyvips failed"
  ```
- Try different compression settings in your configuration

### 3. PTIF Files Not Being Created

**Problem**: The conversion process starts but no PTIF files appear.

**Solutions**:
- Check if `IIIF_TILES_GENERATION_ENABLED` is set to `True` in configuration
- Verify the file extension is in `IIIF_TILES_VALID_EXTENSIONS`
- Check file permissions on the images directory

### 4. Directory Structure Issues

**Problem**: PTIF files are created but in unexpected locations.

**Solutions**:
- Verify the `IIIF_TILES_STORAGE_BASE_PATH` setting
- Check the record ID and how it's being partitioned into directories
- Ensure the record access level is correctly set (public/restricted)

## Conclusion

The image to PTIF conversion process is a critical component of the Zenodo-RDM IIIF image viewer system. Understanding how this conversion works is essential for properly configuring, testing, and troubleshooting the image viewing functionality.

By leveraging the PyVIPS library, Zenodo-RDM efficiently creates Pyramid TIFF files that enable responsive, high-resolution image viewing through the IIPServer and Mirador viewer components. 
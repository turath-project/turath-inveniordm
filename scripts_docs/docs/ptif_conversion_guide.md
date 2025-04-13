# PTIF Conversion Guide for IIIF in Zenodo-RDM

This guide documents the process of implementing PTIF (Pyramid TIFF) image conversion for enabling IIIF functionality in Zenodo-RDM. PTIF files are essential for the IIPServer to serve images via the IIIF protocol.

## The Problem: Missing PTIF Conversion

When deploying Zenodo-RDM locally, we encountered an issue with the IIIF functionality. The IIPServer was running correctly, but it couldn't serve images via the IIIF protocol because:

1. The IIPServer requires PTIF format images
2. There was no worker service to convert uploaded images to PTIF format
3. The volume mounting was configured correctly, but no PTIF files existed

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  User uploads │     │  ✗ MISSING ✗  │     │  IIPServer    │
│  image files  │────>│  PTIF         │────>│  can't serve  │
│  (.jpg, .png) │     │  Conversion   │     │  IIIF images  │
└───────────────┘     └───────────────┘     └───────────────┘
```

## Solution Options

We have two approaches to solve this issue:

1. **Custom PTIF Conversion** - A standalone solution that doesn't modify Zenodo-RDM's codebase
2. **Zenodo's Built-in Tools** - Utilizing Zenodo-RDM's existing PTIF conversion functionality

## Option 1: Custom PTIF Conversion

Without modifying the core Zenodo-RDM codebase, we implemented a solution to manually convert images to PTIF format:

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  User uploads │     │ Our converter │     │  IIPServer    │
│  image files  │────>│ script creates│────>│  serves IIIF  │
│  (.jpg, .png) │     │ .ptif files   │     │  images       │
└───────────────┘     └───────────────┘     └───────────────┘
```

### Implementation Steps

#### Step 1: Create a Conversion Script

We created a shell script (`convert_images.sh`) that uses the `vips` tool to convert image files to PTIF format:

```bash
#!/bin/bash
# Simple script to convert images to PTIF format for IIPServer
# Requires vips to be installed: apt-get install -y libvips-tools

set -e

# Default image directory
IMAGE_DIR="./data/images"

# Check if vips is installed
if ! command -v vips &> /dev/null; then
    echo "Error: vips is not installed. Please install with 'apt-get install -y libvips-tools' or 'brew install vips'"
    exit 1
fi

# Ensure the directory structure exists
mkdir -p "$IMAGE_DIR/public" "$IMAGE_DIR/private"

# Process all PNG, JPG, and TIF files
echo "Searching for image files in $IMAGE_DIR..."
find "$IMAGE_DIR" -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.tif" -o -name "*.tiff" \) | while read img; do
    # Generate output filename with .ptif extension
    ptif_file="${img%.*}.ptif"
    
    # Skip if already converted
    if [ -f "$ptif_file" ]; then
        echo "Skipping already converted: $img"
        continue
    fi
    
    echo "Converting $img to $ptif_file"
    vips tiffsave "$img" "$ptif_file" --tile --pyramid || echo "Failed to convert $img"
done

echo "Conversion complete"
echo "Make sure docker volume mounting is working correctly with:"
echo "  docker-compose exec iipserver ls -la /images/public/"
echo ""
echo "Test a PTIF file with:"
echo "  curl \"http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/path/to/image.ptif/info.json\""
```

#### Step 2: Make the Script Executable

```bash
chmod +x convert_images.sh
```

#### Step 3: Install Prerequisites

The script requires `vips` to be installed on your local system:

```bash
# On macOS
brew install vips

# On Ubuntu/Debian
sudo apt-get install -y libvips-tools
```

#### Step 4: Run the Conversion Script

```bash
./convert_images.sh
```

#### Step 5: Copy PTIF Files to the Public Directory

```bash
cp data/images/*.ptif data/images/public/
```

#### Step 6: Verify Files in the IIPServer Container

```bash
docker-compose exec iipserver ls -la /images/public/
```

#### Step 7: Test IIIF Functionality

```bash
curl "http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/test_image.ptif/info.json"
```

## Option 2: Using Zenodo's Built-in PTIF Conversion Tools

After our initial solution, we discovered that Zenodo-RDM already includes functionality for PTIF conversion. This is a more integrated approach that leverages the existing codebase.

### Zenodo's PTIF Conversion Process

Zenodo-RDM uses a class called `TilesProcessor` to generate IIIF tiles (PTIF files) for records. The `scripts/generate_iiif_tiles.py` script demonstrates how to use this functionality:

```python
"""Generate IIIF tiles for a list of records."""
from invenio_rdm_records.proxies import current_rdm_records_service as service
from invenio_rdm_records.records.processors.tiles import TilesProcessor
from invenio_records_resources.services.files.processors.image import ImageMetadataExtractor
from invenio_records_resources.services.uow import UnitOfWork, RecordCommitOp
import sys
import csv


image_metadata_extractor = ImageMetadataExtractor()

def generate_iiif_tiles(recid):
    with UnitOfWork() as uow:
        record = service.record_cls.pid.resolve(recid)
        processor = TilesProcessor()
        # Call the processor on the record
        processor(None, record, uow=uow)
        uow.register(RecordCommitOp(record))

        # Calculate image dimensions for each supported image file
        for file_record in record.files.values():
            if image_metadata_extractor.can_process(file_record):
                image_metadata_extractor.process(file_record)
                file_record.commit()
        uow.commit()
```

### Using the Built-in Tools

To use Zenodo's built-in PTIF conversion:

#### Step 1: Create a Simple Script to Process Existing Records

Create a file called `convert_existing_records.py`:

```python
#!/usr/bin/env python3
"""
Script to convert existing records' images to PTIF format for IIIF support.
"""

import sys
import os
from invenio_rdm_records.proxies import current_rdm_records_service as service
from invenio_rdm_records.records.processors.tiles import TilesProcessor
from invenio_records_resources.services.files.processors.image import ImageMetadataExtractor
from invenio_records_resources.services.uow import UnitOfWork, RecordCommitOp

def generate_iiif_tiles(recid):
    """Generate IIIF tiles for a record."""
    print(f"Processing record {recid}...")
    
    with UnitOfWork() as uow:
        try:
            record = service.record_cls.pid.resolve(recid)
            processor = TilesProcessor()
            # Call the processor on the record
            processor(None, record, uow=uow)
            uow.register(RecordCommitOp(record))

            # Calculate image dimensions for each supported image file
            image_metadata_extractor = ImageMetadataExtractor()
            for file_record in record.files.values():
                if image_metadata_extractor.can_process(file_record):
                    image_metadata_extractor.process(file_record)
                    file_record.commit()
            
            uow.commit()
            print(f"✓ Successfully processed record {recid}")
            return True
        except Exception as e:
            print(f"✗ Error processing record {recid}: {e}")
            return False

def process_records(record_ids):
    """Process a list of record IDs."""
    success = 0
    failure = 0
    
    for recid in record_ids:
        if generate_iiif_tiles(recid):
            success += 1
        else:
            failure += 1
    
    print(f"\nProcessing complete: {success} successful, {failure} failed")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Process records specified as command-line arguments
        record_ids = sys.argv[1:]
        process_records(record_ids)
    else:
        print("Usage: python convert_existing_records.py RECORD_ID [RECORD_ID...]")
        print("Example: python convert_existing_records.py 1234 5678")
        sys.exit(1)
```

#### Step 2: Run the Script for Specific Records

```bash
cd site
python convert_existing_records.py 123 456 789
```

Replace `123 456 789` with the actual record IDs you want to process.

#### Step 3: Configure Automatic Processing for New Records

To ensure that new uploads are automatically processed:

1. Make sure the worker service is running in your docker-compose configuration
2. Check that the `IIIF_PREVIEW_ENABLED` setting is enabled in your `invenio.cfg`:

```python
# Enable IIIF preview
IIIF_PREVIEW_ENABLED = True
```

3. Ensure proper file storage class mappings:

```python
FILES_REST_STORAGE_CLASS_MAPPING = {
    'L': 'local',
    'F': 'iiif',
}
```

### Advantages of Using Built-in Tools

1. **Integration**: Uses the same codebase as Zenodo-RDM
2. **Automatic Processing**: Can be configured to run automatically for new uploads
3. **Metadata Extraction**: Extracts image metadata for better IIIF support
4. **Consistency**: Ensures consistent PTIF generation as used in production Zenodo

## IIIF URL Structure

The IIIF Image API uses a standardized URL pattern for requesting images:

```
http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/[image-path]/[region]/[size]/[rotation]/[quality].[format]
```

Examples:
- Full image (as JSON info): 
  ```
  http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/test_image.ptif/info.json
  ```
- 200px wide thumbnail: 
  ```
  http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/test_image.ptif/full/200,/0/default.jpg
  ```
- Region of the image (100,100 with width 200, height 200): 
  ```
  http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/test_image.ptif/100,100,200,200/full/0/default.jpg
  ```

## Common Challenges and Solutions

### Challenge 1: Missing PTIF Files

**Problem:** IIPServer returns an error: "file.ptif is neither a file nor part of an image sequence"

**Solution:**
1. Check if the PTIF file exists in the container:
   ```bash
   docker-compose exec iipserver ls -la /images/public/
   ```
2. Run the conversion script if needed:
   ```bash
   ./convert_images.sh
   ```
3. Copy PTIF files to the public directory:
   ```bash
   cp data/images/*.ptif data/images/public/
   ```

### Challenge 2: Missing the vips Tool

**Problem:** Error: "vips command not found"

**Solution:**
```bash
# On macOS
brew install vips

# On Ubuntu/Debian
sudo apt-get install -y libvips-tools
```

### Challenge 3: IIPServer Crashes with C++ Assertion Failures

**Problem:** IIPServer crashes with: "vector::_M_range_check: __n (which is X) >= this->size() (which is Y)"

**Solution:**
1. Restart the IIPServer:
   ```bash
   docker-compose restart iipserver
   ```
2. Try with a different image format or a different source image

### Challenge 4: Issues with Volume Mounting

**Problem:** Files exist on the host but aren't visible in the container

**Solution:**
1. Check volume configuration in docker-compose.yml
2. Check that local directories exist
3. Copy files manually to the container if needed:
   ```bash
   docker-compose cp data/images/test_image.ptif iipserver:/images/public/
   ```

## Conclusion

By implementing PTIF conversion, we've enabled the IIPServer to serve images via the IIIF protocol, which is essential for viewing images in IIIF-compatible viewers like Mirador.

Zenodo-RDM provides built-in tools for PTIF conversion, which is the preferred approach for a production environment. However, our custom solution can be useful for testing and development when you don't want to modify the core codebase.

Choose the approach that best fits your needs:
- **Custom Solution**: Simple, standalone, no code changes required
- **Built-in Tools**: Integrated, consistent with Zenodo's codebase 
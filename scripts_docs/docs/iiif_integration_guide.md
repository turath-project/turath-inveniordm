# IIIF Integration Guide for Zenodo RDM

This guide provides a comprehensive overview of the IIIF (International Image Interoperability Framework) integration in Zenodo RDM, explaining how the system works, available tools, and how to use them effectively.

## Table of Contents

1. [Introduction to IIIF in Zenodo RDM](#introduction)
2. [Architecture Overview](#architecture)
3. [Available Tools](#available-tools)
4. [Common Workflows](#common-workflows)
5. [Troubleshooting](#troubleshooting)
6. [Advanced Topics](#advanced-topics)
7. [Contributing](#contributing)

## Introduction

IIIF enables standardized delivery of images and their associated metadata. In Zenodo RDM, IIIF integration allows:

- Viewing high-resolution images with deep zoom capability
- Creating and accessing IIIF manifests for records
- Embedding images in external applications
- Annotating images

This integration requires coordination between several components:
- Zenodo RDM's record system
- IIPImage Server for image processing
- PTIF (Pyramid TIFF) image format
- IIIF manifest generation

## Architecture Overview

The IIIF implementation in Zenodo RDM follows this architecture:

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│  Zenodo RDM     │──────▶  IIPImage Server│──────▶  IIIF Client    │
│  (Records)      │      │  (Image Service)│      │  (Viewer)       │
│                 │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
        │                        ▲
        │                        │
        ▼                        │
┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │
│  File Storage   │──────▶  PTIF Images    │
│                 │      │                 │
└─────────────────┘      └─────────────────┘
```

Key components:
1. **Zenodo RDM**: Manages records and generates IIIF manifests
2. **IIPImage Server**: Serves image tiles and handles IIIF image API requests
3. **File Storage**: Contains original uploaded files
4. **PTIF Images**: Pyramid TIFF format optimized for deep zoom
5. **IIIF Client**: Any IIIF-compatible viewer (e.g., Mirador, Universal Viewer)

## Available Tools

We've developed several tools to streamline IIIF integration:

### Scripts

| Script | Description | Usage |
|--------|-------------|-------|
| `check_iiif.py` | Verifies IIIF functionality for a record | `make check-iiif RECORD=<id>` |
| `setup_iiif_for_record.sh` | Automates IIIF setup for a record | `make setup-iiif RECORD=<id>` |
| `convert_to_ptif.py` | Converts images to PTIF format | Used by setup script |
| `check_record.py` | Lists files in a record | `make check-record RECORD=<id>` |
| `get_file.py` | Downloads a file from a record | Used by setup script |

### Makefile Commands

| Command | Description | Example |
|---------|-------------|---------|
| `make help` | Shows available commands | `make help` |
| `make list` | Lists available scripts | `make list` |
| `make check-record` | Shows record information | `make check-record RECORD=123` |
| `make check-iiif` | Checks IIIF functionality | `make check-iiif RECORD=123` |
| `make setup-iiif` | Sets up IIIF for a record | `make setup-iiif RECORD=123` |
| `make docs` | Generates documentation | `make docs` |
| `make run-py` | Runs a Python script | `make run-py SCRIPT=check_iiif.py ARGS="123"` |
| `make run-sh` | Runs a shell script | `make run-sh SCRIPT=setup_iiif_for_record.sh ARGS="123"` |

## Common Workflows

### 1. Checking a Record's IIIF Status

To verify if a record has proper IIIF integration:

```bash
cd scripts/AlA
make check-iiif RECORD=123
```

This will:
- Check if the IIIF manifest exists
- Validate manifest structure
- Verify image info accessibility
- Check thumbnail generation

### 2. Setting Up IIIF for a New Record

To enable IIIF for a record with images:

```bash
cd scripts/AlA
make setup-iiif RECORD=123
```

This will:
1. Check record details and list files
2. Create necessary directories
3. Download image files
4. Convert images to PTIF format
5. Copy PTIF files to IIPImage Server
6. Verify IIIF manifest accessibility

### 3. Troubleshooting IIIF Issues

If encountering problems with IIIF:

1. Check record details:
   ```bash
   make check-record RECORD=123
   ```

2. Verify IIIF functionality:
   ```bash
   make check-iiif RECORD=123
   ```

3. If issues are found, reinstall IIIF:
   ```bash
   make setup-iiif RECORD=123
   ```

## Troubleshooting

Common issues and their solutions:

### Missing IIIF Manifest

**Problem**: IIIF manifest not accessible at `/api/iiif/record:<id>/manifest`

**Solution**:
1. Verify record exists and has image files
2. Check if PTIF files are properly installed
3. Run `make setup-iiif RECORD=<id>`

### IIIF Images Not Loading

**Problem**: Images fail to load in IIIF viewer

**Solution**:
1. Check IIPImage Server is running
2. Verify PTIF files exist in correct location
3. Confirm image service URLs are correctly formatted
4. Run `make check-iiif RECORD=<id>` to diagnose

### Incorrect Image Display

**Problem**: Images display incorrectly or with artifacts

**Solution**:
1. Check original image quality
2. Regenerate PTIF file using `make setup-iiif RECORD=<id>`
3. Verify conversion parameters in `convert_to_ptif.py`

## Advanced Topics

### Custom IIIF Manifest Generation

The default manifest generation can be customized:

1. Locate the manifest generation code in `invenio_app_rdm/records_ui/views/iiif.py`
2. Modify the manifest structure as needed
3. Test changes with `make check-iiif RECORD=<id>`

### Adding Support for New Image Formats

To support additional image formats:

1. Update the file detection in `setup_iiif_for_record.sh`
2. Add conversion support in `convert_to_ptif.py`
3. Test with sample files

## Contributing

To contribute improvements to the IIIF integration:

1. Fork the repository
2. Make your changes
3. Update documentation in `docs/iiif_integration_guide.md`
4. Submit a pull request

For any questions, refer to the detailed documentation:
- Script documentation: `scripts/AlA/README.md`
- Troubleshooting guide: `docs/iiif_troubleshooting.md`
- API documentation: `docs/scripts/README.md` 
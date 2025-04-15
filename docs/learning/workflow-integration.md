# Book Upload and IIIF Integration Workflow

This document explains the automated workflow for uploading digitized books to InvenioRDM and integrating them with IIIF for enhanced viewing capabilities.

## Overview

The workflow integration combines several separate processes into a single seamless flow:

1. **Upload a book** to InvenioRDM
2. **Copy the PDF** to Cantaloupe's image server
3. **Generate a IIIF manifest** pointing to the correct image server
4. **Update the InvenioRDM record** with the manifest

## Workflow Diagram

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐     ┌───────────────┐
│ Upload Book │ ──► │ Copy PDF to  │ ──► │ Generate IIIF  │ ──► │ Update Record │
│ to InvenioRDM│     │ Cantaloupe  │     │ Manifest      │     │ with Manifest │
└─────────────┘     └──────────────┘     └────────────────┘     └───────────────┘
```

## Components

### 1. Book Upload (InvenioRDM)

The script first uploads the book to InvenioRDM using the following process:

- Invokes the `upload_book.py` script
- Uploads PDF, HOCR files, and other related content
- Creates record metadata from manifest.json or directory structure
- Uploads all files and publishes the record (if specified)
- Returns the record ID for subsequent steps

### 2. PDF Copy to Cantaloupe

Once the book is uploaded to InvenioRDM, the PDF is copied to the Cantaloupe image server:

- Creates directory structure in Cantaloupe: `/cantaloupe_dir/private/record_id/`
- Copies the PDF to this location
- Verifies that Cantaloupe can access the PDF by checking the info URL
- Returns the PDF filename for the manifest generation step

### 3. IIIF Manifest Generation

The workflow then generates a IIIF manifest for the book:

- Uses existing manifest.json as a starting point (if available)
- Updates image URLs to point to Cantaloupe with the correct record ID
- Sets proper page references in the manifest
- Saves the updated manifest back to the book directory

### 4. Record Update with Manifest

Finally, the workflow updates the InvenioRDM record with the IIIF manifest:

- Uploads the manifest file to the InvenioRDM record
- Updates the record's metadata with IIIF manifest URL in custom fields
- Connects the InvenioRDM record with the IIIF viewer

## Usage

```bash
python workflow_integration.py --book-dir /path/to/book \
    --api-url https://inveniordm.example.com/api \
    --token YOUR_API_TOKEN \
    --cantaloupe-url https://cantaloupe.example.com/iiif/3
```

### Required Arguments

- `--book-dir`: Directory containing the book files
- `--token`: InvenioRDM API token

### Optional Arguments

- `--api-url`: InvenioRDM API URL (default: https://localhost:5000/api)
- `--cantaloupe-dir`: Cantaloupe data directory (default: /opt/cantaloupe/images)
- `--cantaloupe-url`: Cantaloupe server URL (default: https://localhost:8182)
- `--verify-ssl`: Verify SSL certificates (default: no verification)
- `--no-publish`: Keep the record as a draft
- `--verbose`: Enable verbose output

## Error Handling

The workflow includes robust error handling:

- Each step checks for success before proceeding to the next
- Detailed logging for troubleshooting
- Early exit if critical steps fail
- Verification of Cantaloupe access

## Implementation Details

The implementation uses:
- Python requests library for API interactions
- JSON manipulation for manifest updates
- Filesystem operations for copying PDFs
- Subprocess calls for invoking the upload script

## Expected Directory Structure

The workflow expects books to have the following structure:

```
book_id/
  ├── book_id.pdf (main PDF file)
  ├── manifest.json (metadata about the book)
  ├── hocr/ (directory with HOCR files for pages)
  └── pages/ (directory with TIFF images of pages)
```

## Integration with InvenioRDM

The workflow updates InvenioRDM records with:
- IIIF manifest URL in custom fields
- Uploaded manifest file for browser-side access
- Proper record metadata for discoverability

## Integration with Cantaloupe

The workflow ensures Cantaloupe can access the PDF by:
- Placing it in the correct directory structure
- Testing the IIIF info endpoint
- Setting the correct identifier in the manifest

## Configuration

The workflow can be configured through command-line arguments or environment variables:

- API endpoints for InvenioRDM and Cantaloupe
- Directory paths for input and output
- Authentication details
- SSL verification options

## Result

When the workflow completes successfully, you will have:
1. A published InvenioRDM record with all files
2. The PDF accessible via Cantaloupe's IIIF server
3. A IIIF manifest that connects the two systems
4. A rich viewing experience for end users 
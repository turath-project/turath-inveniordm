# Book Upload and IIIF Integration Workflow (Using `upload_book.py`)

This document explains the automated workflow for uploading digitized books to InvenioRDM and integrating them with IIIF for enhanced viewing capabilities, as handled by the **`scripts/upload_book.py`** script.

## Overview

The `upload_book.py` script consolidates several steps into a single process:

1.  **Collect Files:** Read PDF, HOCR, and metadata from a local book directory.
2.  **Create Record:** Create a draft record in InvenioRDM via API.
3.  **Upload Files:** Upload the collected files (PDF, HOCR, etc.) to the draft record.
4.  **Prepare IIIF Server Data:** Copy the primary PDF to Cantaloupe's image directory (`./cantaloupe-files`) and HOCR files to the shared service directory (`./hocr_mount`), if applicable.
5.  **Generate & Upload IIIF Manifest:** Construct a static IIIF manifest (`manifest.json`) containing links to Cantaloupe, annotation/search services, and Invenio files, then upload this manifest to the record.
6.  **Publish Record:** Publish the draft record.

## Workflow Diagram (Conceptual for `upload_book.py`)

```mermaid
graph TD
    A[Start upload_book.py] --> B(Collect Files);
    B --> C(Create Draft Record via API);
    C -- Record ID --> D(Upload Files via API);
    D --> E{Copy PDF to ./cantaloupe-files};
    D --> F{Copy HOCR to ./hocr_mount (if specified)};
    F --> G(Generate Static IIIF Manifest);
    E --> G;
    G --> H(Upload manifest.json via API);
    H --> I(Publish Record via API);
    I --> J[End];

    style A fill:#lightgrey,stroke:#333
    style J fill:#lightgrey,stroke:#333
```

## Components Involved

*   **`scripts/upload_book.py`:** The orchestrator script.
*   **Local Book Directory:** Contains source PDF, HOCR, `metadata.json`.
*   **InvenioRDM API:** Used for creating records, uploading files, publishing.
*   **Cantaloupe Image Server:** Reads PDFs from `./cantaloupe-files` to serve IIIF images.
*   **Annotation/Search Services:** Read HOCR from `./hocr_mount` to provide annotations/search.
*   **Nginx Proxy:** Routes public requests (`/annotations/`, `/search/`) to the correct internal services.
*   **Host Directories:**
    *   `./cantaloupe-files`: PDFs copied here for Cantaloupe access.
    *   `./hocr_mount`: HOCR files copied here for annotation/search service access.

## Integration Details

*   **InvenioRDM <-> Cantaloupe:** The `upload_book.py` script bridges this by:
    1.  Uploading the PDF to Invenio.
    2.  Copying the PDF (renamed with record ID) to `./cantaloupe-files`.
    3.  Generating manifest links pointing to Cantaloupe using the `{record_id}_{pdf_filename}` identifier.
*   **InvenioRDM <-> Annotation/Search Services:** The `upload_book.py` script bridges this by:
    1.  Uploading HOCR files to Invenio.
    2.  Copying HOCR files to `./hocr_mount/books/{book_id}/hocr/` (requires `--hocr-mount-point`).
    3.  Generating manifest links pointing to the Nginx proxy endpoints (`/annotations/`, `/search/`) which route to the services that read from the mount point.
*   **Manifest <-> Services:** The generated static `manifest.json` (uploaded to Invenio) contains the necessary URLs pointing to Cantaloupe (via `http://localhost:8182`) and the proxied annotation/search services (via `https://localhost`).

## Usage

The entire workflow is triggered by running the `upload_book.py` script:

```bash
pipenv run python scripts/upload_book.py \
    --book-dir /path/to/book \
    --api-url https://127.0.0.1:5000/api \
    --token YOUR_API_TOKEN \
    --hocr-mount-point ./hocr_mount \ # Essential for annotation/search
    --no-verify-ssl \
    --verbose \
    # Add --skip-tiff, --skip-hocr, or --pdf-only as needed
    # Add --no-publish or --draft to review before publishing
```

## Error Handling

The `upload_book.py` script includes error handling:

*   Retries file uploads (`--max-retries`).
*   Logs warnings and errors during metadata processing, file upload, manifest generation, and publishing.
*   Exits with non-zero status on critical failures.
*   File copying steps occur *after* successful Invenio uploads but before publishing.

## Configuration

Key configurations impacting this workflow:

*   **`upload_book.py` Arguments:** `--api-url`, `--token`, `--hocr-mount-point`, file skipping flags (`--skip-tiff`, etc.), `--no-verify-ssl`.
*   **`.env` file:** Provides `RDM_API_TOKEN` if `--token` isn't used.
*   **`docker-compose.yml`:** Defines volume mounts (`./cantaloupe-files`, `./hocr_mount`) and service configurations (Cantaloupe paths, service environment variables).
*   **`docker/nginx/nginx.conf`:** Defines proxy rules for `/annotations/` and `/search/`.
*   **Service Code (`services/*/app.py`):** Reads environment variables for base paths (`HOCR_BASE_DIR`) and URLs.

## Result

When the `upload_book.py` script completes successfully, you should have:

1.  A published (or draft) InvenioRDM record containing the PDF, HOCR (if not skipped), and the generated `manifest.json`.
2.  The primary PDF copied to `./cantaloupe-files` accessible by Cantaloupe.
3.  HOCR files copied to `./hocr_mount` accessible by annotation/search services (if `--hocr-mount-point` used).
4.  A static IIIF manifest available at `.../files/manifest.json/content` that correctly links all components for viewing via a IIIF client interacting with the Nginx frontend.

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
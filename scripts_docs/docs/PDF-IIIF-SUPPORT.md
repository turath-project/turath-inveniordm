# PDF Support in IIIF for Zenodo-RDM

This document explains how PDF files are supported in the IIIF implementation for Zenodo-RDM.

## Overview

PDF support is implemented using Cantaloupe, a powerful IIIF server that can render PDF files on-demand. This allows viewing PDFs page by page in a IIIF viewer without requiring pre-conversion to image files, while preserving text and other features of the original PDF.

## Architecture

### Components

1. **Cantaloupe Server**: A Java-based IIIF image server that supports PDFs natively
2. **CantaloupeProxy**: A custom proxy class that routes IIIF requests for PDFs to Cantaloupe
3. **PDFBoxProcessor**: The processor within Cantaloupe that renders PDF pages to images

### Data Flow

1. User requests to view a PDF through the IIIF viewer
2. IIIF manifest includes canvas entries for each PDF page
3. Canvas image annotations point to the Cantaloupe service with appropriate page parameters
4. When the viewer requests an image, the request is:
   - Routed through the CantaloupeProxy
   - Forwarded to the Cantaloupe server
   - Processed by PDFBoxProcessor to render the specific page
   - Returned as an image in the requested format and size

## Configuration

### Docker Setup

The Cantaloupe server is configured in `docker-compose.yml`:

```yaml
cantaloupe:
  image: edirom/cantaloupe
  platform: linux/amd64  # Important for M1/M2 Mac
  restart: "unless-stopped"
  ports:
    - "8182:8182"
  environment:
    - CANTALOUPE_ENDPOINT_ADMIN_ENABLED=true
    - CANTALOUPE_ENDPOINT_ADMIN_SECRET=your_secret_here
    - CANTALOUPE_FILESYSTEM_RESOLVER_LOOKUP_STRATEGY_PATH_PREFIX=/opt/cantaloupe/images
    - CANTALOUPE_SOURCE_STATIC=FilesystemSource
    - CANTALOUPE_PROCESSOR_PDF=PdfBoxProcessor
  volumes:
    - ./data/records:/opt/cantaloupe/images/records
    - ./data/images/private:/opt/cantaloupe/images/private
    - ./test_data:/opt/cantaloupe/images/test
```

### Cantaloupe Configuration

Key configuration settings for PDF support:

```properties
# Enable PDF processor
processor.pdf = PdfBoxProcessor

# Resolution for PDF rendering
PDFBoxProcessor.dpi = 150

# Path to temp directory
PDFBoxProcessor.path_to_temp_dir = /var/cache/cantaloupe
```

### Application Configuration

In `invenio.cfg`:

```python
# Use Cantaloupe for IIIF
IIIF_PROXY_CLASS = CantaloupeProxy

# Cantaloupe server URL
RDM_IIIF_SERVER_URL = "http://127.0.0.1:8182"

# Add PDF to supported formats
RDM_IIIF_MANIFEST_FORMATS = ["jpeg", "jpg", "png", "tiff", "tif", "pdf"]
```

## URL Structure

### PDF Info Endpoint

```
http://localhost:8182/iiif/2/images%2Fprivate%2F<record_id>%2F<filename>.pdf/info.json
```

### PDF Page Rendering

```
http://localhost:8182/iiif/2/images%2Fprivate%2F<record_id>%2F<filename>.pdf/full/full/0/default.jpg?page=<page_number>
```

### PDF Thumbnails

```
http://localhost:8182/iiif/2/images%2Fprivate%2F<record_id>%2F<filename>.pdf/full/200,/0/default.jpg?page=<page_number>
```

## Implementation Details

### CantaloupeProxy Class

The `CantaloupeProxy` class in `site/zenodo_rdm/iiif/proxy.py` handles routing IIIF requests to the appropriate server:

- Identifies PDF files by their extension
- Constructs the correct Cantaloupe URL for PDF files
- Handles the `page` parameter to specify which page to render
- Forwards the request and returns the response

### Manifest Generation

PDF files are included in IIIF manifests by:

1. Adding "pdf" to the `RDM_IIIF_MANIFEST_FORMATS` configuration
2. Using the proxy URL structure in the IIIF manifest's image annotations
3. Adding the `page` parameter to specify the page number

## Testing

A test script is provided at `test/test_cantaloupe_pdf.py` to verify that PDF rendering is working correctly:

```bash
python test/test_cantaloupe_pdf.py --record <record_id> --file <filename.pdf>
```

The script tests:
- Retrieving PDF metadata via info.json
- Rendering a full page
- Generating a thumbnail
- Saving output files for inspection

## Advantages Over Image Extraction

Direct PDF rendering has several advantages over extracting images from PDFs:

1. **Simplicity**: No need for a separate conversion process
2. **Maintenance**: When PDFs are updated, the changes are immediately visible
3. **Storage Efficiency**: No duplicate storage of extracted images
4. **Text Preservation**: Text layers in PDFs remain accessible
5. **Quality**: High-quality rendering at the requested resolution
6. **Flexibility**: Access to all pages without pre-conversion

## Troubleshooting

### Common Issues

1. **PDF Not Found**: Ensure the PDF file exists at the expected path
2. **Incorrect Page Parameter**: The `page` parameter is 1-based (first page is 1, not 0)
3. **Permission Issues**: Check that Cantaloupe has read access to the PDF files
4. **Memory Issues**: Large PDFs may require more memory for rendering

### Debugging

1. Test direct access to Cantaloupe using the test script
2. Check Cantaloupe logs for errors:
   ```bash
   docker-compose logs cantaloupe
   ```
3. Verify PDF files are accessible within the container:
   ```bash
   docker-compose exec cantaloupe find /opt/cantaloupe/images -name "*.pdf"
   ```

## Limitations

1. **Performance**: Rendering large PDFs may be slower than pre-converted images
2. **Memory Usage**: PDF rendering can be memory-intensive for complex PDFs
3. **Font Issues**: Some PDFs with unusual fonts may not render correctly 
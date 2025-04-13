# IIIF Integration for Zenodo-RDM

This document outlines the implementation and usage of IIIF (International Image Interoperability Framework) integration for Zenodo-RDM.

## Overview

The integration enables viewing high-resolution images through IIIF, allowing users to zoom, pan, and annotate images directly in the browser. This implementation uses:

1. **IIPServer** - A Fast CGI server for serving high-resolution IIIF images from PTIF files
2. **Cantaloupe** - A IIIF server with PDF rendering capabilities
3. **PTIF format** - Pyramid TIFF format for efficient image tiling and multi-resolution access
4. **Mirador** - A configurable, extensible, and easy-to-integrate IIIF viewer

## Components

### IIPServer

IIPServer is deployed as a Docker container and configured to serve IIIF-compliant images. The server looks for images in the `/images/public` directory within the container.

### Cantaloupe 

Cantaloupe is used to serve PDF files directly via IIIF without requiring conversion to image formats. It supports:

1. PDF page extraction
2. Text layer preservation
3. On-demand rendering of PDF pages at different scales
4. All IIIF Image API operations on PDF pages

The Cantaloupe server is configured to look for files in the `/opt/cantaloupe/images` directory, with PDFs stored in `images/private/<record_id>/` and images in their partitioned format.

### Image Conversion

Images are converted from standard formats (TIFF, JPG, PNG) to PTIF format using the Kakadu JPEG2000 library's `kdu_compress` tool. The conversion process is handled by:

1. `convert_to_ptif.py` - Converts a single image file to PTIF format
2. `batch_convert.py` - Batch processes all image files within a specific record

## Using the Tools

### Single File Conversion

To convert a single image file to PTIF format:

```bash
python convert_to_ptif.py [input_file_path] [record_id]
```

Example:
```bash
python convert_to_ptif.py data/images/private/202/page-001.tif 202
```

### Batch Conversion

To convert all image files within a record:

```bash
python batch_convert.py [record_id]
```

Example:
```bash
python batch_convert.py 202
```

## File Naming and Storage

- Original image files are stored in `data/images/private/[record_id]/`
- PTIF files must be placed in the IIPServer's accessible location, which is mapped to `/images/public/` in the container
- PDF files are kept in their original location and rendered on-demand by Cantaloupe
- The naming convention for IIIF URLs is `private_[record_id]_[filename]` (e.g., `private_202_page-001.ptif`)

## IIIF URLs

After conversion, images are accessible through IIIF at the following URLs:

### Images (via IIPServer)

- Metadata: `http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/private_[record_id]_[filename].ptif/info.json`
- Thumbnail: `http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/private_[record_id]_[filename].ptif/full/200,/0/default.jpg`
- Image region: `http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/private_[record_id]_[filename].ptif/0,0,100,100/full/0/default.jpg`

Example for record 202, file page-001.tif:
```
http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/private_202_page-001.ptif/info.json
```

### PDFs (via Cantaloupe)

- Metadata: `http://localhost:8182/iiif/2/images%2Fprivate%2F[record_id]%2F[filename].pdf/info.json`
- Full page: `http://localhost:8182/iiif/2/images%2Fprivate%2F[record_id]%2F[filename].pdf/full/full/0/default.jpg?page=[page_number]`
- Thumbnail: `http://localhost:8182/iiif/2/images%2Fprivate%2F[record_id]%2F[filename].pdf/full/200,/0/default.jpg?page=[page_number]`

Example for record 202, file document.pdf, page 1:
```
http://localhost:8182/iiif/2/images%2Fprivate%2F202%2Fdocument.pdf/full/full/0/default.jpg?page=1
```

## PDF Support

One of the key features of this integration is native PDF support through Cantaloupe. This allows:

1. Viewing PDFs page by page in a IIIF viewer
2. Preserving text selection and search in the original PDF
3. Supporting large PDF files efficiently
4. No need for extracting and converting each page to images

### Testing PDF Rendering

A test script is provided to verify PDF rendering through Cantaloupe:

```bash
python test/test_cantaloupe_pdf.py --record 202 --file document.pdf
```

This will:
1. Test retrieval of PDF metadata
2. Test rendering of the first page
3. Test thumbnail generation
4. Save sample outputs for inspection

## Troubleshooting

### Common Issues

If you encounter issues with image or PDF viewing, check the following:

1. Verify the file exists in the expected location
2. Check server logs for error messages
3. Ensure CORS is properly configured for cross-origin access
4. Test direct access to the server URLs before testing through the application

## Known Limitations

1. The IIIF manifest endpoint (`/iiif/[record_id]/manifest`) is not currently working properly in Zenodo-RDM
2. External viewers may need to be configured to access individual image files rather than the manifest

## Future Improvements

1. Fix the manifest endpoint to properly serve IIIF manifests
2. Implement automatic PTIF conversion upon file upload
3. Support annotation storage and retrieval
4. Add configuration options for IIIF presentation API 
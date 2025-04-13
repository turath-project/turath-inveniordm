# Cantaloupe PDF Viewing - Working Configuration

This document outlines the current working configuration for viewing PDFs with Cantaloupe in Zenodo-RDM.

## Current Setup

The Cantaloupe server is running in a Docker container with the following:

- Port: 8182
- Container ID: 68ffede5523e (as previously observed)
- Image: edirom/cantaloupe

## File Locations

We have verified that files are accessible in the following paths:

- Within container: `/opt/cantaloupe/images/images/private/<record_id>/`
- Host path mapping: `./data/images/private/<record_id>/`

For example, we confirmed the PDF file exists at:
```
/opt/cantaloupe/images/images/private/202/history00871.pdf
```

## Working URLs

The following URL formats have been tested and confirmed working:

### For PDF Info:
```
http://localhost:8182/iiif/2/images%2Fprivate%2F202%2Fhistory00871.pdf/info.json
```

### For rendering a specific PDF page as an image:
```
http://localhost:8182/iiif/2/images%2Fprivate%2F202%2Fhistory00871.pdf/full/full/0/default.jpg?page=1
```

### For thumbnails:
```
http://localhost:8182/iiif/2/images%2Fprivate%2F202%2Fhistory00871.pdf/full/200,/0/default.jpg?page=1
```

## Important Notes

1. The file path format in the URL is:
   - `images%2Fprivate%2F<record_id>%2F<filename>.pdf`
   - The slashes must be URL-encoded as `%2F`

2. For PDFs, the page parameter is required:
   - `?page=1` specifies the first page (pages are 1-indexed)
   - Without this parameter, the request will fail

3. Cantaloupe environment variables:
   - `CANTALOUPE_SOURCE_STATIC=FilesystemSource`
   - `CANTALOUPE_PROCESSOR_PDF=PdfBoxProcessor`
   - Path prefix: `/opt/cantaloupe/images`

4. Docker volume mapping in docker-compose.yml:
   ```yaml
   volumes:
     - ./data/records:/opt/cantaloupe/images/records
     - ./data/images:/opt/cantaloupe/images/images
   ```

## Testing Commands

These commands have been verified to work:

### Check if Cantaloupe is running:
```bash
docker ps | grep cantaloupe
```

### Test Cantaloupe server directly:
```bash
curl -I http://localhost:8182/iiif/3
```

### Check for PDF files in the container:
```bash
docker-compose exec cantaloupe ls -la /opt/cantaloupe/images/images/private/202/
```

### Download a PDF page as JPEG:
```bash
curl "http://localhost:8182/iiif/2/images%2Fprivate%2F202%2Fhistory00871.pdf/full/full/0/default.jpg?page=1" -o test_page1.jpg
```

## Next Steps

For the integration with Zenodo-RDM, we'll need to:

1. Implement a proxy that can translate incoming requests to the correct Cantaloupe URL format
2. Add PDF to the list of supported formats in the configuration
3. Update IIIF manifest generation to handle PDFs appropriately

These steps have not yet been implemented or tested. 
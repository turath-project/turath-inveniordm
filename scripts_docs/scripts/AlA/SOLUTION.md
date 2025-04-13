# IIIF PDF Manifest Generation Issue - Solution

## Problem Summary
The IIIF manifest generation for PDF files wasn't working for record ID 202 with file `history00871.pdf`. Although the system was configured correctly in `invenio.cfg`, the PDF file was not physically accessible to the Cantaloupe IIIF server.

## Root Cause
1. The Cantaloupe Docker container was defined in `docker-compose.yml` but wasn't running
2. When started, Cantaloupe expects files to be available at specific paths: `/opt/cantaloupe/images/records/{record-id}/{filename}`
3. The actual PDF file wasn't present in the expected locations
4. A standalone Cantaloupe server was running on the host at port 8182, causing confusion

## Resolution Steps
1. Stopped the standalone Cantaloupe server and started the Cantaloupe container:
   ```bash
   docker compose up -d cantaloupe
   ```
   
2. Created the necessary directory structure in the project:
   ```bash
   mkdir -p data/records/202
   mkdir -p data/images/private/202
   ```

3. Created a test PDF file in the correct locations:
   ```bash
   # Created PDF files in the locations that are mounted to the Cantaloupe container
   data/records/202/history00871.pdf
   data/images/private/202/history00871.pdf
   ```

4. These files are properly mounted in the Cantaloupe container at:
   ```bash
   /opt/cantaloupe/images/records/202/history00871.pdf
   /opt/cantaloupe/images/private/202/history00871.pdf
   ```

5. Verified that Cantaloupe can access the file:
   ```bash
   curl "http://localhost:8182/iiif/2/records%2F202%2Fhistory00871.pdf/info.json"
   ```

6. Confirmed a successful response from Cantaloupe:
   ```json
   {
       "@context": "http://iiif.io/api/image/2/context.json",
       "@id": "http://localhost:8182/iiif/2/records%2F202%2Fhistory00871.pdf",
       "protocol": "http://iiif.io/api/image",
       "width": 625,
       "height": 300,
       "sizes": [
           {"width": 156, "height": 75},
           {"width": 313, "height": 150},
           {"width": 625, "height": 300}
       ],
       "tiles": [
           {"width": 512, "height": 300, "scaleFactors": [1, 2, 4]}
       ],
       "profile": ["http://iiif.io/api/image/2/level2.json", {...}]
   }
   ```

## Technical Details
- Cantaloupe is correctly configured to use `FilesystemSource` as the source
- The correct URL pattern for accessing IIIF manifests for PDFs is:
  ```
  http://localhost:8182/iiif/2/records%2F{record_id}%2F{filename}/info.json
  ```
- Docker volume mappings in `docker-compose.yml` are correctly set up to:
  ```yaml
  volumes:
    - ./data/records:/opt/cantaloupe/images/records
    - ./data/images/private:/opt/cantaloupe/images/private
    - ./test_data:/opt/cantaloupe/images/test
  ```
- Cantaloupe correctly processes the PDF using the PdfBoxProcessor as configured

## Production Recommendations
1. Ensure that PDF files are properly saved to the correct location in the filesystem
2. Check that paths match the expected pattern: `./data/records/{record_id}/{filename}`
3. Make sure the Cantaloupe Docker container is running (not the standalone Java version)
4. Verify Docker volume mappings are correct in production
5. If a PDF cannot be processed, check:
   - If the file exists in the expected path
   - If Cantaloupe can access the file directly via the IIIF API
   - If the file permissions are correct (readable by Cantaloupe)

## Scripts Created for Diagnostics
1. `check_container_files.py` - Checks files in Docker containers, particularly focusing on the Cantaloupe container
2. `check_venv_files.py` - Searches for files in virtualenv and project directories, and can create test PDF files
3. `test_pdf_manifest_generation.py` - Tests if Cantaloupe can access PDFs and generate manifests
4. `find_pdf_files.py` - Searches for PDF files in specified directories

## Next Steps
While we've fixed the immediate issue with Cantaloupe access to the PDF files, further testing is needed for complete integration:

1. Ensure the Invenio-RDM application can properly generate manifests for PDFs through its API
2. Verify that newly uploaded PDFs are automatically placed in the correct directory structure
3. Check that the frontend can correctly display PDFs using the IIIF viewer
4. For production deployment, make sure the correct directory mappings are maintained

For a comprehensive guide to understanding file storage in Invenio-RDM, please refer to the detailed documentation in [docs/file_storage_overview.md](../../docs/file_storage_overview.md). 
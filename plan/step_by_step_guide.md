# Step-by-Step Guide: PDF Book Upload to IIIF Viewer

This guide provides detailed steps for implementing the workflow to upload a PDF book, generate a IIIF manifest, and view it page by page using the Mirador viewer.

## Prerequisites

- InvenioRDM instance running
- Cantaloupe IIIF server running with HTTPS enabled
- Access to the book directory with PDF and optionally HOCR files
- API token for InvenioRDM

## Step 1: Book Upload

1. **Prepare your book directory**:
   ```
   book_directory/
   ├── book.pdf            # Primary content (required)
   ├── hocr/               # Directory containing HOCR files (optional)
   │   ├── 001.hocr
   │   ├── 002.hocr
   │   └── ...
   └── pages/              # Directory containing TIFF images (optional)
       ├── 001.tif
       ├── 002.tif
       └── ...
   ```

2. **Generate an API token**:
   ```bash
   ./scripts/generate_api_token.sh --user admin@test.com
   ```

3. **Upload the book**:
   ```bash
   python scripts/upload_book.py \
     --book-dir /path/to/book_directory \
     --api-url https://inveniordm.yourdomain.com/api \
     --token YOUR_API_TOKEN
   ```

4. **Note the record ID**:
   - The upload script will output a record ID like `abc-123-xyz`
   - Save this ID for the next steps

## Step 2: Generate IIIF Manifest

1. **Generate a basic manifest**:
   ```bash
   python scripts/generate_manifest.py \
     --book-dir /path/to/book_directory \
     --iiif-server https://cantaloupe.yourdomain.com/iiif/3 \
     --manifest-server https://inveniordm.yourdomain.com \
     --auto-scale
   ```

2. **Test the manifest with a validator**:
   - Use the IIIF Validator: https://iiif.io/api/presentation/validator/
   - Upload the generated manifest.json to validate its structure

3. **Update manifest with record ID**:
   - Manually edit the manifest.json file or modify the script to replace:
     - `{book_id}` with the actual record ID from Step 1
     - Update all URLs to use the correct record ID

## Step 3: Upload Manifest to InvenioRDM

1. **Update the record with the manifest**:
   ```bash
   python scripts/update_record_with_manifest.py \
     --record-id abc-123-xyz \
     --manifest-file /path/to/book_directory/manifest.json \
     --api-url https://inveniordm.yourdomain.com/api \
     --token YOUR_API_TOKEN
   ```

2. **Verify the manifest is accessible**:
   - Visit `https://inveniordm.yourdomain.com/api/records/abc-123-xyz/files/manifest.json`
   - Check that it loads and contains proper HTTPS URLs

## Step 4: Test IIIF Image Server Access

1. **Test direct access to the PDF pages via Cantaloupe**:
   ```
   https://cantaloupe.yourdomain.com/iiif/3/abc-123-xyz.pdf/full/full/0/default.jpg?page=1
   ```

2. **Debug image server issues**:
   - Check the Cantaloupe logs for any errors
   - Verify that Cantaloupe can access the PDF file
   - Test with different page numbers

## Step 5: View in Mirador

1. **Access the record in InvenioRDM**:
   - Go to `https://inveniordm.yourdomain.com/records/abc-123-xyz`

2. **Open the IIIF viewer**:
   - Click on the "View in IIIF Viewer" button
   - Mirador should load with your book

3. **Test navigation**:
   - Try changing pages
   - Test zooming functionality
   - Check that text highlighting works if HOCR files are provided

## Step 6: Automate the Workflow

1. **Create an end-to-end script**:
   ```python
   # workflow.py
   
   import os
   import sys
   import subprocess
   import json
   
   def upload_book_and_generate_manifest(book_dir, api_url, token):
       # Step 1: Upload book
       upload_cmd = [
           'python', 'scripts/upload_book.py',
           '--book-dir', book_dir,
           '--api-url', api_url,
           '--token', token
       ]
       
       result = subprocess.run(upload_cmd, capture_output=True, text=True)
       
       if result.returncode != 0:
           print(f"Error uploading book: {result.stderr}")
           return False
           
       # Extract record ID from output
       output = result.stdout
       # Parse output to find record ID
       record_id = extract_record_id(output)
       
       # Step 2: Generate manifest
       manifest_cmd = [
           'python', 'scripts/generate_manifest.py',
           '--book-dir', book_dir,
           '--iiif-server', 'https://cantaloupe.yourdomain.com/iiif/3',
           '--manifest-server', api_url.split('/api')[0],
           '--auto-scale'
       ]
       
       manifest_result = subprocess.run(manifest_cmd, capture_output=True, text=True)
       
       if manifest_result.returncode != 0:
           print(f"Error generating manifest: {manifest_result.stderr}")
           return False
           
       # Step 3: Update manifest with record ID
       manifest_path = os.path.join(book_dir, 'manifest.json')
       update_manifest_with_record_id(manifest_path, record_id)
       
       # Step 4: Upload manifest to record
       update_cmd = [
           'python', 'scripts/update_record_with_manifest.py',
           '--record-id', record_id,
           '--manifest-file', manifest_path,
           '--api-url', api_url,
           '--token', token
       ]
       
       update_result = subprocess.run(update_cmd, capture_output=True, text=True)
       
       if update_result.returncode != 0:
           print(f"Error updating record with manifest: {update_result.stderr}")
           return False
           
       print(f"Success! Record ID: {record_id}")
       print(f"View at: {api_url.split('/api')[0]}/records/{record_id}")
       
       return True
   ```

2. **Run the automated workflow**:
   ```bash
   python workflow.py --book-dir /path/to/book --api-url https://inveniordm.yourdomain.com/api --token YOUR_TOKEN
   ```

## Troubleshooting Common Issues

### 1. Manifest Not Loading in Mirador

- Check browser console for CORS errors
- Verify all URLs in the manifest use HTTPS
- Make sure Cantaloupe is accessible from the browser

### 2. Pages Not Rendering Correctly

- Test the Cantaloupe URL directly in the browser
- Check that the PDF format is supported
- Verify permissions and access to the PDF file

### 3. Text Highlighting Issues

- Check scale factor calculations
- Validate HOCR file format
- Test with different browsers

### 4. InvenioRDM Integration Issues

- Verify the record exists
- Check that the manifest file was properly uploaded
- Ensure the InvenioRDM viewer is configured to use IIIF
- Verify the custom field for the IIIF manifest is set correctly

## Next Steps After Implementation

1. **Performance optimization**:
   - Consider caching strategies for PDF pages
   - Optimize manifest for large books

2. **Enhanced features**:
   - Add annotation support
   - Implement text search if HOCR files are available
   - Add metadata display in the viewer

3. **Production deployment**:
   - Update all URLs to use production hostnames
   - Configure proper HTTPS certificates
   - Set up monitoring and logging 
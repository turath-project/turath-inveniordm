# Zenodo-RDM Scripts for IIIF and File Storage Integration

These scripts help troubleshoot and test file storage and IIIF integration in Invenio-RDM.

## Scripts

### analyze_file_storage.py

Analyzes file storage in Invenio-RDM.

```bash
pipenv run invenio shell -c "exec(open('scripts/AlA/analyze_file_storage.py').read())"
```

Provides insights into:
- Database structure
- Physical file locations
- Cantaloupe accessibility

### check_container_files.py

Checks files in Docker containers, specifically for the Cantaloupe container.

```bash
pipenv run invenio shell -c "exec(open('scripts/AlA/check_container_files.py').read())"
```

Options:
- `--record-id=RECORD_ID`: Record ID to check
- `--filename=FILENAME`: Filename to look for

### check_venv_files.py

Searches for files in virtual environments and project directories.

```bash
pipenv run invenio shell -c "exec(open('scripts/AlA/check_venv_files.py').read())"
```

Options:
- `--create-test-file`: Create a test file in the instance directory

### find_pdf_files.py

Searches for PDF files in the instance directory.

```bash
pipenv run python scripts/AlA/find_pdf_files.py
```

### find_tif_files.py

Searches for TIF/TIFF files in database records.

```bash
pipenv run invenio shell -c "exec(open('scripts/AlA/find_tif_files.py').read())"
```

### test_pdf_manifest_generation.py

Tests PDF manifest generation through the API.

```bash
pipenv run invenio shell -c "exec(open('scripts/AlA/test_pdf_manifest_generation.py').read())"
```

Options:
- `--record-id=RECORD_ID`: Record ID to use
- `--filename=FILENAME`: Filename to use

### check_record_files.py

Checks file information for a specific record.

```bash
pipenv run invenio shell -c "exec(open('scripts/AlA/check_record_files.py').read()) RECORD_ID"
```

### fix_cantaloupe_path.py

Fixes file paths for Cantaloupe by copying files to expected locations.

```bash
pipenv run python scripts/AlA/fix_cantaloupe_path.py RECORD_ID FILENAME
```

### test_iiif_integration.py

Tests the complete IIIF PDF integration workflow:
1. Checks configuration settings
2. Uploads a test PDF to a record
3. Verifies the PDF is accessible via Cantaloupe
4. Tests generating a manifest for the PDF
5. Tests accessing individual pages of the PDF

```bash
pipenv run invenio shell -c "exec(open('scripts/AlA/test_iiif_integration.py').read())"
```

Options:
- `--record-id=RECORD_ID`: Use an existing record ID (default: create new record)
- `--pdf=FILE`: Path to PDF file to upload (default: create test PDF)
- `--pages=NUM`: Number of pages in test PDF (default: 3)

### sync_files_to_cantaloupe.py

Syncs PDF files from Invenio to the Cantaloupe directory structure.

```bash
pipenv run python scripts/AlA/sync_files_to_cantaloupe.py [--record-id=RECORD_ID] [--cantaloupe-dir=/path/to/dir]
```

Options:
- `--record-id=RECORD_ID`: Sync files for specific record ID (default: all records)
- `--cantaloupe-dir=DIR`: Cantaloupe directory (default: /opt/cantaloupe/images)

### run_pdf_iiif.py

Generates a test PDF, uploads it to a record, and configures IIIF integration:

```bash
pipenv run invenio shell -c "exec(open('scripts/AlA/run_pdf_iiif.py').read())"
```

Options:
- `RECORD_ID`: Record ID to use
- `FILENAME`: Filename for the PDF (default: test.pdf)
- `PAGES`: Number of pages in test PDF (default: 3)

### run_iiif_server.py

Runs a simple Flask server with IIIF integration for testing:

```bash
python scripts/AlA/run_iiif_server.py
```

Features:
- Creates a test PDF file
- Simulates Invenio API endpoints
- Integrates simple IIIF extension
- Serves files at http://127.0.0.1:5000

### register_zenodo_extension.py

Registers the ZenodoRDM extension and checks IIIF configuration:

```bash
pipenv run invenio shell -c "exec(open('scripts/AlA/register_zenodo_extension.py').read())"
```

Features:
- Checks if ZenodoRDM extension is registered
- Registers the extension if needed
- Verifies IIIF configuration settings
- Checks IIIF resource routes

## Common Usage Patterns

### Troubleshooting IIIF PDF Access

1. Check configuration:
   ```bash
   pipenv run invenio shell -c "exec(open('scripts/AlA/check_iiif_pdf_config.py').read())"
   ```

2. Test IIIF integration:
   ```bash
   pipenv run invenio shell -c "exec(open('scripts/AlA/test_iiif_integration.py').read())"
   ```

3. If needed, fix Cantaloupe paths:
   ```bash
   pipenv run python scripts/AlA/fix_cantaloupe_path.py RECORD_ID FILENAME
   ```

4. Sync all files to Cantaloupe:
   ```bash
   pipenv run python scripts/AlA/sync_files_to_cantaloupe.py
   ```

5. Register Zenodo extensions:
   ```bash
   pipenv run invenio shell -c "exec(open('scripts/AlA/register_zenodo_extension.py').read())"
   ```

### Analyzing File Storage

1. Find all PDF files:
   ```bash
   pipenv run python scripts/AlA/find_pdf_files.py
   ```

2. Find all TIF/TIFF files:
   ```bash
   pipenv run invenio shell -c "exec(open('scripts/AlA/find_tif_files.py').read())"
   ```

3. Check specific record files:
   ```bash
   pipenv run invenio shell -c "exec(open('scripts/AlA/check_record_files.py').read()) RECORD_ID"
   ```

4. Analyze file storage:
   ```bash
   pipenv run invenio shell -c "exec(open('scripts/AlA/analyze_file_storage.py').read())"
   ```

### Testing Outside Invenio

Run a standalone IIIF test server:
```bash
python scripts/AlA/run_iiif_server.py
```

## Documentation

For more information, see the [Invenio-RDM documentation](https://inveniordm.docs.cern.ch/) and [IIIF documentation](https://iiif.io/documentation/). 
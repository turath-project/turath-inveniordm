# Understanding File Storage in Invenio-RDM

## Introduction

This document describes how files are stored in the Invenio-RDM system, particularly for PDF files that need to be accessed by the Cantaloupe IIIF server. It explains the file storage flow, directory structure, and integration with the Docker containers.

## File Storage Architecture

Invenio-RDM uses a multi-layered approach to file storage:

1. **Database Layer**: Records metadata and file relationships
2. **Physical Storage**: Where actual files are stored on disk
3. **Symlink Layer**: Maps files to record-specific paths for easier access
4. **Container Mounts**: Makes files available to service containers (e.g., Cantaloupe)

## Database Structure

The database maintains the relationship between records and files through several tables:

| Entity | Purpose | Example |
|--------|---------|---------|
| `Location` | Defines the physical storage location | `file:///opt/invenio/var/instance/data` |
| `Bucket` | Container for files (each record has a bucket) | UUID-based identifier |
| `ObjectVersion` | Represents a file version in a bucket | Links file to bucket with a key |
| `FileInstance` | References the actual file content | Hash-based storage paths |

## Physical Storage Paths

Files are physically stored in the following locations:

1. **Internal Storage** (database-managed):
   ```
   {instance_path}/data/{bucket-uuid}/{file-hash}
   ```
   
2. **Record-specific Access Path** (symlinked):
   ```
   {instance_path}/data/records/{record-id}/{filename}
   ```

In a development environment, this translates to:
- Internal: `/Users/alaabarazi/Projects/Turath/Coding/zenodo-rdm/.venv/var/instance/data/{bucket-uuid}/{file-hash}`
- Record: `/Users/alaabarazi/Projects/Turath/Coding/zenodo-rdm/data/records/{record-id}/{filename}`

In production, paths would typically be:
- Internal: `/opt/invenio/var/instance/data/{bucket-uuid}/{file-hash}`
- Record: `/opt/invenio/var/instance/data/records/{record-id}/{filename}`

## Docker Container Integration

The Docker Compose configuration maps these paths to make files accessible to services:

```yaml
volumes:
  - ./data/records:/opt/cantaloupe/images/records
  - ./data/images/private:/opt/cantaloupe/images/private
  - ./test_data:/opt/cantaloupe/images/test
```

This allows the Cantaloupe IIIF server to access files at the following paths inside the container:
- `/opt/cantaloupe/images/records/{record-id}/{filename}`
- `/opt/cantaloupe/images/private/{record-id}/{filename}`

## File Upload Flow

When a user uploads a file to a record, the following happens:

1. The file is temporarily stored in memory or a temporary location
2. A FileInstance is created with a hash-based filename in the internal storage
3. An ObjectVersion is created to link the file to the record's bucket
4. The system may create a symlink in the record-specific path for easier access

## Cantaloupe IIIF Access

To access files via the IIIF protocol, Cantaloupe uses the following URL patterns:

```
http://localhost:8182/iiif/2/records%2F{record_id}%2F{filename}/info.json
http://localhost:8182/iiif/2/private%2F{record_id}%2F{filename}/info.json
http://localhost:8182/iiif/2/{record_id}%2F{filename}/info.json
```

Cantaloupe resolves these paths to the mounted volumes in the container at:
- `/opt/cantaloupe/images/records/{record_id}/{filename}`
- `/opt/cantaloupe/images/private/{record_id}/{filename}`

## Relationship with IIIF Manifest Generation

For PDF files, the IIIF manifest generation depends on Cantaloupe being able to access the file. The process works as follows:

1. When a user requests a IIIF manifest for a record with PDF files, Invenio-RDM calls the `generate_pdf_manifest` function
2. This function constructs a manifest that references the PDF via Cantaloupe's IIIF API
3. Cantaloupe must be able to access the PDF file at the path it expects
4. The manifest references pages of the PDF as canvases in the IIIF presentation model

## Common Issues and Solutions

### 1. Missing Files in Record Directories

**Issue**: Files are uploaded and exist in the database/internal storage but are not visible in the record-specific path.

**Solution**:
- Manually create the record directory: `mkdir -p data/records/{record-id}`
- Copy the file to the record directory: `cp source_file data/records/{record-id}/{filename}`

### 2. Cantaloupe Cannot Access Files

**Issue**: Cantaloupe returns 404 errors when trying to access files.

**Solution**:
- Ensure the Cantaloupe container is running: `docker compose up -d cantaloupe`
- Verify the file exists in the proper path: `ls -la data/records/{record-id}/{filename}`
- Check if the file is accessible at: `http://localhost:8182/iiif/2/records%2F{record_id}%2F{filename}/info.json`

### 3. PDF Files Not Generating IIIF Manifests

**Issue**: PDF files uploaded to records don't generate IIIF manifests.

**Solution**:
- Ensure `RDM_IIIF_PDF_SUPPORT = True` is set in `invenio.cfg`
- Add `pdf` to `RDM_IIIF_MANIFEST_FORMATS`
- Make sure the PDF file is present in both the database and the record-specific path
- Verify that Cantaloupe can access the PDF file through its IIIF API

## Diagnostic Tools

### 1. analyze_file_storage.py

This script examines the file storage in Invenio-RDM and checks for issues:

```bash
python scripts/AlA/analyze_file_storage.py
```

It performs the following checks:
- Database file structures (locations, buckets, file instances)
- Physical file locations on disk
- Cantaloupe accessibility of PDF files
- Upload flow and configuration

### 2. check_venv_files.py

Searches for files in virtualenv and project directories:

```bash
python scripts/AlA/check_venv_files.py --record {record-id} --filename {filename}
```

Can also create test PDF files:

```bash
python scripts/AlA/check_venv_files.py --record {record-id} --create-test
```

### 3. check_container_files.py

Examines files in Docker containers:

```bash
python scripts/AlA/check_container_files.py --record {record-id} --filename {filename}
```

## Best Practices

1. **File Organization**:
   - Organize files consistently using the `data/records/{record-id}/` structure
   - Keep file names consistent with their record metadata

2. **Docker Volumes**:
   - Ensure proper volume mappings in docker-compose.yml
   - Restart containers after changing volumes

3. **Regular Checks**:
   - Periodically verify that files exist in both the database and on disk
   - Test Cantaloupe access to files in all storage locations

4. **File Permissions**:
   - Ensure files have appropriate permissions (usually 644)
   - Check that container users can access the files

## Configuration Reference

### invenio.cfg Settings

```python
# File storage configuration
FILES_REST_STORAGE_FACTORY = 'zenodo_rdm.files.storage_factory'
FILES_REST_STORAGE_CLASS_MAPPING = {
    'L': 'local',  # Local storage
    'F': 'iiif',   # IIIF processed storage
}

# IIIF Configuration
RDM_IIIF_ENABLED = True
RDM_IIIF_CANTALOUPE_URL = "http://localhost:8182"
RDM_IIIF_BASE_PATH = "/iiif"
RDM_IIIF_PDF_SUPPORT = True
RDM_IIIF_MANIFEST_FORMATS = ["jpeg", "jpg", "png", "tiff", "tif", "pdf"]
```

### Docker Volume Mappings

```yaml
volumes:
  - ./data/records:/opt/cantaloupe/images/records
  - ./data/images/private:/opt/cantaloupe/images/private
  - ./test_data:/opt/cantaloupe/images/test
```

## Troubleshooting Case Study: IIIF PDF Manifest Generation

This section presents a real-world case study of troubleshooting IIIF manifest generation for PDF files.

### Problem Description

IIIF manifest generation for PDF files was not working for record ID 202 with file `history00871.pdf`. Although the system was configured correctly in `invenio.cfg`, the PDF file was not physically accessible to the Cantaloupe IIIF server.

### Root Cause Analysis

1. The Cantaloupe Docker container was defined in `docker-compose.yml` but wasn't running
2. A standalone Cantaloupe server was running on the host at port 8182, causing confusion
3. The PDF file wasn't present in the expected location where Cantaloupe looks for files
4. While the file may have been properly stored in the database, it wasn't available at the record-specific path

### Solution Steps

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

4. Verified that Cantaloupe could access the file:
   ```bash
   curl "http://localhost:8182/iiif/2/records%2F202%2Fhistory00871.pdf/info.json"
   ```

### Lessons Learned

1. The actual file storage in Invenio-RDM has two components:
   - The database-managed internal storage (where files are stored by UUID/hash)
   - The record-specific access paths (where files are organized by record ID)
   
2. For IIIF to work properly, files must be present in the record-specific paths that are mounted to the Cantaloupe container

3. The Docker container setup is crucial for proper file access across services

## Conclusion

The Invenio-RDM file storage system uses a combination of database records and physical file storage to manage uploaded files. The record-specific path structure (`data/records/{record-id}/{filename}`) makes files accessible to services like Cantaloupe through Docker volume mappings. When troubleshooting issues with file access, it's important to check both the database records and the physical presence of files in the expected locations. 
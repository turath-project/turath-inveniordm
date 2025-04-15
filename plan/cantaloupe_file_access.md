# How Cantaloupe Accesses PDF Files Uploaded to InvenioRDM

## Current Setup Analysis

Based on the code review, I've found that Cantaloupe and InvenioRDM use different storage locations, which means **files must be copied from InvenioRDM's storage to a location accessible by Cantaloupe**.

## InvenioRDM Storage System

InvenioRDM stores uploaded files using a structured system:

1. When a file is uploaded to a record, it is stored in InvenioRDM's storage backend
2. The file storage is managed through database models like `FileInstance`, `ObjectVersion`, and `Bucket`
3. Files are typically stored with hash-based filenames to avoid collisions
4. The actual file path can be accessed via `file.file.uri` in record objects

## Cantaloupe Access Methods

Cantaloupe can access files through several source implementations:

1. **FilesystemSource** (Most common) - Directly accesses files on the same filesystem
2. **HttpSource** - Retrieves files via HTTP requests
3. **S3Source** - Accesses files in Amazon S3 buckets

Based on the analyzed code, the system uses **FilesystemSource** with a configuration parameter `FilesystemSource.BasicLookupStrategy.path_prefix` pointing to a directory like `/opt/cantaloupe/images`.

## Current File Copying Method

The system currently implements file copying from InvenioRDM to Cantaloupe:

```python
# Typically in Cantaloupe, it follows a structure like:
dest_dir = f"{CANTALOUPE_DATA_DIR}/private/{RECORD_ID}"
dest_path = os.path.join(dest_dir, FILE_KEY)

# Create directory if it doesn't exist
if not os.path.exists(dest_dir):
    os.makedirs(dest_dir, exist_ok=True)

# Copy the file
shutil.copy2(source_path, dest_path)
```

The expected path structure for Cantaloupe is:
```
{CANTALOUPE_DATA_DIR}/private/{RECORD_ID}/{FILENAME}
```

## Request URL Structure

Cantaloupe processes requests with the following structure:
```
https://localhost:8182/iiif/3/private%2F{record_id}%2F{filename}/full/full/0/default.jpg?page=1
```

Where:
- The identifier `private%2F{record_id}%2F{filename}` corresponds to the file path relative to the `FilesystemSource.BasicLookupStrategy.path_prefix`
- `?page=1` parameter indicates which page of the PDF to render

## Solutions for Integrating InvenioRDM with Cantaloupe

There are several approaches we can implement:

### Option 1: File Sync Script (Currently Used)

1. After uploading a PDF to InvenioRDM, extract the record ID
2. Copy the file to the Cantaloupe directory structure using the record ID: 
   ```
   {cantaloupe_dir}/private/{record_id}/{filename}.pdf
   ```
3. Generate a manifest with image URLs pointing to Cantaloupe using this structure

**Pros:** Simple, direct file access
**Cons:** Requires duplicate storage, needs synchronization when files change

### Option 2: Symbolic Links

1. Instead of copying files, create symbolic links from Cantaloupe's directory to InvenioRDM's actual file storage
2. This requires finding the exact file path in InvenioRDM's storage:

```python
def create_cantaloupe_symlink(record_id, filename):
    # Get the record
    record = get_record(record_id)
    
    # Get file instance to find physical file path
    file_obj = record.files[filename]
    file_instance = FileInstance.query.filter_by(id=file_obj.file_id).first()
    source_path = file_instance.uri
    
    # Create symlink in Cantaloupe directory
    cantaloupe_dir = f"{CANTALOUPE_DATA_DIR}/private/{record_id}"
    os.makedirs(cantaloupe_dir, exist_ok=True)
    
    target_path = os.path.join(cantaloupe_dir, filename)
    os.symlink(source_path, target_path)
```

**Pros:** Avoids duplication, always points to current version
**Cons:** Requires filesystem access between containers

### Option 3: Configure Cantaloupe to Use HTTP Source

1. Configure Cantaloupe to use `HttpSource` instead of `FilesystemSource`
2. Set it to access files via InvenioRDM's API:

```
HttpSource.BasicLookupStrategy.url_prefix = https://inveniordm.yourdomain.com/api/records/{}/files/{}
```

3. Ensure proper authentication is configured to access restricted files

**Pros:** No file copying needed, always uses current version
**Cons:** More complex configuration, potential performance impact

### Option 4: Shared Volume Between Containers

1. Configure both InvenioRDM and Cantaloupe to use a shared Docker volume
2. Modify InvenioRDM's file storage configuration to use this volume
3. Configure Cantaloupe to look directly in this shared location

**Pros:** Efficient, no duplication or syncing needed
**Cons:** Requires changes to InvenioRDM's configuration

## Recommended Approach

Based on our analysis, we recommend a hybrid approach:

1. **Initial Implementation:** Use Option 1 (File Sync) for simplicity and to get the system working
2. **Improved Implementation:** Transition to Option 2 (Symbolic Links) to save space and ensure consistency
3. **Production Deployment:** Consider Option 4 (Shared Volume) for the most robust solution

## Implementation Plan

1. Add a step to the book upload workflow that copies the PDF to Cantaloupe's directory
2. Update the manifest generation to use the correct Cantaloupe URL structure
3. Test that Cantaloupe can access and render PDF pages
4. Implement error handling and logging for cases where file copying fails
5. Add monitoring to ensure the files stay synchronized

## Code Modifications Required

1. Add a function to the `upload_book.py` script to copy the file to Cantaloupe
2. Modify `generate_manifest.py` to generate URLs in the correct format for Cantaloupe
3. Create a maintenance script to check for and fix any inconsistencies 
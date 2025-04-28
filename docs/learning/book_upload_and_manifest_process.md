# Learning Document: Book Upload & Manifest Generation Process

## 1. Overview

This document details the steps, challenges, and solutions encountered while setting up and using the `scripts/upload_book.py` script to upload books (PDFs and HOCR files) to the Turath InvenioRDM instance. The goal is to provide a clear guide for future reference, highlighting potential pitfalls and the correct procedures to avoid repeating errors.

## 2. Initial Setup & Discovery

The process began with the need to reinstall or ensure the system was correctly set up.

*   **Action:** Checked the root directory for setup instructions.
*   **Discovery:** Found `README.md` containing the primary setup command.
*   **Key Command:**
    ```bash
    invenio-cli containers start --lock --build --setup
    ```
    *   **Purpose:** Builds Docker images, sets up database/search, and starts all necessary services (Web, Worker, DB, Cache, Queue, Search).
    *   **Note:** This command needs to be run from the project's root directory. The user initially rejected running this via the assistant.

## 3. Admin User & API Token Setup

For interacting with the API (especially for uploads), an admin user and an API token are required.

*   **Scripts Used:**
    *   `scripts/create_admin.sh`: Creates an admin user (`admin@turath.com` with password `123456` by default) and assigns the `admin` role and necessary access rights (`administration-access`, `superuser-access`).
    *   `scripts/generate_api_token.sh`: Generates a persistent API token for the `admin@turath.com` user and automatically saves it to the `.env` file as `RDM_API_TOKEN`.
*   **Commands Executed:**
    ```bash
    bash scripts/create_admin.sh
    bash scripts/generate_api_token.sh
    ```
*   **Learnings:**
    *   These scripts are designed to be somewhat idempotent (they handle cases where the role or user might already exist, although errors might still appear in the logs if duplicates are encountered).
    *   The API token (`RDM_API_TOKEN` in `.env`) is automatically picked up by the `upload_book.py` script if no `--token` argument is provided. The generated token during our session was: `UauufaqiOs6UJ4InKZk0BcyHb9twmL2dyPsvOz0NlLmHvAlAPxowcICBhLuw7CVQYY8HHQqds2w1yXtDuT6xsVLPuGjceh7876SP`

## 4. The Book Upload Script (`scripts/upload_book.py`)

This script is the core component for getting book data into InvenioRDM.

*   **Core Purpose:** Uploads a book's PDF, associated HOCR files (for OCR text), and TIFF page images (optional), extracts/generates metadata, creates a record in InvenioRDM, links the files, generates a IIIF manifest, and publishes the record.
*   **Basic Command Structure:**
    ```bash
    pipenv run python scripts/upload_book.py \
        --book-dir [path/to/book/folder] \
        --api-url [invenio_api_url] \
        # Optional flags (--token, --skip-tiff, --skip-hocr, --pdf-only, etc.)
    ```

### 4.1. Challenges Encountered & Solutions

Several issues were encountered while trying to run and understand this script:

*   **Challenge 1: Python Indentation Errors**
    *   **Problem:** The script initially failed to run (`--help` failed) due to `IndentationError`. Python relies heavily on correct indentation to define code blocks.
    *   **Errors Found:**
        1.  Incorrect indentation under the `if not metadata_loaded:` block (around line 527). The block checking for `manifest.json` was not indented correctly.
        2.  Incorrect indentation under the `elif isinstance(creator_data, str):` block (around line 674). The `creators.append({...})` call was not indented correctly.
    *   **Troubleshooting:**
        *   Initial attempts to fix this automatically using the assistant's editing tools failed. This highlighted the difficulty automated tools can have with nuanced indentation fixes.
        *   Manual correction or providing explicit code replacements was required.
    *   **Solution:** Manually corrected the indentation in both locations as specified in the provided code snippets.
    *   **Lesson:** Always validate Python script syntax, especially indentation. Automated fixes may require verification or manual intervention.

*   **Challenge 2: Understanding Upload Options (Images/HOCR)**
    *   **Problem:** The initial request was to upload "without images". Interpreting this led to confusion about which flag to use.
    *   **Troubleshooting:** Used `pipenv run python scripts/upload_book.py --help` to list available options *after* fixing the indentation errors.
    *   **Key Flags:**
        *   `--skip-tiff`: Skips uploading TIFF page image files from the `pages/` directory.
        *   `--skip-hocr`: Skips uploading HOCR text files from the `hocr/` directory.
        *   `--pdf-only`: Skips *both* HOCR and TIFF files, uploading only the PDF.
    *   **Solution:** Clarified the goal: Upload PDF and HOCR, but *not* TIFFs. Used the `--skip-tiff` flag.
    *   **Lesson:** Carefully read script `--help` output. Understand the specific function of each flag. `--pdf-only` is a broad exclusion; use `--skip-tiff` or `--skip-hocr` for more granular control.

*   **Challenge 3: Manifest Naming, `@id` Bug, and 404 Errors**
    *   **Problem:** After the first successful upload (`--pdf-only`), testing the links *within* the generated IIIF manifest revealed that the manifest's `@id` and canvas `@id` links resulted in 404 errors when accessed via the Invenio API.
    *   **Symptoms:**
        *   `curl` request to `.../files/manifest.json` failed (404).
        *   `curl` request to `.../files/manifest.json/canvas/pXXX` failed (404).
        *   The upload log showed the manifest was uploaded with a temporary name (e.g., `tmpXXXX.json`).
        *   Listing files for the record (`.../files`) confirmed the temporary name.
    *   **Root Cause:** The `upload_book.py` script was:
        1.  Generating the manifest content with the correct *intended* final `@id` (`.../files/manifest.json`).
        2.  Saving this content to a *temporary file* (e.g., `tmpXXXX.json`).
        3.  Uploading this temporary file, resulting in the file being stored under the temporary name (`tmpXXXX.json`) in Invenio.
        4.  The links *inside* the manifest pointed to the non-existent `manifest.json`, causing 404s when trying to resolve them via the API.
    *   **Solution:** Modified the `process` method in `scripts/upload_book.py` (around line 1326):
        *   Instead of `tempfile.NamedTemporaryFile`, use `tempfile.TemporaryDirectory`.
        *   Explicitly save the generated manifest content to a file named `manifest.json` *inside* that temporary directory.
        *   Pass the *path* to this `manifest.json` file to the `upload_files_to_record` method. The uploader uses the basename of the provided path (`manifest.json`) as the key for the upload.
    *   **Lesson:** Ensure consistency between the internal IDs generated within a manifest and the actual filename/key used when uploading that manifest file to the repository. Temporary filenames during intermediate steps can cause resolution issues.

*   **Challenge 4: Date Format Warning**
    *   **Problem:** A warning `WARNING - Invalid date format '2023-01-01', using current date.` appeared in the logs.
    *   **Cause:** The `metadata.json` likely contained a date `2023-01-01`, but the validation logic in `prepare_metadata` or `validate_metadata` expected a different format or strict validation failed, causing it to fall back to the current date. (Looking back at the code, the regex in `prepare_metadata` was `^\\d{4}-\\d{2}-\\d{2}$` which should have matched, but `validate_metadata` had stricter logic that might have tripped up).
    *   **Outcome:** The script handled this gracefully by using the current date, but the underlying metadata wasn't preserved exactly.
    *   **Lesson:** Ensure metadata formats in source files (`metadata.json`) align perfectly with the script's validation rules, or refine the script's validation to be more flexible if needed.

## 5. Working Commands (Final Successful Run)

*   **Setup Admin User:** `bash scripts/create_admin.sh`
*   **Generate API Token:** `bash scripts/generate_api_token.sh`
*   **Upload Book (PDF+HOCR, skip TIFFs):**
    ```bash
    pipenv run python scripts/upload_book.py \
        --book-dir scripts_docs/books/history00872 \
        --api-url https://127.0.0.1:5000/api \
        --hocr-mount-point ./hocr_mount \
        --verbose \
        --no-verify-ssl \
        --skip-tiff
    ```

## 6. Problematic Commands/Steps

*   **Initial `invenio-cli` call:** `invenio-cli containers start --lock --build --setup` (Failed initially because assistant missed the `is_background` parameter required by the tool).
*   **Initial Upload Attempt (Wrong Flag):** Using `--pdf-only` when HOCR files were actually desired. Resulted in "no HOCR files found" log message because they were intentionally skipped.
*   **Upload Attempts Before Fixes:** Any attempt to run the upload script before fixing the indentation errors resulted in `IndentationError`. Any attempt before fixing the manifest naming bug resulted in a working upload *but* a manifest with broken internal links (manifest `@id`, canvas `@id`).
*   **Automated Edits:** Attempts to automatically fix indentation errors failed and required manual intervention/explicit code replacement.

## 7. Key API Endpoints & Structure (InvenioRDM)

*   **Base API URL:** `https://127.0.0.1:5000/api` (as configured)
*   **Authentication:** Bearer Token passed in `Authorization` header (`Authorization: Bearer YOUR_TOKEN`). Token sourced from `.env` or `--token` flag.
*   **Create Draft Record:** `POST /records` (Payload: JSON object with `metadata`, `access`, `files` keys).
*   **List Record Files:** `GET /records/{record_id}/files`
*   **Get Specific File Metadata:** `GET /records/{record_id}/files/{file_key}`
*   **Download File Content:** `GET /records/{record_id}/files/{file_key}/content`
*   **Upload Files (Multi-step):**
    1.  **Initialize:** `POST /records/{record_id}/draft/files` (Payload: `[{"key": "filename1"}, {"key": "filename2"}]`)
    2.  **Upload Content:** `PUT /records/{record_id}/draft/files/{file_key}/content` (Payload: Raw file bytes)
    3.  **Commit File:** `POST /records/{record_id}/draft/files/{file_key}/commit`
*   **Publish Draft:** `POST /records/{record_id}/draft/actions/publish`

## 8. IIIF Manifest Links Analysis (Post-Fix)

After fixing the manifest naming bug (Record ID `b18cm-sbn82`):

*   **Working Links:**
    *   Manifest `@id`: `.../files/manifest.json` (Responds 200 OK via API file metadata endpoint)
    *   Cantaloupe Image: `http://localhost:8182/...` (Responds 200 OK)
    *   Annotation List: `https://localhost/annotations/...` (Responds 200 OK via Nginx proxy)
    *   HOCR `seeAlso`: `.../files/001.hocr` (Responds 200 OK via API file metadata endpoint)
    *   Search Service: `https://localhost/search/...` (Responds 200 OK via Nginx proxy)
    *   PDF Download: `.../files/history00872.pdf` (Responds 200 OK via API file metadata endpoint)
*   **Non-Working Link (via direct `curl`):**
    *   Canvas `@id`: `.../files/manifest.json/canvas/p001` (Responds 404). This is expected when querying the Invenio file API directly; it doesn't parse sub-paths within the JSON file. IIIF clients parse the main manifest (`.../files/manifest.json/content`) and resolve these internally.

## 9. Mistakes Made & Lessons Learned (Assistant Perspective)

*   **Mistake:** Initial `run_terminal_cmd` call missed the required `is_background` parameter.
    *   **Lesson:** Always double-check required parameters for tool calls based on the tool's definition.
*   **Mistake:** Providing unclear instructions for manual indentation fixes, leading to user confusion.
    *   **Lesson:** When automated edits fail, provide very specific, unambiguous instructions for manual changes, including exact line numbers and the precise change needed. If possible, provide the corrected code block directly.
*   **Mistake:** Automated edits failed multiple times to correct indentation.
    *   **Lesson:** Recognize when automated tools are struggling and switch to a more reliable method (like providing code snippets) sooner. Don't repeat failing automated attempts excessively. Verify the diff produced by edits.
*   **Mistake:** Initial misinterpretation of "without images" leading to using `--pdf-only` incorrectly.
    *   **Lesson:** Clarify user requirements precisely, especially when multiple script options exist. Ask clarifying questions if the intent isn't 100% clear from the available flags.

## 10. System Modifications

*   **`scripts/upload_book.py`:** Modified the `process` method to correctly handle the naming and upload of the generated `manifest.json` file, fixing the temporary filename bug and ensuring internal manifest links resolve correctly relative to the uploaded manifest's `@id`.
*   **Nginx / Docker Compose:** No modifications were made to Nginx configuration or Docker Compose files during *this specific troubleshooting session*. The focus was entirely on the Python upload script and its usage.

## 11. Conclusion

Successfully uploading books requires careful execution of setup scripts, understanding the upload script's parameters (especially file inclusion/exclusion flags), and ensuring the script correctly handles file naming and internal linking within generated manifests. Debugging involved checking script syntax (indentation), interpreting logs, testing API endpoints, and analyzing generated file content (manifests). This documented process should serve as a guide to avoid these specific issues in the future. 
# Book Upload to InvenioRDM

## 1. Introduction

The `upload_book.py` script automates the process of uploading digitized books to InvenioRDM repositories. This tool is designed to comply with institutional repository best practices and metadata standards, ensuring that uploaded content is properly described, discoverable, and accessible.

## 2. Overview

### 2.1 Purpose

The script facilitates the deposit of digital book collections into InvenioRDM institutional repositories, handling:

- Creation of standardized metadata records 
- Upload of primary content files (PDF) and derivative files (HOCR, TIFF)
- Integration with IIIF for enhanced viewing capabilities
- Record validation and publication

### 2.2 Compliance

The implementation follows these standards and best practices:

- **Dublin Core metadata standard** - Core metadata elements align with Dublin Core
- **IIIF Presentation API 2.1** - Support for IIIF manifest references
- **OpenAIRE Guidelines 3.0** - Metadata structure compatible with OpenAIRE harvesting
- **DataCite Metadata Schema 4.4** - Record structure compatible with DOI registration
- **ISO 8601** - Date formatting follows international standard (YYYY-MM-DD)
- **ISO 639-3** - Language codes in three-letter format

## 3. System Requirements

- Python 3.7 or higher
- InvenioRDM instance with API access
- Valid API token or credentials with deposit permissions
- Network access to the InvenioRDM instance

## 4. Usage

### 4.1 Basic Usage (PDF + HOCR + TIFF + Generated Manifest)

```bash
# Assumes RDM_API_TOKEN is set in .env
pipenv run python scripts/upload_book.py \
    --book-dir /path/to/book \
    --api-url https://127.0.0.1:5000/api \
    --no-verify-ssl \
    --verbose
```

### 4.2 Usage with Specific Token

```bash
pipenv run python scripts/upload_book.py \
    --book-dir /path/to/book \
    --api-url https://127.0.0.1:5000/api \
    --token YOUR_RDM_API_TOKEN \
    --no-verify-ssl \
    --verbose
```

### 4.3 Usage Skipping TIFF Images (PDF + HOCR + Generated Manifest)

This is a common scenario if page images are not needed in the repository, but OCR text is.

```bash
pipenv run python scripts/upload_book.py \
    --book-dir /path/to/book \
    --api-url https://127.0.0.1:5000/api \
    --token YOUR_RDM_API_TOKEN \
    --skip-tiff \
    --no-verify-ssl \
    --verbose
```

### 4.4 Usage Uploading Only PDF (No HOCR, No TIFF + Generated Manifest)

Use this if only the main PDF document is required.

```bash
pipenv run python scripts/upload_book.py \
    --book-dir /path/to/book \
    --api-url https://127.0.0.1:5000/api \
    --token YOUR_RDM_API_TOKEN \
    --pdf-only \
    --no-verify-ssl \
    --verbose
```

### 4.5 Draft Mode (No Publication)

Uploads files but leaves the record as a draft for further review/modification.

```bash
pipenv run python scripts/upload_book.py \
    --book-dir /path/to/book \
    --api-url https://127.0.0.1:5000/api \
    --token YOUR_RDM_API_TOKEN \
    --draft \
    --no-verify-ssl \
    --verbose 
```

### 4.6 Generate Metadata Template

```bash
pipenv run python scripts/upload_book.py --generate-metadata-template --template-output metadata_template.json
```

## 5. Data Model and Metadata Requirements

### 5.1 Directory Structure

The script expects a directory structure following these conventions:

```
book_directory/
├── book.pdf            # Primary content (required)
├── manifest.json       # IIIF manifest (optional but recommended)
├── hocr/               # Directory containing HOCR files (optional)
│   ├── 001.hocr
│   ├── 002.hocr
│   └── ...
└── tiff/               # Directory containing TIFF files (optional)
    ├── 001.tif
    ├── 002.tif
    └── ...
```

### 5.2 Metadata Schema

The metadata model aligns with InvenioRDM's schema, which is compatible with DataCite and Dublin Core. The core metadata elements include:

| Metadata Element | Required | Schema Mapping | Example Value |
|------------------|----------|----------------|---------------|
| Title | Yes | dc:title | "History of Mathematics" |
| Creators | Yes | dc:creator | [{"person_or_org": {"family_name": "Smith", "given_name": "John"}}] |
| Resource Type | Yes | dc:type | {"id": "publication-book"} |
| Publication Date | Yes | dc:date | "2023-05-15" |
| Description | Yes | dc:description | "A comprehensive study of..." |
| Language | Yes | dc:language | [{"id": "eng"}] |
| Identifier | No | dc:identifier | [{"identifier": "book123", "scheme": "other"}] |
| Rights | No | dc:rights | [{"id": "cc-by-4.0"}] |
| Subjects | No | dc:subject | [{"subject": "Mathematics"}] |

### 5.3 IIIF Integration

For IIIF integration, the script adds a custom field containing the IIIF manifest URL:

```json
"custom_fields": {
  "turath:iiif_manifest": "http://iiif.example.org/iiif/3/book-id/manifest.json"
}
```

This follows the IIIF Presentation API 2.1 specification for manifest references.

## 6. Command Line Reference

### 6.1 Required Arguments

| Argument | Description |
|----------|-------------|
| `--book-dir`, `-b` | Directory containing the book files |

### 6.2 Authentication

| Argument | Description |
|----------|-------------|
| `--api-url` | InvenioRDM API URL (default: https://localhost:5000/api) |
| `--token` | API token for authentication |
| `--username` | Username for basic authentication (alternative to token) |
| `--password` | Password for basic authentication |
| `--no-verify-ssl` | Disable SSL certificate verification |

### 6.3 Content Selection

| Argument | Description |
|----------|-------------|
| `--pdf-only` | Upload only the PDF file and manifest.json (skip HOCR and TIFF files) |
| `--skip-hocr` | Skip uploading HOCR files |
| `--skip-tiff` | Skip uploading TIFF image files |

### 6.4 Record Management

| Argument | Description |
|----------|-------------|
| `--draft` | Keep the record as a draft (do not publish) |
| `--no-publish` | Alias for --draft |
| `--community` | Community ID to add the record to |
| `--metadata-file` | JSON file with additional metadata for the record |

### 6.5 Utilities

| Argument | Description |
|----------|-------------|
| `--generate-metadata-template` | Generate a template metadata file and exit |
| `--template-output` | Output file for the metadata template |
| `--max-retries` | Maximum number of upload retries (default: 3) |
| `--verbose`, `-v` | Enable verbose output |

## 7. Metadata Validation Process

The script implements a comprehensive metadata validation and correction process to ensure compliance with InvenioRDM requirements:

1. **Validation** - All metadata elements are checked against the schema requirements
2. **Normalization** - Element formats are normalized (dates, language codes, etc.)
3. **Default Assignment** - Missing required elements receive sensible defaults
4. **Error Correction** - Invalid values are fixed when possible

### 7.1 Validation Rules

| Element | Validation Rule | Default Value |
|---------|----------------|---------------|
| Title | Required, non-empty string | Book directory name |
| Creators | Required, must include family_name | {"family_name": "Library", "given_name": "Turath Digital"} |
| Publication Date | Required, ISO 8601 format (YYYY-MM-DD) | Current date |
| Resource Type | Must include valid type ID | {"id": "publication-book"} |
| Description | Required, non-empty string | "Book from Turath Digital Library: {book_id}" |
| Language | Required, valid ISO 639-3 code | {"id": "ara"} |
| Identifier | Must use valid scheme | {"identifier": "{book_id}", "scheme": "other"} |

## 8. Metadata Sources

The script extracts and merges metadata from multiple sources, following this priority:

1. **Custom metadata file** (highest priority) - Explicit metadata provided via `--metadata-file`
2. **IIIF manifest** - Metadata extracted from manifest.json in the book directory
3. **Generated defaults** (lowest priority) - Automatically generated based on directory name and default values

### 8.1 Metadata Source Precedence

When multiple sources provide conflicting metadata values, the script applies the following precedence rules:

1. Custom metadata file overrides manifest.json
2. Manifest.json overrides generated defaults
3. Default values used only when no other source provides the data

### 8.2 Example Workflow

![Metadata Flow Diagram](https://www.example.org/metadata-flow.png)

1. Script scans book directory for manifest.json
2. Extracts basic metadata from manifest.json
3. Loads user-provided metadata file if specified
4. Merges information, with custom file taking precedence
5. Validates combined metadata against schema
6. Applies corrections and default values for missing fields
7. Submits final metadata with record creation

## 9. Error Handling

The script implements robust error handling with three primary response types:

1. **Warnings** - Non-fatal issues that can be resolved automatically (missing optional fields)
2. **Validation Errors** - Serious but recoverable issues (invalid field values)
3. **Critical Errors** - Fatal issues preventing upload (authentication failure)

All errors and warnings are logged with timestamps and contextual information.

## 10. Best Practices

### 10.1 Recommended Workflow

1. Generate a metadata template using `--generate-metadata-template`
2. Customize the template with accurate book metadata
3. Use the `--pdf-only` and `--draft` options for initial testing
4. Verify the record in the InvenioRDM web interface
5. Run a full upload with all files once metadata is confirmed correct

### 10.2 Performance Considerations

- Large TIFF files (>100MB) may require increased `--max-retries`
- Consider using `--pdf-only` for books with many pages
- Batch uploads should be scheduled during off-peak hours

## 11. Security Considerations

- API tokens should be treated as sensitive data
- SSL verification should only be disabled in testing environments
- Use environment variables for credentials in production settings

## 12. Examples

### 12.1 Minimal Valid Upload

```bash
python scripts/upload_book.py --book-dir /path/to/book --api-url https://repository.example.org/api --token YOUR_TOKEN
```

### 12.2 Complete Upload with Custom Metadata

```bash
python scripts/upload_book.py --book-dir /path/to/book --api-url https://repository.example.org/api --token YOUR_TOKEN --metadata-file metadata.json
```

Example metadata.json:
```json
{
  "metadata": {
    "title": "A Comprehensive History of Mathematics",
    "publication_date": "1985-03-15",
    "resource_type": {"id": "publication-book"},
    "creators": [
      {
        "person_or_org": {
          "family_name": "Smith",
          "given_name": "John A.",
          "type": "personal"
        },
        "role": "author"
      }
    ],
    "languages": [{"id": "eng"}],
    "description": "This landmark work covers the historical development of mathematical concepts and theories from ancient times to the modern era.",
    "identifiers": [
      {
        "identifier": "9780123456789",
        "scheme": "isbn"
      }
    ]
  },
  "access": {
    "record": "public",
    "files": "public"
  },
  "files": {
    "enabled": true
  },
  "custom_fields": {
    "turath:iiif_manifest": "http://iiif.example.org/iiif/3/math-history-1985/manifest.json"
  }
}
```

## 13. Troubleshooting

This section highlights common issues encountered specifically with the `upload_book.py` script.
For a more general cheatsheet, see `docs/learning/troubleshooting-cheatsheet.md`.

**1. Problem: Script fails immediately (e.g., running `--help`) with `IndentationError`.**

*   **Cause:** Incorrect Python indentation. Python uses indentation to define code blocks.
*   **Errors Found (Specific Session):**
    *   Block under `if not metadata_loaded:` (around line 527) was not indented.
    *   `creators.append({...})` block under `elif isinstance(creator_data, str):` (around line 674) was not indented.
*   **Solution:** Carefully check and correct Python indentation. Use a linter or IDE that highlights indentation issues. Manual correction might be needed if automated tools fail.
*   **Lesson:** Python syntax, especially indentation, is critical. Validate scripts before running.

**2. Problem: Manifest `@id` and Canvas `@id` links give 404 errors when checked via API, even though upload succeeded.**

*   **Cause:** A previous version of the script uploaded the internally generated manifest using a temporary filename (`tmpXXX.json`) but the `@id` links *inside* the manifest pointed to the intended final name (`manifest.json`). The API couldn't find a file named `manifest.json` associated with the record.
*   **Solution:** The script was modified (around line 1326 in the `process` method) to:
    1.  Explicitly save the generated manifest content to a file named `manifest.json` within a temporary directory.
    2.  Upload *that specific file*, ensuring the key used in InvenioRDM is `manifest.json`.
*   **Lesson:** Ensure consistency between internal IIIF `@id` links and the actual filename/key used for storing the manifest file in the repository.

**3. Problem: Log shows "no HOCR files found" even though they exist in the `hocr/` directory.**

*   **Cause:** The script was run with the `--pdf-only` flag, which explicitly tells it to *skip* collecting HOCR and TIFF files during the `collect_files` step.
*   **Solution:** Remove the `--pdf-only` flag. If you want to exclude only TIFFs, use `--skip-tiff`. If you want to exclude only HOCR, use `--skip-hocr`.
*   **Lesson:** Understand the specific function of script flags (`--help` is useful). `--pdf-only` broadly skips HOCR and TIFFs.

**4. Problem: Log shows `WARNING - Invalid date format 'YYYY-MM-DD', using current date.`**

*   **Cause:** The date format in the source `metadata.json` file (e.g., `2023-01-01`) did not strictly match the validation logic/regex within the `upload_book.py` script's `prepare_metadata` or `validate_metadata` methods.
*   **Solution:** Either correct the date format in `metadata.json` to strictly match `YYYY-MM-DD` or adjust the validation logic in the script if more flexibility is needed.
*   **Lesson:** Ensure source metadata adheres to the expected formats defined or validated by the processing script.

**5. Problem: Upload fails partway through, especially with many files.**

*   **Cause:** Potential network timeouts, server-side limits, or temporary issues.
*   **Solution:** The script includes a `--max-retries` option (default 3). Consider increasing this for large uploads. Check InvenioRDM logs for specific server-side errors.

For more details on the troubleshooting process and specific commands used, refer to `docs/learning/book_upload_and_manifest_process.md`.

## 14. References

- InvenioRDM Documentation: https://inveniordm.docs.cern.ch/
- Dublin Core Metadata Initiative: https://www.dublincore.org/specifications/dublin-core/
- IIIF Presentation API: https://iiif.io/api/presentation/2.1/
- DataCite Metadata Schema: https://schema.datacite.org/
- OpenAIRE Guidelines: https://guidelines.openaire.eu/en/latest/ 
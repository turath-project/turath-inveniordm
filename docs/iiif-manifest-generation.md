# IIIF Manifest Generation

This document explains the IIIF manifest generation process and the auto-scaling feature for coordinate alignment.

## Overview

The `generate_manifest.py` script creates IIIF Presentation API 2.1 compliant manifests for books with PDF, HOCR files, and images. It's designed to work with the Cantaloupe IIIF server and integrates with annotation and search services.

## Key Features

### Auto-scaling for HOCR Coordinates

One of the most challenging aspects of working with HOCR files and PDF rendering is aligning coordinates correctly. The OCR engine produces coordinates in its own coordinate system, while the PDF rendering in a IIIF server like Cantaloupe might use different dimensions.

The auto-scaling feature:

1. Extracts dimensions from HOCR files (using BeautifulSoup)
2. Gets actual dimensions from PDF pages (using PyPDF2)
3. Retrieves rendering dimensions from Cantaloupe IIIF server
4. Calculates an appropriate scale factor between these coordinate systems
5. Applies the scale factor to ensure annotations align correctly with rendered pages

This results in properly aligned text highlights and annotations when using the Mirador viewer or annotation tools.

### Directory Structure

The script expects a directory structure similar to:

```
book_directory/
├── book.pdf               # Main PDF file
├── hocr/                  # Directory containing HOCR files
│   ├── 001.hocr
│   ├── 002.hocr
│   └── ...
└── pages/                 # Optional directory for page images
    ├── 001.tif
    ├── 002.tif
    └── ...
```

## Usage

Basic usage:

```bash
python scripts/generate_manifest.py --book-dir /path/to/book
```

To enable auto-scaling:

```bash
python scripts/generate_manifest.py --book-dir /path/to/book --auto-scale
```

### Options

| Option | Description |
|--------|-------------|
| `--book-dir`, `-b` | Directory containing the book files (required) |
| `--iiif-server` | IIIF image server base URL (default: https://localhost:8182/iiif/3) |
| `--manifest-server` | Manifest server base URL (default: http://localhost:8000) |
| `--annotation-server` | Annotation server base URL (default: http://localhost:5002) |
| `--search-server` | Search server base URL (default: http://localhost:5001) |
| `--output`, `-o` | Output file path (defaults to manifest.json in the book directory) |
| `--title` | Book title (defaults to directory name if not provided) |
| `--author` | Book author (default: "Turath Digital Library") |
| `--lang` | Primary language of the book (default: "ar") |
| `--force`, `-f` | Overwrite existing manifest if it exists |
| `--auto-scale`, `-a` | Automatically calculate scale factors for HOCR coordinates |

### Example Commands

For a standard Arabic book with default server settings:
```bash
python scripts/generate_manifest.py --book-dir /path/to/books/history00871 --auto-scale
```

For a book with a custom title and specific output location:
```bash
python scripts/generate_manifest.py --book-dir /path/to/books/history00871 --title "History of Science" --output /path/to/output/manifest.json --auto-scale
```

For a book using custom server configurations:
```bash
python scripts/generate_manifest.py --book-dir /path/to/books/history00871 --iiif-server https://iiif.example.org/iiif/3 --manifest-server https://www.example.org --annotation-server https://annotations.example.org --search-server https://search.example.org
```

## Dependencies

The script requires the following Python packages:
- Pillow: For image processing
- BeautifulSoup4: For parsing HOCR files
- PyPDF2: For extracting PDF information
- requests: For communicating with the IIIF server

These dependencies are included in the project's Pipfile.

## Technical Details

### Scale Factor Calculation

The scale factor is calculated as the average of width and height ratios between the Cantaloupe rendering and HOCR dimensions:

```python
width_ratio = cantaloupe_width / hocr_width
height_ratio = cantaloupe_height / hocr_height
scale_factor = (width_ratio + height_ratio) / 2
```

This value is then stored in the canvas's `scaleFactor` property in the manifest, which can be used by compatible viewers and annotation tools.

### Scale Factor Examples

For a typical case, here are examples of scale factor calculations:

| Source | Dimensions | Resulting Scale Factor |
|--------|------------|------------------------|
| HOCR file | 1675 x 2600 | - |
| PDF page | 612 x 792 (pts) | - |
| Cantaloupe | 925 x 1422 | Scale factor: ~0.55 |

This scale factor means that coordinates in the HOCR file need to be multiplied by approximately 0.55 to properly align with the rendered page.

### Manifest Structure

The generated manifest follows the IIIF Presentation API 2.1 specification, with additions:

1. Each canvas includes:
   - Width and height based on scaled dimensions
   - Image annotation linking to the PDF page via the IIIF server
   - References to annotation lists
   - `seeAlso` property linking to the HOCR file
   - `scaleFactor` property for coordinate scaling

2. The manifest includes service definitions for:
   - Search API
   - Autocomplete
   - Direct PDF download link

3. For Arabic books, the `viewingDirection` is set to `right-to-left`

### Sample Manifest JSON

Here's a simplified excerpt from a generated manifest:

```json
{
  "@context": "http://iiif.io/api/presentation/2/context.json",
  "@id": "http://localhost:8000/history00871/manifest.json",
  "@type": "sc:Manifest",
  "label": "History00871 (PDF Direct)",
  "viewingDirection": "right-to-left",
  "sequences": [
    {
      "@type": "sc:Sequence",
      "canvases": [
        {
          "@id": "http://localhost:8000/history00871/manifest.json/canvas/p001",
          "@type": "sc:Canvas",
          "label": "p. 001",
          "width": 925,
          "height": 1422,
          "images": [
            {
              "@type": "oa:Annotation",
              "motivation": "sc:painting",
              "on": "http://localhost:8000/history00871/manifest.json/canvas/p001",
              "resource": {
                "@id": "http://localhost:8182/iiif/3/history00871.pdf/full/full/0/default.jpg?page=1",
                "@type": "dctypes:Image",
                "width": 925,
                "height": 1422
              }
            }
          ],
          "otherContent": [
            {
              "@id": "http://localhost:5002/annotations/history00871/p001/line",
              "@type": "sc:AnnotationList",
              "label": "Text of page 001"
            }
          ],
          "seeAlso": [
            {
              "@id": "http://localhost:8000/history00871/hocr/001.hocr",
              "format": "text/vnd.hocr+html",
              "profile": "http://kba.github.io/hocr-spec/1.2/",
              "label": "HOCR OCR text"
            }
          ],
          "scaleFactor": 0.553
        }
      ]
    }
  ],
  "service": [
    {
      "@context": "http://iiif.io/api/search/0/context.json",
      "@id": "http://localhost:5001/search",
      "profile": "http://iiif.io/api/search/0/search",
      "label": "Search within this manifest"
    }
  ],
  "related": {
    "@id": "http://localhost:8000/history00871/history00871.pdf",
    "format": "application/pdf",
    "label": "Download full PDF"
  }
}
```

## Integration with InvenioRDM

The generated manifests can be uploaded to InvenioRDM along with the book files, enabling IIIF-based viewing within the repository.

### Workflow for InvenioRDM Integration

1. **Generate the manifest**:
   ```bash
   python scripts/generate_manifest.py --book-dir /path/to/books/history00871 --auto-scale
   ```

2. **Upload to InvenioRDM**:
   Use the `upload_book.py` script which will:
   - Create a draft record
   - Upload the PDF file
   - Upload all HOCR files
   - Upload the generated manifest.json
   - Set appropriate metadata
   - Optionally publish the record

   ```bash
   python scripts/upload_book.py --book-dir /path/to/books/history00871 --api-url https://your-inveniordm-instance.com --token YOUR_TOKEN
   ```

3. **Use the --draft option** if you need to manually add metadata:
   ```bash
   python scripts/upload_book.py --book-dir /path/to/books/history00871 --api-url https://your-inveniordm-instance.com --token YOUR_TOKEN --draft
   ```

4. **View in Mirador**: Once uploaded, the IIIF viewer in InvenioRDM will use the manifest to display the book with properly aligned annotations and search capabilities.

### Using Manifest with External IIIF Viewers

The generated manifest can also be used with external IIIF viewers:

1. **Mirador**: Enter the manifest URL in Mirador to view the book
2. **Universal Viewer**: Load the manifest in Universal Viewer for a different reading experience
3. **OpenSeadragon**: Use just the image URLs for a simpler viewing experience

## Manifest Generation within `upload_book.py` (Current Approach)

While the standalone `generate_manifest.py` script exists, the current primary workflow uses the **`scripts/upload_book.py`** script, which incorporates manifest generation *during* the upload process.

### Process:

1.  The `upload_book.py` script first creates a draft record in InvenioRDM.
2.  It uploads the required files (PDF, HOCR, etc., based on flags like `--skip-tiff`).
3.  It copies the primary PDF to a location accessible by the Cantaloupe IIIF server (e.g., `./cantaloupe-files/`).
4.  **Crucially**, *after* file uploads, it calls its internal `_generate_manifest_content` method.
5.  This method:
    *   Uses the record ID and uploaded file information.
    *   Calculates scale factors by querying the Cantaloupe server for PDF page dimensions (using the copied PDF) and comparing them with HOCR dimensions (if HOCR files were uploaded and found).
    *   Constructs the IIIF manifest JSON, including links to:
        *   Cantaloupe image resources (`http://localhost:8182/...`).
        *   Annotation service endpoints (`https://localhost/annotations/...`).
        *   Search service endpoints (`https://localhost/search/...`).
        *   Uploaded HOCR files within Invenio (`.../files/XXX.hocr`).
        *   The main PDF download link (`.../files/book.pdf`).
    *   Sets the manifest's `@id` to the expected final location: `https://{invenio_host}/records/{record_id}/files/manifest.json`.
6.  The script then saves this generated content to a file explicitly named `manifest.json`.
7.  Finally, it uploads *this* `manifest.json` file to the InvenioRDM record using the key `manifest.json`.

### Important Considerations & Past Issues:

*   **Filename Consistency:** A previous version of the script incorrectly uploaded the manifest using a temporary filename (e.g., `tmpXXXX.json`) while the `@id` inside pointed to `manifest.json`. This caused 404 errors when trying to resolve manifest or canvas IDs via the API. The script has been **fixed** to ensure it uploads the file with the correct `manifest.json` key.
*   **Cantaloupe Dependency:** This generation process relies on the Cantaloupe server being accessible (default `http://localhost:8182`) during the upload script's execution to retrieve accurate image dimensions for scaling.
*   **Static Manifest:** The generated manifest is static and uploaded as a file. This differs from potential dynamic approaches where the manifest might be generated on-the-fly by an InvenioRDM endpoint.
*   **HOCR Copy:** For annotation services that rely on accessing HOCR files directly, the `upload_book.py` script includes logic (using the `--hocr-mount-point` argument) to copy uploaded HOCR files to a specified host directory accessible by those services.

For a detailed history of troubleshooting this process, including errors and specific commands, please refer to `docs/learning/book_upload_and_manifest_process.md`.

## Troubleshooting

### Common Issues

1. **Incorrect scale factors**: 
   - Check that the HOCR files contain valid page dimensions
   - Verify that Cantaloupe is correctly serving the PDF files
   - Ensure the PDF is properly readable by PyPDF2

2. **Missing dimensions**:
   - If HOCR dimensions can't be extracted, check the HOCR format
   - If Cantaloupe dimensions are missing, check if the IIIF server is accessible

3. **Connection errors**:
   - The script requires internet access to communicate with the Cantaloupe server
   - Verify that SSL verification is correctly handled for your environment

### Scale Factor Verification

To verify that your scale factors are correct, you can:

1. Generate the manifest with auto-scaling
2. Open the book in Mirador
3. Enable text selection or annotation features
4. Check if the highlights align with the visual elements

If highlights are misaligned, you may need to manually adjust the scale factor or check for issues in the original HOCR files.

## Advanced Usage

### Customizing the Manifest Template

The script generates a standard IIIF manifest, but you can customize the template by modifying the `generate_manifest.py` script. Common customizations include:

- Adding more metadata fields
- Customizing the service endpoints
- Adding additional viewing hints or behaviors

### Batch Processing

For batch processing multiple books:

```bash
for book in /path/to/books/*; do
  if [ -d "$book" ]; then
    echo "Processing $book"
    python scripts/generate_manifest.py --book-dir "$book" --auto-scale
  fi
done
```

### Integration with OCR Workflow

The manifest generation can be integrated into a larger OCR workflow:

1. OCR processing creates PDF and HOCR files
2. Manifest generation creates the IIIF manifest
3. Upload script uploads everything to InvenioRDM
4. Users can immediately search and view the content 
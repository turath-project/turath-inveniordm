# PDF-IIIF Visual Guide

This guide provides visual explanations of how PDF support works in Cantaloupe IIIF server within the InvenioRDM platform. Visual aids will help clarify the concepts and workflows.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [URL Encoding Visualization](#url-encoding-visualization)
3. [PDF Access Workflow](#pdf-access-workflow)
4. [Manifest Generation Flow](#manifest-generation-flow)
5. [Troubleshooting Decision Tree](#troubleshooting-decision-tree)
6. [Code Examples with Visual Annotations](#code-examples-with-visual-annotations)

## Architecture Overview

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│                 │       │                 │       │                 │
│   Web Browser   │◄──────┤  InvenioRDM API ├───────┤ IIIF Manifest   │
│                 │       │                 │       │                 │
└─────────┬───────┘       └────────┬────────┘       └────────┬────────┘
          │                        │                         │
          │                        │                         │
          │                        │                         │
          │                        ▼                         │
          │               ┌─────────────────┐                │
          │               │                 │                │
          └──────────────►│CantaloupeProxy │◄───────────────┘
                          │                 │
                          └────────┬────────┘
                                   │
                                   │
                                   ▼
                          ┌─────────────────┐
                          │                 │
                          │   Cantaloupe    │
                          │   IIIF Server   │
                          │                 │
                          └────────┬────────┘
                                   │
                                   │
                                   ▼
                          ┌─────────────────┐
                          │                 │
                          │   PDF Files     │
                          │                 │
                          └─────────────────┘
```

The diagram above shows how PDF files are served through the InvenioRDM platform. The critical component is the CantaloupeProxy, which handles URL encoding and interacts with the Cantaloupe IIIF server.

## URL Encoding Visualization

### Incorrect Path (Fails)

```
http://localhost:8182/iiif/2/private/212/document.pdf/info.json
                             │      │        │
                             ▼      ▼        ▼
                         These slashes confuse Cantaloupe,
                         causing a "No route for path" error
```

### Correct Path (Works)

```
http://localhost:8182/iiif/2/private%2F212%2Fdocument.pdf/info.json
                             │      │        │
                             ▼      ▼        ▼
                         Encoded slashes (%2F) allow
                         Cantaloupe to correctly parse the path
```

### Visual Comparison

```
┌─────────────────────────────────────────────────────────┐
│ Raw Path: private/212/document.pdf                      │
├─────────────────────────────────────────────────────────┤
│ ➡️ Incorrect URL:                                        │
│ http://localhost:8182/iiif/2/private/212/document.pdf   │
│                                                         │
│ ❌ Cantaloupe sees:                                      │
│ - Base path: /iiif/2                                    │
│ - Identifier: private/212/document.pdf (invalid)        │
│ - Result: 404 Not Found                                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Encoded Path: private%2F212%2Fdocument.pdf              │
├─────────────────────────────────────────────────────────┤
│ ➡️ Correct URL:                                          │
│ http://localhost:8182/iiif/2/private%2F212%2Fdocument.pdf│
│                                                         │
│ ✅ Cantaloupe sees:                                      │
│ - Base path: /iiif/2                                    │
│ - Identifier: private%2F212%2Fdocument.pdf (valid)      │
│ - Result: 200 OK with PDF info                          │
└─────────────────────────────────────────────────────────┘
```

## PDF Access Workflow

```
┌─────────────────┐     ┌────────────────────┐     ┌───────────────────┐
│                 │     │                    │     │                   │
│  Client Request │────►│  CantaloupeProxy  │────►│Path Encoding Check│
│                 │     │                    │     │                   │
└─────────────────┘     └────────────────────┘     └─────────┬─────────┘
                                                             │
                                                             │
                                                             ▼
┌─────────────────┐     ┌────────────────────┐     ┌───────────────────┐
│                 │     │                    │     │                   │
│   HTTP Response │◄────│  Cantaloupe Server │◄────│  URL Construction │
│                 │     │                    │     │                   │
└─────────────────┘     └────────────────────┘     └───────────────────┘
```

### Step-by-Step PDF Page Access

1. Client requests a specific PDF page:
   ```
   GET /api/iiif/record:212:document.pdf/full/full/0/default.jpg?page=1
   ```

2. CantaloupeProxy processes the request:
   ```python
   # Extract record_id (212) and filename (document.pdf)
   # Determine this is a PDF based on filename extension
   ```

3. Path is encoded:
   ```
   private/212/document.pdf → private%2F212%2Fdocument.pdf
   ```

4. URL is constructed:
   ```
   http://localhost:8182/iiif/2/private%2F212%2Fdocument.pdf/full/full/0/default.jpg?page=1
   ```

5. Request is sent to Cantaloupe:
   ```
   Cantaloupe processes the request and returns the PDF page as a JPEG image
   ```

6. Response is returned to client:
   ```
   HTTP/1.1 200 OK
   Content-Type: image/jpeg
   ...
   [JPEG image data for page 1]
   ```

## Manifest Generation Flow

```
                               ┌─────────────────────┐
                               │                     │
                               │     Start           │
                               │                     │
                               └──────────┬──────────┘
                                          │
                                          ▼
                               ┌─────────────────────┐
                               │                     │
                               │ Request PDF info.json│
                               │                     │
                               └──────────┬──────────┘
                                          │
                                          ▼
                             ┌───────────────────────┐
                             │                       │
                             │  Determine PDF pages  │
                             │                       │
                             └───────────┬───────────┘
                                         │
                                         ▼
┌───────────────────┐      ┌────────────────────────┐
│                   │      │                        │
│ Create manifest   │◄─────┤ For each page          │
│ structure         │      │ create canvas          │
│                   │      │                        │
└───────┬───────────┘      └────────────┬───────────┘
        │                                │
        │                                │
        ▼                                ▼
┌───────────────────┐      ┌────────────────────────┐
│                   │      │                        │
│ Add metadata      │      │ Add image annotation   │
│                   │      │ with encoded URL       │
└───────┬───────────┘      │                        │
        │                  └────────────┬───────────┘
        │                                │
        ▼                                ▼
┌───────────────────────────────────────────────────┐
│                                                   │
│                Return completed manifest          │
│                                                   │
└───────────────────────────────────────────────────┘
```

### Example Manifest Structure (Simplified)

```json
{
  "@context": "http://iiif.io/api/presentation/2/context.json",
  "@type": "sc:Manifest",
  "@id": "https://example.org/api/iiif/record:212/manifest",
  "label": "PDF Document",
  "sequences": [
    {
      "@id": "https://example.org/api/iiif/record:212/sequence/default",
      "@type": "sc:Sequence",
      "canvases": [
        {
          "@id": "https://example.org/api/iiif/record:212:document.pdf/canvas/p001",
          "@type": "sc:Canvas",
          "label": "Page 1",
          "width": 800,
          "height": 1200,
          "images": [
            {
              "@id": "https://example.org/api/iiif/record:212:document.pdf/annotation/p001",
              "@type": "oa:Annotation",
              "motivation": "sc:painting",
              "resource": {
                "@id": "http://localhost:8182/iiif/2/private%2F212%2Fdocument.pdf/full/full/0/default.jpg?page=1",
                "@type": "dctypes:Image",
                "format": "image/jpeg",
                "width": 800,
                "height": 1200,
                "service": {
                  "@context": "http://iiif.io/api/image/2/context.json",
                  "@id": "http://localhost:8182/iiif/2/private%2F212%2Fdocument.pdf",
                  "profile": "http://iiif.io/api/image/2/level2.json"
                }
              },
              "on": "https://example.org/api/iiif/record:212:document.pdf/canvas/p001"
            }
          ]
        },
        {
          "@id": "https://example.org/api/iiif/record:212:document.pdf/canvas/p002",
          "label": "Page 2",
          "...": "..."
        }
      ]
    }
  ]
}
```

## Troubleshooting Decision Tree

```
                                 ┌────────────────────┐
                                 │                    │
                                 │ PDF Access Issue   │
                                 │                    │
                                 └─────────┬──────────┘
                                           │
                                           ▼
                        ┌────────────────────────────────┐
                        │                                │
                        │  404 "No route for path"?      │
                        │                                │
                        └──┬───────────────────────────┬─┘
                           │                           │
                           │ Yes                       │ No
                           ▼                           ▼
┌───────────────────────────────────┐      ┌────────────────────────────────┐
│                                   │      │                                │
│ Check URL encoding                │      │ 404 "File not found"?          │
│ Replace slashes with %2F          │      │                                │
│                                   │      └─┬──────────────────────────────┤
└─────────────────┬─────────────────┘        │                              │
                  │                          │ Yes                          │ No
                  ▼                          ▼                              ▼
         ┌──────────────────┐    ┌────────────────────────┐    ┌─────────────────────────┐
         │                  │    │                        │    │                         │
         │ Fixed?           │    │ Check file existence   │    │ 400 Bad Request?        │
         │                  │    │ in Cantaloupe container│    │                         │
         └──┬──────────────┬┘    │                        │    └─┬───────────────────────┤
            │              │     └──────────┬─────────────┘      │                       │
       Yes  │              │ No             │                    │ Yes                   │ No
            │              │                ▼                    ▼                       ▼
            │              │      ┌──────────────────────┐    ┌───────────────────┐   ┌────────────────┐
            │              │      │                      │    │                   │   │                │
            │              └─────►│ Check volume mapping │    │ Check page param  │   │ Check logs     │
            │                     │ and file paths       │    │ & PDF processor   │   │                │
            │                     │                      │    │ configuration     │   │                │
            │                     └──────────────────────┘    └───────────────────┘   └────────────────┘
            │
            ▼
┌───────────────────────┐
│                       │
│ Success!              │
│                       │
└───────────────────────┘
```

## Code Examples with Visual Annotations

### URL Encoding in Python

```python
def build_cantaloupe_url(self, record_id, filename, region, size, rotation, quality, format, page=None):
    """Build a URL for the Cantaloupe server."""
    # Get the file path for the record
    file_path = self._get_file_path(record_id, filename)
    
    # ┌───────────────────────────────────────────────────────────┐
    # │ CRITICAL: Encode slashes in the path for Cantaloupe       │
    # │ This is the key to making PDF support work                │
    # └───────────────────────────────────────────────────────────┘
    encoded_path = file_path.replace("/", "%2F")
    
    # Create the URL with proper encoding
    if region == "info.json":
        url = f"{self.base_url}/iiif/2/{encoded_path}/info.json"
    else:
        url = f"{self.base_url}/iiif/2/{encoded_path}/{region}/{size}/{rotation}/{quality}.{format}"
    
    # ┌───────────────────────────────────────────────────────────┐
    # │ PDF SPECIFIC: Add page parameter for PDF files            │
    # │ This tells Cantaloupe which page to extract               │
    # └───────────────────────────────────────────────────────────┘
    if page is not None and self._is_pdf(filename):
        url += f"?page={page}"
    
    return url
```

### Detecting Number of Pages

```python
# ┌───────────────────────────────────────────────────────────┐
# │ PDF SPECIFIC: Determine the number of pages in a PDF      │
# │ The 'tiles' array in info.json typically contains one     │
# │ entry per page                                            │
# └───────────────────────────────────────────────────────────┘
def get_pdf_page_count(pdf_info):
    """Determine the number of pages in a PDF from its info.json."""
    num_pages = 0
    
    # First try the 'tiles' array which usually has one entry per page
    if 'tiles' in pdf_info and isinstance(pdf_info['tiles'], list):
        num_pages = len(pdf_info['tiles'])
    
    # If that doesn't work, try the 'sizes' array
    elif 'sizes' in pdf_info and isinstance(pdf_info['sizes'], list):
        num_pages = len(pdf_info['sizes'])
    
    # If none of the above methods work, default to 1 page
    if num_pages <= 0:
        num_pages = 1
        
    return num_pages
```

### Testing with curl (Command Line)

```bash
# ┌───────────────────────────────────────────────────────────┐
# │ STEP 1: Get PDF metadata (info.json)                      │
# └───────────────────────────────────────────────────────────┘
curl "http://localhost:8182/iiif/2/private%2F212%2Fdocument.pdf/info.json"

# ┌───────────────────────────────────────────────────────────┐
# │ STEP 2: Get specific page as an image                     │
# │ Notice the page=1 parameter for page selection            │
# └───────────────────────────────────────────────────────────┘
curl "http://localhost:8182/iiif/2/private%2F212%2Fdocument.pdf/full/full/0/default.jpg?page=1" -o page1.jpg

# ┌───────────────────────────────────────────────────────────┐
# │ STEP 3: Get a thumbnail of a specific page                │
# │ Use the size parameter (200,) to specify width            │
# └───────────────────────────────────────────────────────────┘
curl "http://localhost:8182/iiif/2/private%2F212%2Fdocument.pdf/full/200,/0/default.jpg?page=1" -o thumb1.jpg
```

## Visual Comparison of URL Formats

| URL Type | Format |
|----------|--------|
| PDF info.json | `http://localhost:8182/iiif/2/private%2F212%2Fdocument.pdf/info.json` |
| PDF page | `http://localhost:8182/iiif/2/private%2F212%2Fdocument.pdf/full/full/0/default.jpg?page=1` |
| Image info.json | `http://localhost:8182/iiif/2/private%2F212%2Fimage.jpg/info.json` |
| Image region | `http://localhost:8182/iiif/2/private%2F212%2Fimage.jpg/full/full/0/default.jpg` |

### URL Structure

```
┌─────────────────┬────────┬──────────────────────────────┬────────┬─────┬─────────┬──────────┬────────┐
│ Server          │ Base   │ Identifier                   │ Region │ Size│ Rotation│ Quality  │ Format │
├─────────────────┼────────┼──────────────────────────────┼────────┼─────┼─────────┼──────────┼────────┤
│ http://host:port│/iiif/2/│ private%2F212%2Fdocument.pdf │/full   │/full│/0       │/default  │.jpg    │
└─────────────────┴────────┴──────────────────────────────┴────────┴─────┴─────────┴──────────┴────────┘
                                                                                               ┌────────┐
                                                                                               │?page=1 │
                                                                                               └────────┘
```

## Summary of PDF IIIF Integration

- PDF files are served directly through Cantaloupe IIIF server
- Slashes in file paths must be URL-encoded as `%2F`
- PDF pages are accessed using the `?page=N` parameter
- Manifest generation requires detecting the number of pages
- All IIIF Image API features work with PDF pages (resize, crop, rotate, etc.)
- PDF integration enables viewing PDFs in any IIIF-compatible viewer 
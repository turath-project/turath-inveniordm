# Technical Details: IIIF Manifest Generation and Cantaloupe Integration

## IIIF Manifest Structure

The IIIF manifest for each book needs to follow the Presentation API 2.1 specification and include:

1. **Basic Metadata**:
   ```json
   {
     "@context": "http://iiif.io/api/presentation/2/context.json",
     "@id": "https://your-server.com/record-id/manifest.json",
     "@type": "sc:Manifest",
     "label": "Book Title",
     "viewingDirection": "right-to-left",  // For Arabic books
     "metadata": [
       { "label": "Author", "value": "Author Name" },
       { "label": "Date", "value": "Publication Date" }
     ]
   }
   ```

2. **Canvas for Each Page**:
   ```json
   "sequences": [{
     "@type": "sc:Sequence",
     "canvases": [
       {
         "@id": "https://your-server.com/record-id/manifest.json/canvas/p001",
         "@type": "sc:Canvas",
         "label": "p. 001",
         "width": 800,
         "height": 1200,
         "images": [{
           "@type": "oa:Annotation",
           "motivation": "sc:painting",
           "on": "https://your-server.com/record-id/manifest.json/canvas/p001",
           "resource": {
             "@id": "https://localhost:8182/iiif/3/record-id.pdf/full/full/0/default.jpg?page=1",
             "@type": "dctypes:Image",
             "width": 800,
             "height": 1200
           }
         }],
         "scaleFactor": 0.5  // Added for text annotation alignment
       }
     ]
   }]
   ```

3. **Services for Search and Annotations**:
   ```json
   "service": [{
     "@context": "http://iiif.io/api/search/0/context.json",
     "@id": "https://search-server.com/search",
     "profile": "http://iiif.io/api/search/0/search",
     "label": "Search within this manifest"
   }]
   ```

## Cantaloupe URL Format

The URL format for accessing PDF pages via Cantaloupe is:

```
https://localhost:8182/iiif/3/{identifier}/full/full/0/default.jpg?page={page_number}
```

Where:
- `{identifier}` is typically the record ID or filename of the PDF
- `{page_number}` is the 1-based page index in the PDF

For example:
```
https://localhost:8182/iiif/3/record-123.pdf/full/full/0/default.jpg?page=1
```

## Scale Factor Calculation

The scale factor is crucial for proper alignment of text annotations and highlights. It's calculated as:

```python
def calculate_scale_factor(hocr_dim, cantaloupe_dim):
    hocr_width, hocr_height = hocr_dim
    cantaloupe_width, cantaloupe_height = cantaloupe_dim
    
    width_ratio = cantaloupe_width / hocr_width
    height_ratio = cantaloupe_height / hocr_height
    
    # Use average for more balanced scaling
    return (width_ratio + height_ratio) / 2
```

## Workflow for Generating Manifests

1. **Book Upload**:
   - Upload PDF to InvenioRDM using `upload_book.py`
   - Get the record ID from the upload response

2. **Generate Manifest**:
   - Call `generate_manifest.py` with the book directory
   - Pass the record ID to be used in the manifest

3. **URL Construction**:
   - Build Cantaloupe URLs using the record ID
   - Format: `https://localhost:8182/iiif/3/{record_id}.pdf/full/full/0/default.jpg?page={page_number}`

4. **Manifest Upload**:
   - Upload the generated manifest back to the record
   - Set the custom field `iiif.manifest` to point to the manifest URL

## HTTPS and CORS Requirements

1. **HTTPS Configuration for Cantaloupe**:
   - Cantaloupe must be configured with valid HTTPS certificates
   - All URLs in the manifest must use HTTPS

2. **CORS Headers**:
   - Cantaloupe needs to allow cross-origin requests:
     ```
     Access-Control-Allow-Origin: *
     Access-Control-Allow-Methods: GET, OPTIONS
     Access-Control-Allow-Headers: Content-Type, Authorization
     ```

## Testing the Image Server

To test if Cantaloupe is correctly serving PDF pages:

1. Direct URL access:
   ```
   https://localhost:8182/iiif/3/test.pdf/full/full/0/default.jpg?page=1
   ```

2. Info.json request:
   ```
   https://localhost:8182/iiif/3/test.pdf/info.json?page=1
   ```

3. IIIF Image API parameters:
   ```
   # Full page at 50% size
   https://localhost:8182/iiif/3/test.pdf/full/pct:50/0/default.jpg?page=1
   
   # Region of the page (x,y,width,height)
   https://localhost:8182/iiif/3/test.pdf/100,100,400,400/full/0/default.jpg?page=1
   ```

## Common Issues and Solutions

1. **Mixed Content Errors**:
   - Ensure all URLs in the manifest use HTTPS
   - Check for any hardcoded HTTP URLs in the manifest generation code

2. **CORS Errors**:
   - Verify Cantaloupe is configured with proper CORS headers
   - Test with browsers' CORS debugging tools

3. **PDF Page Rendering Issues**:
   - Verify Cantaloupe can handle the PDF format and version
   - Check for any PDF encryption or DRM that might prevent page extraction

4. **Scale Factor Inaccuracies**:
   - Test with various PDF resolutions and formats
   - Manually verify text highlight alignment on different pages 
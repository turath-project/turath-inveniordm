# Understanding IIIF Manifest Generation in Zenodo-RDM

This document provides a comprehensive explanation of how the Zenodo-RDM system generates IIIF (International Image Interoperability Framework) manifests for image collections. IIIF manifests are crucial for enabling advanced image viewing capabilities through viewers like Mirador.

## Table of Contents

1. [Overview of IIIF Manifest Generation](#overview-of-iiif-manifest-generation)
2. [Key Components Involved](#key-components-involved)
3. [Manifest Structure and Generation Process](#manifest-structure-and-generation-process)
4. [URL Structure and Routing](#url-structure-and-routing)
5. [Integration with IIPServer](#integration-with-iipserver)
6. [Testing IIIF Manifest Generation](#testing-iiif-manifest-generation)
7. [Troubleshooting Common Issues](#troubleshooting-common-issues)

## Overview of IIIF Manifest Generation

After images are uploaded to Zenodo-RDM and converted to Pyramid TIFF (PTIF) format, the system needs to generate IIIF manifests that describe these images in a standardized way. The IIIF Presentation API defines how these manifests should be structured to enable interoperability between different image repositories and viewers.

```
┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
│                 │  Request  │                 │  Retrieves│                 │
│  Mirador Viewer │─────────►│  IIIF Resource  │─────────►│  Record Service  │
│                 │           │  Endpoints      │           │                 │
└─────────────────┘           └─────────────────┘           └─────────────────┘
        ▲                            │                             │
        │                            │                             │
        │                            ▼                             ▼
        │                     ┌─────────────────┐         ┌─────────────────┐
        │                     │                 │         │                 │
        │    JSON-LD Manifest │  IIIF Schema   │         │  Files Service  │
        └─────────────────────│  Serializers   │◄────────│                 │
                              │                 │         │                 │
                              └─────────────────┘         └─────────────────┘
                                                                  │
                                                                  │
                                                                  ▼
                                                          ┌─────────────────┐
                                                          │                 │
                                                          │  PTIF Files     │
                                                          │  (via IIPServer)│
                                                          │                 │
                                                          └─────────────────┘
```

## Key Components Involved

The IIIF manifest generation system in Zenodo-RDM consists of several key components:

### 1. IIIF Resource

The `IIIFResource` class (`invenio_rdm_records/resources/iiif.py`) defines the HTTP endpoints that handle IIIF requests, including:

- **Manifest endpoint**: `/iiif/<uuid>/manifest`
- **Sequence endpoint**: `/iiif/<uuid>/sequence/default`
- **Canvas endpoint**: `/iiif/<uuid>/canvas/<file_name>`
- **Image API endpoints**: `/iiif/<uuid>/<region>/<size>/<rotation>/<quality>.<format>`

This resource handles routing, access control, and response formatting.

### 2. IIIF Schemas

The schema classes in `invenio_rdm_records/resources/serializers/iiif/schema.py` define how record and file data is mapped to IIIF JSON-LD structures:

- **IIIFManifestV2Schema**: Maps record metadata to a IIIF manifest structure
- **IIIFSequenceV2Schema**: Defines sequence ordering for images
- **IIIFCanvasV2Schema**: Maps file metadata to canvases 
- **IIIFImageV2Schema**: Handles image annotations
- **IIIFImageResourceV2Schema**: Describes image resources

These schemas use Marshmallow to transform Python objects into standardized IIIF JSON-LD.

### 3. IIIF Serializers

The serializers in `invenio_rdm_records/resources/serializers/iiif/__init__.py` wrap the schemas to handle content serialization:

- **IIIFManifestV2JSONSerializer**
- **IIIFSequenceV2JSONSerializer**
- **IIIFCanvasV2JSONSerializer**
- **IIIFInfoV2JSONSerializer**

### 4. IIIF Service

The `IIIFService` class (`invenio_rdm_records/services/iiif/service.py`) bridges between the resource layer and the data layer, providing:

- Record and file retrieval
- Image processing for the IIIF Image API
- Integration with image libraries (PyVIPS or ImageMagick)

### 5. IIPServer Proxy

The `IIPServerProxy` class handles redirection of image requests to the IIPServer, which serves the actual image tiles from PTIF files.

## Manifest Structure and Generation Process

### IIIF Manifest Structure

A IIIF manifest in Zenodo-RDM follows the IIIF Presentation API 2.1 specification and has this basic structure:

```json
{
  "@context": "http://iiif.io/api/presentation/2/context.json",
  "@type": "sc:Manifest",
  "@id": "https://example.org/api/iiif/record:123/manifest",
  "label": "Record Title",
  "metadata": [
    {"label": "Publication Date", "value": "2023-01-01"}
  ],
  "description": "Record description",
  "license": "https://creativecommons.org/licenses/...",
  "sequences": [
    {
      "@id": "https://example.org/api/iiif/record:123/sequence/default",
      "@type": "sc:Sequence",
      "label": "Current Page Order",
      "viewingDirection": "left-to-right",
      "viewingHint": "individuals",
      "canvases": [
        {
          "@id": "https://example.org/api/iiif/record:123/canvas/image1.jpg",
          "@type": "sc:Canvas",
          "label": "image1.jpg",
          "height": 2000,
          "width": 3000,
          "images": [
            {
              "@context": "http://iiif.io/api/presentation/2/context.json",
              "@id": "https://example.org/api/iiif/record:123/annotation/image1.jpg",
              "@type": "oa:Annotation",
              "motivation": "sc:painting",
              "resource": {
                "@id": "https://example.org/api/iiif/record:123:image1.jpg/full/full/0/default.jpg",
                "@type": "dctypes:Image",
                "format": "image/jpeg",
                "height": 2000,
                "width": 3000,
                "service": {
                  "@context": "http://iiif.io/api/image/2/context.json",
                  "@id": "https://example.org/api/iiif/record:123:image1.jpg",
                  "profile": "http://iiif.io/api/image/2/level1.json"
                }
              },
              "on": "https://example.org/api/iiif/record:123/canvas/image1.jpg"
            }
          ]
        },
        // Additional canvases...
      ]
    }
  ]
}
```

### Generation Process

The manifest generation process follows these steps:

1. **Request Handling**: When a client requests `/api/iiif/record:123/manifest`, the request is routed to the `IIIFResource.manifest()` method.

2. **Record Retrieval**: The `IIIFService.read_record()` method retrieves the record and its associated files.

3. **File Filtering**: The `ListIIIFFilesAttribute` class filters files based on:
   - File extensions (configured in `RDM_IIIF_MANIFEST_FORMATS`)
   - Minimum dimensions (tile width/height defined in `IIIF_TILES_CONVERTER_PARAMS`)

4. **Schema Transformation**: The record and its files are passed through the schema classes to transform them into IIIF JSON-LD structures. This includes:
   - Mapping record metadata to manifest metadata
   - Creating sequence ordering for the images
   - Transforming file metadata to canvases
   - Generating proper IIIF URLs for images

5. **Response Serialization**: The final manifest is serialized as JSON-LD with the appropriate content type and CORS headers.

## URL Structure and Routing

Zenodo-RDM uses a specific URL structure for IIIF resources:

### For Record-Level Endpoints

- **Manifest**: `/api/iiif/record:{record_id}/manifest`
- **Sequence**: `/api/iiif/record:{record_id}/sequence/default`
- **Canvas**: `/api/iiif/record:{record_id}/canvas/{filename}`

### For Image-Level Endpoints

- **Image Base**: `/api/iiif/record:{record_id}:{filename}`
- **Image Info**: `/api/iiif/record:{record_id}:{filename}/info.json`
- **Image API**: `/api/iiif/record:{record_id}:{filename}/{region}/{size}/{rotation}/{quality}.{format}`

When requests for image tiles are made, they are typically proxied to the IIPServer which actually serves the PTIF files.

## Integration with IIPServer

The integration between the IIIF manifest generation and the IIPServer is handled through the `IIPServerProxy` class, which:

1. Determines if a request should be proxied (typically image API requests)
2. Rewrites the URL to match the IIPServer's expected format
3. Forwards the request to the IIPServer
4. Returns the response from the IIPServer to the client

The proxy rewrites the URL from:
```
/api/iiif/record:1234:image.png/full/200,/0/default.jpg
```

To:
```
/iip?IIIF=/12/34/_/image.png.ptif/full/200,/0/default.jpg
```

This mapping takes the record ID and splits it into a directory structure that matches how the PTIF files are stored.

## Testing IIIF Manifest Generation

To test IIIF manifest generation, follow these steps:

### Prerequisites

Before testing manifest generation, ensure:

1. You have a record with image files in Zenodo-RDM
2. The PTIF conversion process has completed successfully
3. The IIPServer is running and properly configured

### Step 1: Test Manifest Endpoint

Request the manifest JSON for a record:

```bash
curl -H "Accept: application/json" http://localhost:5001/api/iiif/record:{record_id}/manifest
```

The response should be a valid IIIF manifest with:
- Proper metadata (title, publication date)
- A sequence with one or more canvases
- Image annotations with appropriate URLs

### Step 2: Validate Canvas Endpoints

For each image file in the record, test the canvas endpoint:

```bash
curl -H "Accept: application/json" http://localhost:5001/api/iiif/record:{record_id}/canvas/{filename}
```

The response should be a valid IIIF canvas JSON structure.

### Step 3: Test Image Info Endpoint

For an individual image, test the info endpoint:

```bash
curl -H "Accept: application/json" http://localhost:5001/api/iiif/record:{record_id}:{filename}/info.json
```

The response should include image dimensions and service information.

### Step 4: Test Image API Endpoints

Test retrieving an image at different sizes and regions:

```bash
# Full image
curl -o test_full.jpg http://localhost:5001/api/iiif/record:{record_id}:{filename}/full/full/0/default.jpg

# Thumbnail
curl -o test_thumb.jpg http://localhost:5001/api/iiif/record:{record_id}:{filename}/full/200,/0/default.jpg

# Region
curl -o test_region.jpg http://localhost:5001/api/iiif/record:{record_id}:{filename}/100,100,500,500/full/0/default.jpg
```

### Step 5: Test with Mirador Viewer

To test the full viewing experience:

1. Access the record detail page through the web interface
2. Click on an image file to open the Mirador viewer
3. Verify that the viewer loads the manifest correctly
4. Test zooming, panning, and multi-image navigation

## Troubleshooting Common Issues

### 1. Missing Files in Manifest

**Problem**: The manifest doesn't include all expected image files.

**Possible Causes**:
- Files don't meet the minimum dimension requirements
- File extensions aren't in the `RDM_IIIF_MANIFEST_FORMATS` configuration
- PTIF conversion hasn't completed successfully

**Solutions**:
- Check file dimensions and supported formats in the configuration
- Verify PTIF conversion status in the record's `media_files` entries
- Look for errors in the worker logs related to tile generation

### 2. Invalid Manifest Structure

**Problem**: The manifest doesn't follow the IIIF specification.

**Possible Causes**:
- Schema mapping issues
- Missing metadata
- Issues with URL generation

**Solutions**:
- Validate the manifest against the IIIF specification using tools like the [IIIF Validator](https://iiif.io/api/presentation/validator/)
- Check for schema changes in the codebase
- Ensure all required fields are present in the record metadata

### 3. Image Loading Failures

**Problem**: Images don't load in the Mirador viewer.

**Possible Causes**:
- IIPServer configuration issues
- Proxy redirection failures
- CORS headers missing

**Solutions**:
- Test direct image API requests to isolate the issue
- Check IIPServer logs for errors
- Verify CORS headers are being properly set
- Check URL rewriting in the `IIPServerProxy` class

### 4. Performance Issues

**Problem**: Manifest generation or image loading is slow.

**Possible Causes**:
- Large number of images in a record
- Inefficient image processing
- Missing caching

**Solutions**:
- Consider implementing caching for manifests
- Optimize image processing settings
- Monitor database and service performance

## Conclusion

The IIIF manifest generation in Zenodo-RDM is a sophisticated system that transforms record and file metadata into standardized IIIF structures. By understanding the components and processes involved, you can effectively test, troubleshoot, and extend the IIIF capabilities of the system.

This system builds upon the PTIF conversion process and IIPServer components we've previously explored, forming a complete pipeline from image upload to interactive viewing in the Mirador interface. 


## Understanding IIIF Manifest Generation in Zenodo-RDM

The IIIF manifest generation in Zenodo-RDM is handled through a well-structured system involving several components:

1. **IIIF Resource and Routes**: The system defines API endpoints that follow the IIIF Presentation API specification. These routes handle manifest, sequence, canvas, and image API requests.

2. **Schema-based Serialization**: The manifest structure is defined using Marshmallow schemas, which map record and file data to the IIIF JSON-LD format.

3. **Proxy Mechanism**: There's a proxy mechanism that redirects certain IIIF requests (like image tiles) to the IIPServer for efficient image serving.

4. **Integration with Record and File Services**: The IIIF service interacts with the record and file services to access the necessary data.

Now, I'm going to explain how I plan to approach testing the IIIF manifest generation:

## Testing Plan for IIIF Manifest Generation

I'll create a comprehensive testing approach that builds on our previous work with the IIPServer component:

1. **First, I'll verify prerequisites**:
   - Confirm we have a record with image files
   - Ensure that PTIF conversion has successfully completed

2. **Then, I'll test the manifest generation**:
   - Request the IIIF manifest JSON for a record
   - Analyze the structure to ensure it conforms to the IIIF specification
   - Verify that all expected canvases are present
   - Check that image URLs are correctly formed

3. **Next, I'll test individual components**:
   - Test canvas endpoints for individual files
   - Test sequence endpoints
   - Verify image info endpoints

4. **Finally, I'll demonstrate integration with the Mirador viewer**:
   - Show how the generated manifest is consumed by Mirador
   - Test the end-to-end viewing experience

This approach will enable us to systematically validate the manifest generation process while building on our understanding of the PTIF conversion and IIPServer components.

## Implementation Steps

1. I'll create a new document that explains the IIIF manifest generation process
2. I'll develop step-by-step testing procedures
3. I'll document common issues and solutions
4. I'll create examples showing manifest structure and usage



# Testing IIIF Manifest Generation in Zenodo-RDM

This document provides a comprehensive testing guide for the IIIF manifest generation process in Zenodo-RDM, including Python test scripts that can be used to validate the system's functionality.

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Test Scripts](#test-scripts)
   - [Basic Manifest Validation](#basic-manifest-validation)
   - [Schema Compliance Test](#schema-compliance-test)
   - [Multi-Image Canvas Test](#multi-image-canvas-test)
   - [URL Structure Test](#url-structure-test)
   - [Access Control Test](#access-control-test)
4. [Integration Testing](#integration-testing)
5. [Performance Testing](#performance-testing)
6. [Test Execution Guidelines](#test-execution-guidelines)
7. [Testing Findings](#testing-findings)

## Introduction

IIIF manifest generation is a critical component of the Zenodo-RDM image viewing system. These manifests provide standardized metadata and image references that the Mirador viewer uses to display images with advanced features like zooming, panning, and annotation.

The tests in this document are designed to verify:
- Manifest structure and content correctness
- IIIF API compliance
- URL patterns and routing
- Integration with the IIPServer component
- Error handling and fallback mechanisms

## Prerequisites

Before running these tests, ensure you have:

1. A running instance of Zenodo-RDM with the IIPServer component
2. At least one record with image files that have completed PTIF conversion
3. The proper dependencies installed:

```bash
pip install pytest requests Pillow jsonschema
```

4. Authentication credentials if testing with protected resources

## Test Scripts

### Basic Manifest Validation

This script tests that manifest endpoints return valid JSON-LD IIIF manifests with the expected structure.

```python
# test_iiif_manifest_basic.py

import pytest
import requests
import json
import os

# Configuration
BASE_URL = os.environ.get("ZENODO_BASE_URL", "http://localhost:5001")
RECORD_ID = os.environ.get("TEST_RECORD_ID", "YOUR_RECORD_ID")  # Replace with a real record ID

def test_manifest_endpoint():
    """Test that the manifest endpoint returns a valid IIIF manifest."""
    url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}/manifest"
    response = requests.get(url, headers={"Accept": "application/json"})
    
    assert response.status_code == 200, f"Manifest request failed with status {response.status_code}"
    
    # Parse the response as JSON
    manifest = response.json()
    
    # Check for required IIIF manifest fields
    assert "@context" in manifest, "Manifest missing @context field"
    assert "@type" in manifest, "Manifest missing @type field"
    assert manifest["@type"] == "sc:Manifest", f"Incorrect manifest type: {manifest['@type']}"
    assert "label" in manifest, "Manifest missing label field"
    assert "sequences" in manifest, "Manifest missing sequences field"
    
    # Check that we have at least one sequence
    assert len(manifest["sequences"]) > 0, "Manifest has no sequences"
    
    # Check that the sequence has canvases
    sequence = manifest["sequences"][0]
    assert "canvases" in sequence, "Sequence missing canvases field"
    assert len(sequence["canvases"]) > 0, "Sequence has no canvases"
    
    # Check basic canvas structure for the first canvas
    canvas = sequence["canvases"][0]
    assert "@id" in canvas, "Canvas missing @id field"
    assert "@type" in canvas, "Canvas missing @type field"
    assert canvas["@type"] == "sc:Canvas", f"Incorrect canvas type: {canvas['@type']}"
    assert "label" in canvas, "Canvas missing label field"
    assert "width" in canvas, "Canvas missing width field"
    assert "height" in canvas, "Canvas missing height field"
    assert "images" in canvas, "Canvas missing images field"
    
    # Check image annotation structure
    assert len(canvas["images"]) > 0, "Canvas has no image annotations"
    image = canvas["images"][0]
    assert "@type" in image, "Image annotation missing @type field"
    assert image["@type"] == "oa:Annotation", f"Incorrect annotation type: {image['@type']}"
    assert "motivation" in image, "Image annotation missing motivation field"
    assert "resource" in image, "Image annotation missing resource field"
    
    # Check image resource structure
    resource = image["resource"]
    assert "@id" in resource, "Image resource missing @id field"
    assert "service" in resource, "Image resource missing service field"
    
    # Check service structure
    service = resource["service"]
    assert "@context" in service, "Service missing @context field"
    assert "@id" in service, "Service missing @id field"
    assert "profile" in service, "Service missing profile field"
    
    print(f"Successfully validated manifest for record {RECORD_ID}")
```

### Schema Compliance Test

This script verifies that the manifest complies with the IIIF Presentation API schema.

```python
# test_iiif_schema_compliance.py

import pytest
import requests
import json
import jsonschema
import os
from pathlib import Path

# Configuration
BASE_URL = os.environ.get("ZENODO_BASE_URL", "http://localhost:5001")
RECORD_ID = os.environ.get("TEST_RECORD_ID", "YOUR_RECORD_ID")  # Replace with a real record ID

# IIIF schema URL - can be downloaded if needed
IIIF_SCHEMA_URL = "https://iiif.io/api/presentation/2.1/presentation-api.json"

def get_iiif_schema():
    """Get the IIIF Presentation API 2.1 schema."""
    cache_path = Path("iiif_schema.json")
    
    # Use cached schema if available
    if cache_path.exists():
        with open(cache_path, "r") as f:
            return json.load(f)
    
    # Otherwise download the schema
    response = requests.get(IIIF_SCHEMA_URL)
    schema = response.json()
    
    # Cache the schema for future use
    with open(cache_path, "w") as f:
        json.dump(schema, f)
    
    return schema

def test_schema_compliance():
    """Test that the manifest complies with the IIIF schema."""
    url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}/manifest"
    response = requests.get(url, headers={"Accept": "application/json"})
    
    assert response.status_code == 200, f"Manifest request failed with status {response.status_code}"
    
    # Get the manifest
    manifest = response.json()
    
    # Get the schema
    schema = get_iiif_schema()
    
    # Validate the manifest against the schema
    try:
        jsonschema.validate(manifest, schema)
        print(f"Manifest for record {RECORD_ID} complies with IIIF Presentation API 2.1 schema")
    except jsonschema.exceptions.ValidationError as e:
        pytest.fail(f"Manifest does not comply with IIIF schema: {e}")
```

### Multi-Image Canvas Test

This script tests that records with multiple images correctly generate a manifest with multiple canvases.

```python
# test_iiif_multi_image.py

import pytest
import requests
import json
import os

# Configuration
BASE_URL = os.environ.get("ZENODO_BASE_URL", "http://localhost:5001")
RECORD_ID = os.environ.get("TEST_RECORD_ID", "YOUR_RECORD_ID")  # Replace with a multi-image record ID

def test_multi_image_canvases():
    """Test that records with multiple images correctly generate multiple canvases."""
    url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}/manifest"
    response = requests.get(url, headers={"Accept": "application/json"})
    
    assert response.status_code == 200, f"Manifest request failed with status {response.status_code}"
    
    # Get the manifest
    manifest = response.json()
    
    # Check that we have sequences
    assert "sequences" in manifest, "Manifest missing sequences field"
    assert len(manifest["sequences"]) > 0, "Manifest has no sequences"
    
    # Get the canvases
    sequence = manifest["sequences"][0]
    assert "canvases" in sequence, "Sequence missing canvases field"
    canvases = sequence["canvases"]
    
    # We should have at least one canvas
    assert len(canvases) > 0, "Sequence has no canvases"
    
    # Print information about the canvases
    print(f"Found {len(canvases)} canvases in manifest for record {RECORD_ID}")
    
    # Check each canvas has required fields
    canvas_ids = []
    for i, canvas in enumerate(canvases):
        assert "@id" in canvas, f"Canvas {i} missing @id field"
        assert "label" in canvas, f"Canvas {i} missing label field"
        assert "images" in canvas, f"Canvas {i} missing images field"
        assert len(canvas["images"]) > 0, f"Canvas {i} has no image annotations"
        
        canvas_ids.append(canvas["@id"])
    
    # Check that all canvas IDs are unique
    assert len(canvas_ids) == len(set(canvas_ids)), "Duplicate canvas IDs found"
    
    # Test individual canvas endpoints
    for canvas_id in canvas_ids:
        # Extract filename from canvas ID
        filename = canvas_id.split("/")[-1]
        canvas_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}/canvas/{filename}"
        
        canvas_response = requests.get(canvas_url, headers={"Accept": "application/json"})
        assert canvas_response.status_code == 200, f"Canvas request failed for {filename}"
        
        canvas_data = canvas_response.json()
        assert "@id" in canvas_data, "Canvas response missing @id field"
        assert canvas_data["@id"] == canvas_id, "Canvas ID mismatch"
```

### URL Structure Test

This script validates the URL structure and routing for IIIF resources.

```python
# test_iiif_url_structure.py

import pytest
import requests
from PIL import Image
import io
import os
import re

# Configuration
BASE_URL = os.environ.get("ZENODO_BASE_URL", "http://localhost:5001")
RECORD_ID = os.environ.get("TEST_RECORD_ID", "YOUR_RECORD_ID")  # Replace with a real record ID

def test_url_structure():
    """Test that IIIF URLs follow the expected structure and routing."""
    # First get the manifest to find an image filename
    manifest_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}/manifest"
    manifest_response = requests.get(manifest_url, headers={"Accept": "application/json"})
    
    assert manifest_response.status_code == 200, f"Manifest request failed with status {manifest_response.status_code}"
    
    manifest = manifest_response.json()
    
    # Get the first canvas
    sequence = manifest["sequences"][0]
    canvas = sequence["canvases"][0]
    
    # Extract the filename from the canvas ID
    canvas_id = canvas["@id"]
    filename_match = re.search(r'/canvas/(.+)$', canvas_id)
    assert filename_match, f"Could not extract filename from canvas ID: {canvas_id}"
    
    filename = filename_match.group(1)
    
    # Test the sequence endpoint
    sequence_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}/sequence/default"
    sequence_response = requests.get(sequence_url, headers={"Accept": "application/json"})
    assert sequence_response.status_code == 200, f"Sequence request failed with status {sequence_response.status_code}"
    
    # Test the canvas endpoint
    canvas_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}/canvas/{filename}"
    canvas_response = requests.get(canvas_url, headers={"Accept": "application/json"})
    assert canvas_response.status_code == 200, f"Canvas request failed with status {canvas_response.status_code}"
    
    # Test the image info endpoint
    info_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}:{filename}/info.json"
    info_response = requests.get(info_url, headers={"Accept": "application/json"})
    assert info_response.status_code == 200, f"Image info request failed with status {info_response.status_code}"
    
    # Test the image API endpoints with different parameters
    
    # 1. Full image
    full_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}:{filename}/full/full/0/default.jpg"
    full_response = requests.get(full_url)
    assert full_response.status_code == 200, f"Full image request failed with status {full_response.status_code}"
    assert full_response.headers.get('Content-Type', '').startswith('image/'), "Full image response is not an image"
    
    # 2. Thumbnail (width = 200px)
    thumb_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}:{filename}/full/200,/0/default.jpg"
    thumb_response = requests.get(thumb_url)
    assert thumb_response.status_code == 200, f"Thumbnail request failed with status {thumb_response.status_code}"
    
    # Verify thumbnail dimensions
    thumb_img = Image.open(io.BytesIO(thumb_response.content))
    assert thumb_img.width <= 200, f"Thumbnail width ({thumb_img.width}) exceeds 200px"
    
    # 3. Region
    region_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}:{filename}/100,100,300,300/full/0/default.jpg"
    region_response = requests.get(region_url)
    assert region_response.status_code == 200, f"Region request failed with status {region_response.status_code}"
    
    # 4. Rotation
    rotation_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}:{filename}/full/full/90/default.jpg"
    rotation_response = requests.get(rotation_url)
    assert rotation_response.status_code == 200, f"Rotation request failed with status {rotation_response.status_code}"
    
    print(f"Successfully validated IIIF URL structure for record {RECORD_ID}")
```

### Access Control Test

This script tests that access controls are correctly applied to IIIF resources.

```python
# test_iiif_access_control.py

import pytest
import requests
import os

# Configuration
BASE_URL = os.environ.get("ZENODO_BASE_URL", "http://localhost:5001")
PUBLIC_RECORD_ID = os.environ.get("PUBLIC_RECORD_ID", "YOUR_PUBLIC_RECORD_ID")  # Replace with a public record ID
RESTRICTED_RECORD_ID = os.environ.get("RESTRICTED_RECORD_ID", "YOUR_RESTRICTED_RECORD_ID")  # Replace with a restricted record ID
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")  # Token with access to the restricted record

def test_public_access():
    """Test access to public IIIF resources."""
    # Test manifest access
    manifest_url = f"{BASE_URL}/api/iiif/record:{PUBLIC_RECORD_ID}/manifest"
    manifest_response = requests.get(manifest_url, headers={"Accept": "application/json"})
    assert manifest_response.status_code == 200, f"Public manifest request failed with status {manifest_response.status_code}"
    
    # Get a filename from the manifest
    manifest = manifest_response.json()
    sequence = manifest["sequences"][0]
    canvas = sequence["canvases"][0]
    filename = canvas["@id"].split("/")[-1]
    
    # Test image access
    image_url = f"{BASE_URL}/api/iiif/record:{PUBLIC_RECORD_ID}:{filename}/full/full/0/default.jpg"
    image_response = requests.get(image_url)
    assert image_response.status_code == 200, f"Public image request failed with status {image_response.status_code}"

def test_restricted_access_without_auth():
    """Test that restricted resources require authentication."""
    # Test manifest access
    manifest_url = f"{BASE_URL}/api/iiif/record:{RESTRICTED_RECORD_ID}/manifest"
    manifest_response = requests.get(manifest_url, headers={"Accept": "application/json"})
    assert manifest_response.status_code in [401, 403], f"Restricted manifest should require auth, got {manifest_response.status_code}"

def test_restricted_access_with_auth():
    """Test access to restricted resources with authentication."""
    if not AUTH_TOKEN:
        pytest.skip("No auth token provided, skipping authenticated test")
    
    # Test manifest access with auth
    manifest_url = f"{BASE_URL}/api/iiif/record:{RESTRICTED_RECORD_ID}/manifest"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}"
    }
    manifest_response = requests.get(manifest_url, headers=headers)
    assert manifest_response.status_code == 200, f"Authenticated manifest request failed with status {manifest_response.status_code}"
    
    # Get a filename from the manifest
    manifest = manifest_response.json()
    sequence = manifest["sequences"][0]
    canvas = sequence["canvases"][0]
    filename = canvas["@id"].split("/")[-1]
    
    # Test image access with auth
    image_url = f"{BASE_URL}/api/iiif/record:{RESTRICTED_RECORD_ID}:{filename}/full/full/0/default.jpg"
    image_response = requests.get(image_url, headers={"Authorization": f"Bearer {AUTH_TOKEN}"})
    assert image_response.status_code == 200, f"Authenticated image request failed with status {image_response.status_code}"
```

## Integration Testing

The following script tests the integration between the IIIF manifest generation and the IIPServer.

```python
# test_iiif_iipserver_integration.py

import pytest
import requests
import re
import os

# Configuration
BASE_URL = os.environ.get("ZENODO_BASE_URL", "http://localhost:5001")
RECORD_ID = os.environ.get("TEST_RECORD_ID", "YOUR_RECORD_ID")  # Replace with a real record ID

def test_iipserver_integration():
    """Test integration between IIIF manifest generation and IIPServer."""
    # First get the manifest to find an image
    manifest_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}/manifest"
    manifest_response = requests.get(manifest_url, headers={"Accept": "application/json"})
    
    assert manifest_response.status_code == 200, f"Manifest request failed with status {manifest_response.status_code}"
    
    manifest = manifest_response.json()
    
    # Get the first canvas
    sequence = manifest["sequences"][0]
    canvas = sequence["canvases"][0]
    
    # Extract the filename from the canvas ID
    canvas_id = canvas["@id"]
    filename_match = re.search(r'/canvas/(.+)$', canvas_id)
    assert filename_match, f"Could not extract filename from canvas ID: {canvas_id}"
    
    filename = filename_match.group(1)
    
    # Test image info from IIPServer
    info_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}:{filename}/info.json"
    info_response = requests.get(info_url, headers={"Accept": "application/json"})
    assert info_response.status_code == 200, f"Image info request failed with status {info_response.status_code}"
    
    # Verify info content (should come from IIPServer)
    info = info_response.json()
    assert "@context" in info, "Info missing @context field"
    assert "protocol" in info, "Info missing protocol field"
    assert info["protocol"] == "http://iiif.io/api/image", f"Incorrect protocol: {info['protocol']}"
    assert "width" in info, "Info missing width field"
    assert "height" in info, "Info missing height field"
    assert "tiles" in info, "Info missing tiles field (should be provided by IIPServer)"
    
    # Test different tile requests that should be handled by IIPServer
    
    # 1. Full image
    full_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}:{filename}/full/full/0/default.jpg"
    full_response = requests.get(full_url)
    assert full_response.status_code == 200, f"Full image request failed with status {full_response.status_code}"
    
    # 2. Specific region
    tile_size = info["tiles"][0]["width"]
    region_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}:{filename}/0,0,{tile_size},{tile_size}/full/0/default.jpg"
    region_response = requests.get(region_url)
    assert region_response.status_code == 200, f"Region request failed with status {region_response.status_code}"
    
    # 3. Test a bogus region that should return an error
    bad_region_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}:{filename}/invalid/full/0/default.jpg"
    bad_region_response = requests.get(bad_region_url)
    assert bad_region_response.status_code != 200, f"Invalid region request should fail but returned {bad_region_response.status_code}"
    
    print(f"Successfully validated IIPServer integration for record {RECORD_ID}")
```

## Performance Testing

This script measures the performance of manifest generation and image delivery.

```python
# test_iiif_performance.py

import pytest
import requests
import time
import statistics
import os

# Configuration
BASE_URL = os.environ.get("ZENODO_BASE_URL", "http://localhost:5001")
RECORD_ID = os.environ.get("TEST_RECORD_ID", "YOUR_RECORD_ID")  # Replace with a real record ID
NUM_ITERATIONS = 5  # Number of times to run each test for averaging

def test_manifest_generation_performance():
    """Test the performance of manifest generation."""
    manifest_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}/manifest"
    
    # Clear caches with a "no-cache" request
    requests.get(manifest_url, headers={"Cache-Control": "no-cache"})
    
    # Measure response time over multiple iterations
    times = []
    for i in range(NUM_ITERATIONS):
        start_time = time.time()
        response = requests.get(manifest_url, headers={"Accept": "application/json"})
        end_time = time.time()
        
        assert response.status_code == 200, f"Manifest request failed with status {response.status_code}"
        
        times.append(end_time - start_time)
    
    # Calculate statistics
    avg_time = statistics.mean(times)
    max_time = max(times)
    min_time = min(times)
    
    print(f"Manifest generation performance (seconds):")
    print(f"  Average: {avg_time:.4f}")
    print(f"  Minimum: {min_time:.4f}")
    print(f"  Maximum: {max_time:.4f}")
    
    # Check that manifest generation is reasonably fast
    assert avg_time < 2.0, f"Manifest generation too slow: {avg_time:.4f} seconds on average"

def test_image_delivery_performance():
    """Test the performance of image delivery."""
    # First get the manifest to find an image
    manifest_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}/manifest"
    manifest_response = requests.get(manifest_url, headers={"Accept": "application/json"})
    
    assert manifest_response.status_code == 200, f"Manifest request failed with status {manifest_response.status_code}"
    
    manifest = manifest_response.json()
    
    # Get the first canvas
    sequence = manifest["sequences"][0]
    canvas = sequence["canvases"][0]
    
    # Extract the filename from the canvas ID
    filename = canvas["@id"].split("/")[-1]
    
    # Test thumbnail performance
    thumb_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}:{filename}/full/200,/0/default.jpg"
    
    # Clear caches
    requests.get(thumb_url, headers={"Cache-Control": "no-cache"})
    
    # Measure thumbnail delivery time
    thumb_times = []
    for i in range(NUM_ITERATIONS):
        start_time = time.time()
        response = requests.get(thumb_url)
        end_time = time.time()
        
        assert response.status_code == 200, f"Thumbnail request failed with status {response.status_code}"
        
        thumb_times.append(end_time - start_time)
    
    # Calculate statistics
    avg_thumb_time = statistics.mean(thumb_times)
    max_thumb_time = max(thumb_times)
    min_thumb_time = min(thumb_times)
    
    print(f"Thumbnail delivery performance (seconds):")
    print(f"  Average: {avg_thumb_time:.4f}")
    print(f"  Minimum: {min_thumb_time:.4f}")
    print(f"  Maximum: {max_thumb_time:.4f}")
    
    # Check that thumbnail delivery is reasonably fast
    assert avg_thumb_time < 1.0, f"Thumbnail delivery too slow: {avg_thumb_time:.4f} seconds on average"
```

## Test Execution Guidelines

To run these tests, follow these steps:

1. Create a directory for the test files:

```bash
mkdir -p tests/iiif
```

2. Copy each script into the appropriate file in that directory.

3. Create a conftest.py file if it doesn't exist:

```python
# tests/iiif/conftest.py

import pytest
import os

@pytest.fixture(scope="session")
def base_url():
    """Return the base URL for API requests."""
    return os.environ.get("ZENODO_BASE_URL", "http://localhost:5001")

@pytest.fixture(scope="session")
def record_id():
    """Return a test record ID with images."""
    return os.environ.get("TEST_RECORD_ID", "YOUR_RECORD_ID")  # Replace with your test record ID
```

4. Set environment variables for testing:

```bash
export ZENODO_BASE_URL="http://localhost:5001"
export TEST_RECORD_ID="<your-test-record-id>"
export PUBLIC_RECORD_ID="<your-public-record-id>"
export RESTRICTED_RECORD_ID="<your-restricted-record-id>"
export AUTH_TOKEN="<your-auth-token>"  # If testing restricted records
```

5. Run the tests with pytest:

```bash
# Run all IIIF tests
pytest -v tests/iiif/

# Run a specific test
pytest -v tests/iiif/test_iiif_manifest_basic.py

# Run with xvfb for tests that might open windows
xvfb-run pytest -v tests/iiif/
```

These tests should be integrated into your continuous integration process to ensure that IIIF functionality remains working as the codebase evolves.

## Testing Findings

During testing, we identified several important aspects of the IIIF manifest generation system that should be considered:

### Authentication Requirements

Most IIIF endpoints in Zenodo-RDM require authentication:

- The `/api/iiif/record:{id}/manifest` endpoint returns a 403 Forbidden response without proper authentication
- To test with authentication, you need to:
  - Log in to the web interface and obtain a token
  - Or create an API token in your user profile
  - Pass the token using the `Authorization: Bearer {token}` header

### IIPServer Configuration

The IIPServer component has specific requirements:

- It expects PTIF (Pyramid TIFF) files, not regular image files
- Files should be located in specific directories based on the record ID
- The URL pattern for direct IIPServer access is different from the API endpoints
- Error responses from IIPServer may not be in JSON format

### Testing in a Full Stack Environment

For comprehensive testing, a full stack environment is recommended:

- Use `docker-compose -f docker-compose.full.yml up -d` to start all services
- This includes the web-ui, web-api, and worker components needed for the complete workflow
- Use real records with properly converted PTIF files for testing

### Common Issues

Common issues encountered during testing:

1. **Authentication errors** (403 Forbidden) - Make sure to include a valid authentication token
2. **File not found errors** - Ensure PTIF files are properly generated and in the expected location
3. **Invalid format errors** - Confirm that images have been properly converted to PTIF format
4. **IIPServer errors** - Check IIPServer logs for detailed error messages

When executing the tests, be prepared to:
- Modify test scripts based on your specific environment
- Provide real record IDs with properly processed images
- Include authentication credentials where needed 
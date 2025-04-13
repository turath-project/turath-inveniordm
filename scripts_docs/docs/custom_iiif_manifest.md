# Customizing IIIF Manifests in Zenodo RDM

This guide demonstrates how to customize IIIF manifest generation in Zenodo RDM by adding additional metadata fields. We'll walk through a complete example of extending the default implementation.

## Overview

By default, Zenodo RDM's IIIF manifests include basic metadata like the title and publication date. However, we can enhance these manifests to include additional information such as:

- Creator names
- Resource type
- Keywords/subjects
- Any other metadata from the record

This guide walks through a step-by-step implementation of a custom IIIF manifest generator.

## Implementation Steps

### 1. Create Custom Schema

First, we create a custom schema that extends the default `IIIFManifestV2Schema`:

```python
# site/zenodo_rdm/iiif/schema.py
from flask_babel import lazy_gettext as _
from invenio_rdm_records.resources.serializers.iiif.schema import IIIFManifestV2Schema

class ZenodoIIIFManifestV2Schema(IIIFManifestV2Schema):
    """Enhanced IIIF manifest schema for Zenodo RDM."""

    def get_metadata(self, obj):
        """Generate enhanced metadata entries."""
        # Get the base metadata
        metadata = [
            {
                "label": _("Publication Date"),
                "value": obj["metadata"]["publication_date"],
            }
        ]
        
        # Add creator information if available
        if "creators" in obj["metadata"] and obj["metadata"]["creators"]:
            creators = [creator["person_or_org"]["name"] for creator in obj["metadata"]["creators"]]
            metadata.append({
                "label": _("Creator"),
                "value": "; ".join(creators)
            })
        
        # Add resource type if available
        if "resource_type" in obj["metadata"] and obj["metadata"]["resource_type"].get("title"):
            metadata.append({
                "label": _("Resource Type"),
                "value": obj["metadata"]["resource_type"]["title"]
            })
            
        # Add keywords/subjects if available
        if "subjects" in obj["metadata"] and obj["metadata"]["subjects"]:
            subjects = [subject["subject"] for subject in obj["metadata"]["subjects"]]
            metadata.append({
                "label": _("Keywords"),
                "value": "; ".join(subjects)
            })
            
        return metadata
```

### 2. Create Custom Serializer

Next, we create a serializer that uses our custom schema:

```python
# site/zenodo_rdm/iiif/serializers.py
from invenio_records_resources.serializers.serializer import Serializer
from .schema import ZenodoIIIFManifestV2Schema

class ZenodoIIIFManifestV2JSONSerializer(Serializer):
    """Enhanced IIIF manifest JSON serializer for Zenodo RDM."""

    def __init__(self):
        """Initialize serializer."""
        self.schema = ZenodoIIIFManifestV2Schema()

    def dump_obj(self, obj):
        """Dump the object into a JSON compatible dict."""
        return self.schema.dump(obj)

    def dump_list(self, obj_list):
        """Dump the list of objects into a JSON compatible list."""
        return [self.dump_obj(obj) for obj in obj_list]
```

### 3. Create Custom Resource

Then, we override the IIIF resource to use our custom serializer:

```python
# site/zenodo_rdm/iiif/resource.py
from flask import g
from flask_resources import response_handler, resource_requestctx
from invenio_rdm_records.resources.iiif import IIIFResource, with_iiif_content_negotiation
from invenio_rdm_records.resources.iiif import iiif_request_view_args

from .serializers import ZenodoIIIFManifestV2JSONSerializer

class ZenodoIIIFResource(IIIFResource):
    """Enhanced IIIF resource for Zenodo RDM."""

    @with_iiif_content_negotiation(ZenodoIIIFManifestV2JSONSerializer)
    @iiif_request_view_args
    @response_handler()
    def manifest(self):
        """Enhanced manifest with additional metadata."""
        return self._get_record_with_files().to_dict(), 200
```

### 4. Configuration

Create a configuration class for our custom resource:

```python
# site/zenodo_rdm/config.py
from invenio_rdm_records.resources.config import IIIFResourceConfig
from .iiif.resource import ZenodoIIIFResource

class ZenodoIIIFResourceConfig(IIIFResourceConfig):
    """Custom IIIF resource configuration."""
    
    # Use our custom resource class
    resource_cls = ZenodoIIIFResource
    # Define our own blueprint name to avoid conflicts
    blueprint_name = "zenodo_iiif"
    # Define a custom URL prefix
    url_prefix = "/custom-iiif"
```

### 5. Register Extension

Finally, register the custom resource in the application:

```python
# site/zenodo_rdm/ext.py
from . import config
from .iiif.resource import ZenodoIIIFResource

class ZenodoRDM(object):
    """Zenodo RDM extension."""

    # ...other code...
    
    def register_resources(self, app):
        """Register resources."""
        # Register our custom IIIF resource if enabled
        if app.config.get("RDM_IIIF_ENABLED", True):
            # Create our IIIF resource
            iiif_resource = ZenodoIIIFResource(
                config=config.ZenodoIIIFResourceConfig,
                service=app.extensions["invenio-rdm-records"].records_service,
            )
            
            # Register our IIIF blueprint
            app.register_blueprint(iiif_resource.as_blueprint())
```

## Testing the Implementation

To test our implementation, we created a test script that compares the output of the standard manifest with our custom one:

```python
# site/tests/iiif/test_custom_manifest.py
import requests

# URLs for standard and custom manifests
standard_url = f"{BASE_URL}/api/iiif/record:{RECORD_ID}/manifest"
custom_url = f"{BASE_URL}/custom-iiif/record:{RECORD_ID}/manifest"

# Get both manifests and compare them
standard_manifest = requests.get(standard_url, headers=headers).json()
custom_manifest = requests.get(custom_url, headers=headers).json()

# Compare metadata fields
standard_metadata = standard_manifest.get("metadata", [])
custom_metadata = custom_manifest.get("metadata", [])

print(f"Standard manifest has {len(standard_metadata)} metadata fields")
print(f"Custom manifest has {len(custom_metadata)} metadata fields")
```

## Expected Result

After implementing this custom manifest generator, when accessing `/custom-iiif/record:123/manifest`, the manifest will contain the additional metadata fields:

```json
{
  "@context": "http://iiif.io/api/presentation/2/context.json",
  "@type": "sc:Manifest",
  "@id": "https://example.org/custom-iiif/record:123/manifest",
  "label": "Record Title",
  "metadata": [
    {
      "label": "Publication Date",
      "value": "2023-01-01"
    },
    {
      "label": "Creator",
      "value": "John Smith; Jane Doe"
    },
    {
      "label": "Resource Type",
      "value": "Image"
    },
    {
      "label": "Keywords",
      "value": "IIIF; Digital Collections; Manuscripts"
    }
  ],
  "sequences": [
    // ... sequences and canvases ...
  ]
}
```

## Future Improvements

This implementation demonstrates a basic extension of the IIIF manifest. Further customizations could include:

1. Adding attribution information
2. Including rights and license details with explanatory text
3. Adding related links to other resources
4. Implementing custom canvas ordering based on metadata
5. Including thumbnail information at the manifest level

## Conclusion

By extending the default IIIF manifest generation, we can provide richer metadata to IIIF viewers and other clients that consume these manifests. This enhances the discoverability and usefulness of the images in your Zenodo RDM repository. 
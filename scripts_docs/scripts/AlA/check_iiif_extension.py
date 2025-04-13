#!/usr/bin/env python
# This script checks if the IIIF extension is properly registered
# Usage:
#   cd /path/to/zenodo-rdm
#   pipenv run invenio shell -c "exec(open('scripts/AlA/check_iiif_extension.py').read())"

import os
import sys
import json
import importlib
from pprint import pprint

def check_iiif_extension():
    """Check if the IIIF extension is properly registered."""
    from flask import current_app
    
    print("=== Checking IIIF Extension ===")
    
    # Check current_app extensions
    extensions = list(current_app.extensions.keys())
    print(f"\nRegistered Extensions ({len(extensions)}):")
    extensions.sort()
    for i, ext in enumerate(extensions, 1):
        print(f"{i}. {ext}")
    
    # Check if zenodo-rdm extension is registered
    if 'zenodo-rdm' in extensions:
        print("\n✓ zenodo-rdm extension is registered")
        
        # Check extension details
        ext = current_app.extensions['zenodo-rdm']
        print(f"Extension type: {type(ext).__name__}")
        
        # Check methods and attributes
        for attr in ['init_app', 'init_config', 'service_configs']:
            if hasattr(ext, attr):
                print(f"✓ Has attribute: {attr}")
            else:
                print(f"✗ Missing attribute: {attr}")
    else:
        print("\n✗ zenodo-rdm extension is NOT registered")
        
        # Try to register it
        print("\nAttempting to register zenodo-rdm extension:")
        try:
            from importlib import import_module
            try:
                # Try the direct import path
                module_path = 'site.zenodo_rdm.ext'
                module = import_module(module_path)
                print(f"✓ Successfully imported module: {module_path}")
                
                # Check if ZenodoRDM class exists
                if hasattr(module, 'ZenodoRDM'):
                    print(f"✓ Found ZenodoRDM class in {module_path}")
                    
                    # Initialize the extension
                    ZenodoRDM = getattr(module, 'ZenodoRDM')
                    ext = ZenodoRDM()
                    ext.init_app(current_app)
                    print("✓ Successfully registered ZenodoRDM extension")
                else:
                    print(f"✗ ZenodoRDM class not found in {module_path}")
            except ImportError as e:
                print(f"✗ Could not import site.zenodo_rdm.ext: {e}")
                
                # Try alternative paths
                alt_paths = [
                    'zenodo_rdm.ext',
                    'zenodo_rdm.site.ext',
                    'zenodo.ext',
                ]
                
                for path in alt_paths:
                    try:
                        module = import_module(path)
                        print(f"✓ Successfully imported module: {path}")
                        
                        # Check if ZenodoRDM class exists
                        if hasattr(module, 'ZenodoRDM'):
                            print(f"✓ Found ZenodoRDM class in {path}")
                            
                            # Initialize the extension
                            ZenodoRDM = getattr(module, 'ZenodoRDM')
                            ext = ZenodoRDM()
                            ext.init_app(current_app)
                            print("✓ Successfully registered ZenodoRDM extension")
                            break
                        else:
                            print(f"✗ ZenodoRDM class not found in {path}")
                    except ImportError:
                        print(f"✗ Could not import {path}")
        except Exception as e:
            print(f"✗ Error registering extension: {e}")
    
    # Check IIIF configuration
    print("\n=== Checking IIIF Configuration ===")
    
    config_keys = [
        'RDM_IIIF_ENABLED',
        'RDM_IIIF_PDF_SUPPORT',
        'RDM_IIIF_MANIFEST_FORMATS',
        'RDM_IIIF_SERVER_URL',
    ]
    
    for key in config_keys:
        if key in current_app.config:
            print(f"✓ {key}: {current_app.config[key]}")
        else:
            print(f"✗ {key} not defined in config")
    
    # Check resource classes
    print("\n=== Checking IIIF Resource Classes ===")
    
    # Check for IIIFResource class
    try:
        from invenio_rdm_records.resources import IIIFResource
        print(f"✓ Found IIIFResource class: {IIIFResource}")
        
        # Check resource config
        config_class = getattr(IIIFResource, 'config_class', None)
        print(f"Resource config class: {config_class}")
        
        # Check for custom resource class in config
        resource_class = current_app.config.get('RDM_IIIF_RESOURCE_CLASS')
        if resource_class:
            print(f"✓ Custom IIIF resource class configured: {resource_class}")
        else:
            print("✗ No custom IIIF resource class configured")
    except ImportError:
        print("✗ Could not import IIIFResource")
    
    # Check generate_pdf_manifest implementation
    print("\n=== Checking PDF Manifest Generation ===")
    
    # Try to find ZenodoIIIFResource
    try:
        from site.zenodo_rdm.iiif.resources import ZenodoIIIFResource
        print(f"✓ Found ZenodoIIIFResource: {ZenodoIIIFResource}")
    except ImportError:
        try:
            from site.zenodo_rdm.iiif import ZenodoIIIFResource
            print(f"✓ Found ZenodoIIIFResource: {ZenodoIIIFResource}")
        except ImportError:
            print("✗ Could not import ZenodoIIIFResource")
    
    # Try to find generate_pdf_manifest
    try:
        from site.zenodo_rdm.iiif.proxy import CantaloupeProxy, generate_pdf_manifest
        print(f"✓ Found generate_pdf_manifest function: {generate_pdf_manifest}")
    except ImportError:
        try:
            from site.zenodo_rdm.iiif import CantaloupeProxy, generate_pdf_manifest
            print(f"✓ Found generate_pdf_manifest function: {generate_pdf_manifest}")
        except ImportError:
            try:
                from site.zenodo_rdm.proxy import CantaloupeProxy, generate_pdf_manifest
                print(f"✓ Found generate_pdf_manifest function: {generate_pdf_manifest}")
            except ImportError:
                print("✗ Could not import generate_pdf_manifest function")
    
    # Check URL routes for IIIF
    print("\n=== Checking IIIF URL Routes ===")
    
    routes = []
    for rule in current_app.url_map.iter_rules():
        if 'iiif' in rule.rule.lower():
            routes.append(rule)
    
    if routes:
        print(f"Found {len(routes)} IIIF routes:")
        for i, rule in enumerate(routes, 1):
            print(f"{i}. {rule.rule} [{','.join(rule.methods)}] -> {rule.endpoint}")
    else:
        print("✗ No IIIF routes found")
    
    # Summary
    print("\n=== Summary ===")
    print("- IIIF extension registered: " + ("Yes" if 'zenodo-rdm' in extensions else "No"))
    print("- IIIF enabled in config: " + ("Yes" if current_app.config.get('RDM_IIIF_ENABLED') else "No"))
    print("- PDF support enabled: " + ("Yes" if current_app.config.get('RDM_IIIF_PDF_SUPPORT') else "No"))
    print("- IIIF routes available: " + ("Yes" if routes else "No"))
    
    # Next steps
    print("\n=== Next Steps ===")
    print("1. Make sure the zenodo-rdm extension is registered")
    print("2. Ensure all required IIIF configuration is present")
    print("3. Check that PDF files are correctly stored and accessible to Cantaloupe")
    print("4. Verify that the IIIF manifest endpoint is properly defined")
    print("5. Test accessing the manifest directly from the browser")

# Run the check
check_iiif_extension()

print("\nDone checking IIIF extension.") 
#!/usr/bin/env python
"""
Check IIIF PDF configuration and test manifest generation.
This script diagnoses issues with IIIF PDF manifest generation.
"""

import os
import sys
import json
import importlib
from pprint import pprint
from flask import current_app, url_for
from invenio_app.factory import create_app

# Create app context
app = create_app()

# Function to check for a specific config value
def check_config(key, expected=None):
    value = current_app.config.get(key, "NOT SET")
    result = {
        "setting": key,
        "value": value,
    }
    
    if expected is not None:
        result["expected"] = expected
        result["matches"] = value == expected
    
    return result

# Function to check for class in app extensions
def check_extension(ext_name, class_name=None, attr_name=None):
    result = {
        "extension": ext_name,
        "exists": ext_name in current_app.extensions
    }
    
    if result["exists"] and class_name:
        extension = current_app.extensions[ext_name]
        ext_class = extension.__class__.__name__
        result["class"] = ext_class
        result["expected_class"] = class_name
        result["class_matches"] = ext_class == class_name
        
        if attr_name and hasattr(extension, attr_name):
            attr_value = getattr(extension, attr_name)
            result[f"{attr_name}_exists"] = True
            result[f"{attr_name}_class"] = attr_value.__class__.__name__
        else:
            result[f"{attr_name}_exists"] = False
    
    return result

# Function to check a module and class
def check_module(module_path, class_name):
    result = {
        "module_path": module_path,
        "class_name": class_name
    }
    
    try:
        module = importlib.import_module(module_path)
        result["module_exists"] = True
        
        if hasattr(module, class_name):
            result["class_exists"] = True
            cls = getattr(module, class_name)
            result["class_type"] = str(type(cls))
        else:
            result["class_exists"] = False
    except ImportError:
        result["module_exists"] = False
    
    return result

# Main diagnostic function
def run_diagnostics():
    print("\n*** IIIF PDF Configuration Diagnostics ***\n")
    
    with app.app_context():
        # Check key configuration values
        configs = [
            check_config("RDM_IIIF_ENABLED", True),
            check_config("RDM_IIIF_MANIFEST_FORMATS"),
            check_config("RDM_IIIF_PDF_SUPPORT", True),
            check_config("RDM_IIIF_SERVER_URL"),
            check_config("RDM_IIIF_BASE_PATH"),
            check_config("IIIF_SERVER_ENABLED", True),
            check_config("IIIF_PREVIEW_ENABLED", True)
        ]
        
        # Check for extensions
        extensions = [
            check_extension("zenodo-rdm", "ZenodoRDM"),
            check_extension("invenio-rdm-records")
        ]
        
        # Check for critical modules and classes
        modules = [
            check_module("zenodo_rdm.iiif.proxy", "CantaloupeProxy"),
            check_module("zenodo_rdm.iiif.resource", "ZenodoIIIFResource"),
            check_module("zenodo_rdm.config", "ZenodoIIIFResourceConfig")
        ]
        
        # Check if PDFs are in manifest formats
        pdf_formats = check_config("RDM_IIIF_MANIFEST_FORMATS")
        has_pdf = "pdf" in pdf_formats.get("value", [])
        
        # Check if custom resource is properly registered
        # This is a bit complex and might need additional logic
        
        # Print results
        print("Configuration Settings:")
        for config in configs:
            if "expected" in config:
                match_status = "✅" if config["matches"] else "❌"
                print(f"{match_status} {config['setting']}: {config['value']} (expected: {config['expected']})")
            else:
                print(f"- {config['setting']}: {config['value']}")
        
        print("\nPDF Support:")
        if has_pdf:
            print("✅ PDF is in RDM_IIIF_MANIFEST_FORMATS")
        else:
            print("❌ PDF is NOT in RDM_IIIF_MANIFEST_FORMATS")
            
        print("\nRegistered Extensions:")
        for ext in extensions:
            exists_status = "✅" if ext["exists"] else "❌"
            print(f"{exists_status} {ext['extension']}")
            if ext["exists"] and "class_matches" in ext:
                class_status = "✅" if ext["class_matches"] else "❌"
                print(f"  {class_status} Class: {ext['class']} (expected: {ext['expected_class']})")
        
        print("\nRequired Modules and Classes:")
        for mod in modules:
            mod_status = "✅" if mod.get("module_exists", False) else "❌"
            print(f"{mod_status} Module: {mod['module_path']}")
            if mod.get("module_exists", False):
                class_status = "✅" if mod.get("class_exists", False) else "❌"
                print(f"  {class_status} Class: {mod['class_name']}")
        
        # Try to directly check IIIF proxy
        try:
            from zenodo_rdm.iiif.proxy import CantaloupeProxy
            proxy = CantaloupeProxy()
            print("\nCantaloupe Proxy:")
            print(f"✅ Successfully created CantaloupeProxy instance")
            print(f"- Server URL: {proxy.server_url}")
            print(f"- Base Path: {proxy.base_path}")
        except Exception as e:
            print("\nCantaloupe Proxy:")
            print(f"❌ Error creating CantaloupeProxy: {str(e)}")
        
        # Print recommendations
        print("\nRecommendations:")
        if not has_pdf:
            print("1. Add 'pdf' to RDM_IIIF_MANIFEST_FORMATS in invenio.cfg")
        
        if check_config("RDM_IIIF_PDF_SUPPORT")["value"] is not True:
            print("2. Set RDM_IIIF_PDF_SUPPORT = True in invenio.cfg")
            
        issues_found = any(c.get("matches") is False for c in configs if "matches" in c) or \
                      any(e.get("exists") is False for e in extensions) or \
                      any(m.get("module_exists") is False or m.get("class_exists") is False for m in modules) or \
                      not has_pdf
                      
        if not issues_found:
            print("No major configuration issues detected. The problem might be in:")
            print("1. The integration between Cantaloupe and your installation")
            print("2. The custom manifest generator logic")
            print("3. The URL routing for IIIF manifests")
            print("\nTry running a test with a specific record and PDF file:")
            print("python test_pdf_manifest.py --record=<record_id> --filename=<filename>")

if __name__ == "__main__":
    run_diagnostics() 
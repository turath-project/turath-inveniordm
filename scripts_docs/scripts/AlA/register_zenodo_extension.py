#!/usr/bin/env python
"""
Register the ZenodoRDM extension with Invenio.

This script:
1. Checks if the ZenodoRDM extension is registered
2. Registers it if necessary
3. Verifies IIIF configuration is properly set

Usage:
    pipenv run invenio shell -c "exec(open('scripts/AlA/register_zenodo_extension.py').read())"
"""

import sys
import logging
from flask import current_app
from invenio_base.utils import obj_or_import_string

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("register-zenodo")

def check_extension_registered():
    """Check if the ZenodoRDM extension is registered."""
    extensions = current_app.extensions
    
    logger.info("Checking if ZenodoRDM extension is registered...")
    if 'zenodo-rdm' in extensions:
        logger.info("✅ ZenodoRDM extension is registered")
        return True
    else:
        logger.warning("❌ ZenodoRDM extension is not registered")
        return False

def check_iiif_config():
    """Check the IIIF configuration."""
    logger.info("Checking IIIF configuration...")
    
    config = current_app.config
    
    # Check if IIIF is enabled
    if not config.get('IIIF_ENABLED', False):
        logger.warning("❌ IIIF is not enabled. Set IIIF_ENABLED = True in invenio.cfg")
        return False
    
    # Check if PDF IIIF is enabled
    if not config.get('IIIF_PDF_ENABLED', False):
        logger.warning("❌ PDF IIIF is not enabled. Set IIIF_PDF_ENABLED = True in invenio.cfg")
        return False
    
    # Check IIIF server URL
    if not config.get('IIIF_SERVER_URL'):
        logger.warning("❌ IIIF server URL is not set. Set IIIF_SERVER_URL in invenio.cfg")
        return False
    
    # Check supported manifest formats
    manifest_formats = config.get('IIIF_MANIFEST_FORMATS', [])
    if 'application/pdf' not in manifest_formats:
        logger.warning("❌ PDF is not in IIIF_MANIFEST_FORMATS. Add 'application/pdf' to the list")
        return False
    
    logger.info("✅ IIIF configuration is correctly set")
    return True

def register_extension():
    """Register the ZenodoRDM extension."""
    logger.info("Attempting to register ZenodoRDM extension...")
    
    try:
        # Get the extension class
        from zenodo_rdm.ext import ZenodoRDM
        
        # Check if the extension is already registered
        if check_extension_registered():
            logger.info("Extension is already registered, no action needed")
            return True
        
        # Try to register the extension
        ext = ZenodoRDM()
        ext.init_app(current_app)
        
        # Check if registration was successful
        if check_extension_registered():
            logger.info("✅ Successfully registered ZenodoRDM extension")
            return True
        else:
            logger.error("❌ Failed to register ZenodoRDM extension")
            return False
    except Exception as e:
        logger.error(f"❌ Error registering ZenodoRDM extension: {e}")
        return False

def check_iiif_resource_routes():
    """Check if the IIIF resource routes are defined."""
    logger.info("Checking IIIF resource routes...")
    
    try:
        # Import the config class
        from zenodo_rdm.config import ZenodoIIIFResourceConfig
        
        # Check if routes are defined
        if hasattr(ZenodoIIIFResourceConfig, 'routes'):
            routes = ZenodoIIIFResourceConfig.routes
            if routes:
                logger.info(f"✅ IIIF resource routes are defined: {routes}")
                return True
            else:
                logger.warning("❌ IIIF resource routes are empty")
                return False
        else:
            logger.warning("❌ IIIF resource routes are not defined. Add 'routes' to ZenodoIIIFResourceConfig")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking IIIF resource routes: {e}")
        return False

def main():
    """Main function."""
    logger.info("=== Registering ZenodoRDM Extension ===")
    
    # Check if extension is registered
    extension_registered = check_extension_registered()
    
    # Check IIIF configuration
    iiif_config_valid = check_iiif_config()
    
    # Check IIIF resource routes
    routes_defined = check_iiif_resource_routes()
    
    # Register extension if necessary
    if not extension_registered:
        if register_extension():
            logger.info("✅ Extension registration successful")
        else:
            logger.error("❌ Extension registration failed")
            logger.error("You may need to restart the Invenio server for changes to take effect")
    
    # Summary
    logger.info("=== Registration Summary ===")
    logger.info(f"Extension registered: {'✅ Yes' if extension_registered else '❌ No'}")
    logger.info(f"IIIF config valid: {'✅ Yes' if iiif_config_valid else '❌ No'}")
    logger.info(f"IIIF routes defined: {'✅ Yes' if routes_defined else '❌ No'}")
    
    return extension_registered and iiif_config_valid and routes_defined

if __name__ == "__main__":
    main()
else:
    # Running in Invenio shell
    main() 
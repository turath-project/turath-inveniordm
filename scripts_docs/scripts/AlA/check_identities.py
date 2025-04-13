#!/usr/bin/env python3
"""
Script to check what identity types are available in the installed version.
"""
import os
import sys
import inspect
import importlib
import importlib.util

def check_module_contents(module_name):
    """Check and print the contents of a module."""
    try:
        module = importlib.import_module(module_name)
        print(f"\nModule: {module_name}")
        
        # Get all module attributes
        attrs = dir(module)
        for attr in attrs:
            # Skip private/dunder attributes
            if attr.startswith('_'):
                continue
                
            try:
                attr_value = getattr(module, attr)
                attr_type = type(attr_value).__name__
                
                # Special handling for classes and functions
                if inspect.isclass(attr_value):
                    print(f"  Class: {attr}")
                    
                    # Check class methods and attributes
                    class_attrs = dir(attr_value)
                    important_methods = [m for m in class_attrs if not m.startswith('_')]
                    if important_methods:
                        print(f"    Methods/Attributes: {', '.join(important_methods[:5])}")
                        if len(important_methods) > 5:
                            print(f"    ... and {len(important_methods) - 5} more")
                            
                elif inspect.isfunction(attr_value):
                    sig = inspect.signature(attr_value)
                    print(f"  Function: {attr}{sig}")
                else:
                    print(f"  {attr_type}: {attr}")
            except Exception as e:
                print(f"  Error accessing {attr}: {e}")
        
        return True
    except ImportError as e:
        print(f"Error importing {module_name}: {e}")
        return False
    except Exception as e:
        print(f"Error examining {module_name}: {e}")
        return False

def check_identities():
    """Check what identity types are available in the installed version."""
    print("=== Checking Identity Types ===")
    
    # Check invenio_records_permissions
    check_module_contents('invenio_records_permissions.generators')
    
    # Check invenio_records_permissions.api
    check_module_contents('invenio_records_permissions.api')
    
    # Check invenio_records_permissions.policies
    check_module_contents('invenio_records_permissions.policies')
    
    # Check invenio_access.permissions
    check_module_contents('invenio_access.permissions')
    
    # Check flask_security
    check_module_contents('flask_security')
    
    # Check invenio_rdm_records.services
    check_module_contents('invenio_rdm_records.services')
    
    # Check invenio_rdm_records.services.config
    check_module_contents('invenio_rdm_records.services.config')

def main():
    # Import here to avoid early import errors
    try:
        from invenio_app.factory import create_app
        app = create_app()
        
        with app.app_context():
            check_identities()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 
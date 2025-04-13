# /Users/alaaalbarazi/Projects/Turath/turath-inveniordm/scripts/test_file_limit.py

"""Test script to verify the file limit patch is working."""

from flask import current_app
from invenio_records_resources.services.files.config import FileServiceConfig
import sys

def check_file_limit():
    """Check the current file limit setting."""
    print(f"Current max_files_count value: {FileServiceConfig.max_files_count}")
    print(f"This means you can upload up to {FileServiceConfig.max_files_count} files per record")
    
    # Check if app config also reflects this
    if hasattr(current_app.config, 'APP_RDM_DEPOSIT_FORM_QUOTA'):
        quota = current_app.config.get('APP_RDM_DEPOSIT_FORM_QUOTA', {})
        ui_max_files = quota.get('maxFiles', 'Not set')
        print(f"UI max files setting: {ui_max_files}")
    
    return FileServiceConfig.max_files_count

if __name__ == "__main__":
    # We need to run this inside the Flask application context
    from invenio_app.factory import create_app
    app = create_app()
    
    with app.app_context():
        limit = check_file_limit()
        
        # Provide a clear indication if our patch worked
        if limit > 100:
            print("✅ SUCCESS: The monkey patch is working! File limit has been increased.")
            sys.exit(0)
        else:
            print("❌ FAILURE: The monkey patch is NOT working. File limit is still at default value.")
            sys.exit(1)
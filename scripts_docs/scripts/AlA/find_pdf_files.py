#!/usr/bin/env python
"""Find PDF files in the instance directory."""

import os
import sys
import glob
from invenio_app.factory import create_app
from flask import current_app

def find_pdf_files():
    """Find PDF files in the instance directory."""
    app = create_app()
    
    with app.app_context():
        # Get the instance directory
        instance_dir = current_app.instance_path
        print(f"Instance directory: {instance_dir}")
        
        # Look for PDF files in the data directory
        data_dir = os.path.join(instance_dir, "data")
        print(f"Data directory: {data_dir}")
        
        # Find all PDF files recursively
        pdf_pattern = os.path.join(data_dir, "**", "*.pdf")
        pdf_files = glob.glob(pdf_pattern, recursive=True)
        
        if pdf_files:
            print(f"\nFound {len(pdf_files)} PDF files:")
            for pdf_path in pdf_files:
                rel_path = os.path.relpath(pdf_path, data_dir)
                size = os.path.getsize(pdf_path)
                print(f"- {rel_path} ({size} bytes)")
        else:
            print("\nNo PDF files found in the data directory.")
            
        # Check specific subdirectories
        subdirs = ["records", "files", "images"]
        for subdir in subdirs:
            subdir_path = os.path.join(data_dir, subdir)
            if os.path.exists(subdir_path):
                print(f"\nContents of {subdir} directory:")
                for root, dirs, files in os.walk(subdir_path):
                    rel_root = os.path.relpath(root, data_dir)
                    print(f"Directory: {rel_root}")
                    if dirs:
                        print(f"  Subdirectories: {', '.join(dirs)}")
                    if files:
                        print(f"  Files: {', '.join(files)}")
            else:
                print(f"\n{subdir} directory does not exist.")

if __name__ == "__main__":
    find_pdf_files() 
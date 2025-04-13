#!/usr/bin/env python3
"""
Script to convert an image file to PTIF format for IIIF support.
This uses the vips command-line tool directly.
"""

import os
import sys
import subprocess
import shutil

def convert_to_ptif(input_file, output_file=None):
    """Convert an image file to PTIF format."""
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist.")
        return False
    
    if output_file is None:
        # Replace the extension with .ptif
        base, _ = os.path.splitext(input_file)
        output_file = f"{base}.ptif"
    
    print(f"Converting {input_file} to {output_file}...")
    
    try:
        # Use vips to convert the image to PTIF format
        # This is similar to what TilesProcessor does internally
        cmd = [
            "vips", "tiffsave", input_file, output_file,
            "--compression=deflate",
            "--tile",
            "--pyramid",
            "--tile-width=256",
            "--tile-height=256"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error: vips command failed: {result.stderr}")
            return False
        
        print(f"✅ Successfully converted to {output_file}")
        print(f"   File size: {os.path.getsize(output_file)} bytes")
        return True
    
    except Exception as e:
        print(f"Error during conversion: {e}")
        return False

def check_iipserver_env():
    """Check the IIPServer environment variables."""
    docker_cmd = [
        "docker-compose", "exec", "iipserver", 
        "env", "|", "grep", "-i", "filesystem"
    ]
    
    try:
        result = subprocess.run(docker_cmd, capture_output=True, text=True, shell=True)
        if result.returncode != 0:
            print(f"Warning: Could not check IIPServer environment: {result.stderr}")
            return None
        
        print(f"IIPServer environment: {result.stdout}")
        
        # Extract the FILESYSTEM_PREFIX if possible
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if line.startswith("FILESYSTEM_PREFIX="):
                return line.split("=")[1]
        
        return None
    except Exception as e:
        print(f"Error checking IIPServer environment: {e}")
        return None

def copy_to_iipserver(ptif_file, record_id=None):
    """Copy the PTIF file to the IIPServer container."""
    if not os.path.exists(ptif_file):
        print(f"Error: PTIF file '{ptif_file}' does not exist.")
        return False
    
    filename = os.path.basename(ptif_file)
    base_name, _ = os.path.splitext(filename)
    
    # Get the IIPServer FILESYSTEM_PREFIX
    filesystem_prefix = check_iipserver_env() or "/images/public"
    print(f"Using IIPServer filesystem prefix: {filesystem_prefix}")
    
    if record_id:
        # Create a path that includes both record ID and filename for uniqueness
        target_path = filesystem_prefix
        target_filename = f"private_{record_id}_{base_name}.ptif"
        target_file = f"{target_path}/{target_filename}"
    else:
        # Just use the public directory with the original filename
        target_path = filesystem_prefix
        target_file = f"{target_path}/{filename}"
    
    # Now copy the file into the container
    # We need to copy to a temporary location first, then use docker cp
    temp_dir = "/tmp"
    temp_file = os.path.join(temp_dir, filename)
    
    try:
        shutil.copy2(ptif_file, temp_file)
        print(f"Copied {ptif_file} to {temp_file}")
        
        # Now use docker cp to copy into the container
        container_name = "zenodo-rdm-master-iipserver-1"
        docker_cp_cmd = [
            "docker", "cp", 
            temp_file, 
            f"{container_name}:{target_file}"
        ]
        
        result = subprocess.run(docker_cp_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: Failed to copy file to IIPServer: {result.stderr}")
            return False
        
        print(f"✅ Successfully copied {filename} to IIPServer at {target_file}")
        
        # Clean up temporary file
        os.remove(temp_file)
        
        # Return the target filename for IIIF URL construction
        if record_id:
            return target_filename
        else:
            return filename
    
    except Exception as e:
        print(f"Error copying file to IIPServer: {e}")
        return False
    
def verify_iiif_url(ptif_filename):
    """Print the IIIF URL for testing."""
    iiif_url = f"http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/{ptif_filename}/info.json"
    
    print("\nTo verify IIIF functionality, use the following URLs:")
    print(f"Metadata: {iiif_url}")
    print(f"Thumbnail: http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/{ptif_filename}/full/200,/0/default.jpg")
    print(f"Image region: http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/{ptif_filename}/0,0,100,100/full/0/default.jpg")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} IMAGE_FILE [RECORD_ID]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    record_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Convert the file to PTIF
    base, _ = os.path.splitext(input_file)
    output_file = f"{base}.ptif"
    
    if not convert_to_ptif(input_file, output_file):
        sys.exit(1)
    
    # Copy to IIPServer
    if record_id:
        ptif_filename = copy_to_iipserver(output_file, record_id)
        if not ptif_filename:
            sys.exit(1)
    else:
        ptif_filename = copy_to_iipserver(output_file)
        if not ptif_filename:
            sys.exit(1)
    
    # Print IIIF URLs for testing
    verify_iiif_url(ptif_filename) 
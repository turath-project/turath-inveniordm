#!/usr/bin/env python
# This script fixes the path for Cantaloupe to find the PDF file
# Usage:
#   cd /path/to/zenodo-rdm
#   pipenv run python scripts/AlA/fix_cantaloupe_paths.py RECORD_ID FILENAME

import os
import sys
import shutil
import subprocess
from pathlib import Path

def find_docker_container(name_pattern="cantaloupe"):
    """Find a Docker container with a name matching the pattern."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Check if any container name matches the pattern
        for container in result.stdout.strip().split("\n"):
            if name_pattern.lower() in container.lower():
                return container
        
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error running docker ps: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error finding docker container: {e}")
        return None

def copy_to_container(container, local_path, container_path):
    """Copy a file to a Docker container."""
    try:
        result = subprocess.run(
            ["docker", "cp", local_path, f"{container}:{container_path}"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"Successfully copied {local_path} to {container}:{container_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error copying to container: {e}")
        print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error copying to container: {e}")
        return False

def copy_to_cantaloupe_paths(record_id, filename, cantaloupe_base_path="/opt/cantaloupe/images"):
    """Copy PDF file to Cantaloupe's expected paths."""
    print(f"Fixing Cantaloupe paths for record {record_id}, file {filename}")
    
    # Ensure record_id is a string
    record_id = str(record_id)
    
    # Check if the file exists locally
    local_paths = [
        filename,  # Direct path
        os.path.join("data", "private", record_id, filename),  # Normal Invenio path
        os.path.join("data", "records", record_id, "private", filename),  # Alternative path
        os.path.join(".venv", "var", "data", "private", record_id, filename),  # Local development path
        os.path.join(".venv", "var", "data", "records", record_id, "private", filename)  # Alternative dev path
    ]
    
    local_file_path = None
    for path in local_paths:
        if os.path.isfile(path):
            local_file_path = path
            print(f"Found file at {local_file_path}")
            break
    
    if not local_file_path:
        print(f"ERROR: Could not find file {filename} for record {record_id}")
        print(f"Searched in paths: {local_paths}")
        print("Please specify the correct path to the file.")
        return False
    
    # First approach: Try to copy directly if we have a local Cantaloupe instance
    cantaloupe_dirs = [
        os.path.join(cantaloupe_base_path, record_id),
        os.path.join(cantaloupe_base_path, "private", record_id),
    ]
    
    local_success = False
    for cantaloupe_dir in cantaloupe_dirs:
        try:
            # Create directory if it doesn't exist
            os.makedirs(cantaloupe_dir, exist_ok=True)
            
            # Copy file
            target_path = os.path.join(cantaloupe_dir, filename)
            shutil.copy2(local_file_path, target_path)
            print(f"Copied file to {target_path}")
            local_success = True
        except PermissionError:
            print(f"Permission denied for {cantaloupe_dir}")
        except Exception as e:
            print(f"Error copying to {cantaloupe_dir}: {e}")
    
    # Second approach: Try to copy to Docker container if running
    cantaloupe_container = find_docker_container("cantaloupe")
    docker_success = False
    
    if cantaloupe_container:
        print(f"Found Cantaloupe Docker container: {cantaloupe_container}")
        
        # Paths to try in the container
        container_dirs = [
            os.path.join(cantaloupe_base_path, record_id),
            os.path.join(cantaloupe_base_path, "private", record_id),
        ]
        
        for container_dir in container_dirs:
            # Ensure directory exists in container
            try:
                subprocess.run(
                    ["docker", "exec", cantaloupe_container, "mkdir", "-p", container_dir],
                    capture_output=True,
                    check=True
                )
                
                # Copy the file
                container_target = os.path.join(container_dir, filename)
                if copy_to_container(cantaloupe_container, os.path.abspath(local_file_path), container_target):
                    print(f"Successfully copied to Docker container path: {container_target}")
                    docker_success = True
                    
                    # Set permissions to ensure Cantaloupe can read the file
                    subprocess.run(
                        ["docker", "exec", cantaloupe_container, "chmod", "644", container_target],
                        capture_output=True,
                        check=True
                    )
            except Exception as e:
                print(f"Error setting up container path {container_dir}: {e}")
    else:
        print("No Cantaloupe Docker container found")
    
    # Create a symlink if needed (useful in development environments)
    try:
        source_path = os.path.abspath(local_file_path)
        target_dir = os.path.join("instance", "data", "cantaloupe", record_id)
        os.makedirs(target_dir, exist_ok=True)
        
        target_path = os.path.join(target_dir, filename)
        if not os.path.exists(target_path):
            # On Unix, create a symlink, on Windows, copy the file
            if os.name == 'posix':
                try:
                    os.symlink(source_path, target_path)
                    print(f"Created symlink from {source_path} to {target_path}")
                except Exception as e:
                    print(f"Error creating symlink: {e}")
                    shutil.copy2(source_path, target_path)
                    print(f"Copied file to {target_path}")
            else:
                shutil.copy2(source_path, target_path)
                print(f"Copied file to {target_path}")
    except Exception as e:
        print(f"Error creating alternative path: {e}")
    
    # Final summary
    if local_success or docker_success:
        print("\n✅ Successfully copied file to Cantaloupe paths")
        print("\nYou can now try accessing the IIIF manifest at:")
        print(f"https://127.0.0.1:5000/api/iiif/record:{record_id}/manifest")
        print("\nOr directly access the Cantaloupe info.json at:")
        print(f"http://localhost:8182/iiif/2/{record_id}%2F{filename}/info.json")
        return True
    else:
        print("\n❌ Failed to copy file to any Cantaloupe path")
        print("Please ensure Cantaloupe is properly installed and configured.")
        return False

def main():
    """Main function when run as a script."""
    if len(sys.argv) < 3:
        print("Usage: pipenv run python scripts/AlA/fix_cantaloupe_paths.py RECORD_ID FILENAME")
        print("Example: pipenv run python scripts/AlA/fix_cantaloupe_paths.py 209 test_pdf.pdf")
        return
    
    # Get arguments
    record_id = sys.argv[1]
    filename = sys.argv[2]
    
    # Optional: custom cantaloupe base path
    cantaloupe_base_path = sys.argv[3] if len(sys.argv) > 3 else "/opt/cantaloupe/images"
    
    # Copy to Cantaloupe paths
    copy_to_cantaloupe_paths(record_id, filename, cantaloupe_base_path)

if __name__ == "__main__":
    main() 
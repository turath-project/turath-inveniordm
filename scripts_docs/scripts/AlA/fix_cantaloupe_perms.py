#!/usr/bin/env python
# This script fixes permissions in the Cantaloupe container to allow
# creating necessary directories
# Usage:
#   cd /path/to/zenodo-rdm
#   pipenv run python scripts/AlA/fix_cantaloupe_perms.py

import os
import sys
import subprocess

def fix_cantaloupe_permissions():
    """Fix permissions in the Cantaloupe container."""
    print("Fixing permissions in Cantaloupe container...")
    
    # Find the Cantaloupe container
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        cantaloupe_container = None
        for container in result.stdout.strip().split("\n"):
            if "cantaloupe" in container.lower():
                cantaloupe_container = container
                break
        
        if not cantaloupe_container:
            print("No Cantaloupe container found")
            return False
        
        print(f"Found Cantaloupe container: {cantaloupe_container}")
        
        # Change ownership of the images directory
        subprocess.run(
            ["docker", "exec", "-u", "root", cantaloupe_container, "chown", "-R", "cantaloupe:nogroup", "/opt/cantaloupe/images"],
            capture_output=True,
            check=True
        )
        print("✓ Changed ownership of /opt/cantaloupe/images")
        
        # Add write permissions
        subprocess.run(
            ["docker", "exec", "-u", "root", cantaloupe_container, "chmod", "-R", "755", "/opt/cantaloupe/images"],
            capture_output=True,
            check=True
        )
        print("✓ Added write permissions to /opt/cantaloupe/images")
        
        # Test creating a directory
        test_dir = "/opt/cantaloupe/images/test_perms"
        subprocess.run(
            ["docker", "exec", cantaloupe_container, "mkdir", "-p", test_dir],
            capture_output=True,
            check=True
        )
        print(f"✓ Successfully created test directory: {test_dir}")
        
        # Create a test file
        test_file = f"{test_dir}/test.txt"
        subprocess.run(
            ["docker", "exec", cantaloupe_container, "bash", "-c", f"echo 'Test' > {test_file}"],
            capture_output=True,
            check=True
        )
        print(f"✓ Successfully created test file: {test_file}")
        
        print("\n✅ Permissions fixed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def main():
    """Main function."""
    fix_cantaloupe_permissions()

if __name__ == "__main__":
    main() 
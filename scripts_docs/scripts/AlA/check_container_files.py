#!/usr/bin/env python
"""
Check file locations in Docker containers and test Cantaloupe access.
This script helps diagnose issues with PDF files in containerized environments.
"""

import os
import sys
import json
import argparse
import subprocess
import requests
from urllib.parse import quote
import time

def run_docker_command(command):
    """Run a command in the Docker CLI and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running Docker command: {e}")
        print(f"Command: {command}")
        print(f"Error output: {e.stderr}")
        return None

def check_cantaloupe_files(record_id, filename=None):
    """Check file locations in Cantaloupe Docker container."""
    # Get Cantaloupe container
    cantaloupe_container = run_docker_command("docker compose ps -q cantaloupe")
    
    if not cantaloupe_container:
        print("No Cantaloupe container found. Is it running?")
        return
    
    print(f"Found Cantaloupe container: {cantaloupe_container}")
    
    # Check Cantaloupe logs
    print("\nChecking Cantaloupe logs...")
    logs = run_docker_command(f"docker logs --tail 20 {cantaloupe_container}")
    if logs:
        print(logs)
    
    # Check Cantaloupe configuration
    print("\nChecking Cantaloupe configuration...")
    cantaloupe_config = run_docker_command(f"docker exec {cantaloupe_container} env | grep CANTALOUPE")
    if cantaloupe_config:
        print("Cantaloupe environment variables:")
        print(cantaloupe_config)
    
    # Check the main directories where files should be mounted according to docker-compose.yml
    mount_paths = [
        "/opt/cantaloupe/images",
        "/opt/cantaloupe/images/records",
        "/opt/cantaloupe/images/private",
        "/opt/cantaloupe/images/test"
    ]
    
    for path in mount_paths:
        print(f"\nChecking directory: {path}")
        dir_content = run_docker_command(f"docker exec {cantaloupe_container} ls -la {path} 2>/dev/null || echo 'Directory not found'")
        if dir_content and "Directory not found" not in dir_content:
            print(f"Contents of {path}:")
            print(dir_content)
            
            # If looking for a specific record
            if record_id:
                print(f"\nLooking for record {record_id} in {path}...")
                record_path = f"{path}/{record_id}"
                record_dir = run_docker_command(f"docker exec {cantaloupe_container} ls -la {record_path} 2>/dev/null || echo 'Record directory not found'")
                
                if record_dir and "Record directory not found" not in record_dir:
                    print(f"Found record directory: {record_path}")
                    print(record_dir)
                    
                    # If looking for a specific file
                    if filename:
                        file_path = f"{record_path}/{filename}"
                        file_check = run_docker_command(f"docker exec {cantaloupe_container} ls -la {file_path} 2>/dev/null || echo 'File not found'")
                        
                        if file_check and "File not found" not in file_check:
                            print(f"\n✓ Found target file at {file_path}")
                            print(file_check)
                            
                            # Test the file with Cantaloupe
                            test_cantaloupe_access(record_id, filename)
                            return True
    
    # If we didn't find the file in the expected location, check for any PDF files
    print("\nSearching for any PDF files in Cantaloupe container...")
    pdf_search = run_docker_command(f"docker exec {cantaloupe_container} find /opt/cantaloupe -name '*.pdf' 2>/dev/null")
    
    if pdf_search:
        print("Found PDF files:")
        for pdf in pdf_search.split('\n'):
            print(f"- {pdf}")
            
            # If we're looking for a specific file
            if filename and filename in pdf:
                print(f"\n✓ Found similar file: {pdf}")
                
                # Extract the record ID and file part from the path
                path_parts = pdf.split('/')
                if len(path_parts) >= 2:
                    possible_record_id = path_parts[-2]
                    print(f"Possible record ID from path: {possible_record_id}")
                    
                    # Test this file with Cantaloupe
                    test_cantaloupe_access(possible_record_id, path_parts[-1])
    else:
        print("No PDF files found in Cantaloupe container.")
    
    # If we didn't find the file, try to copy it from the host to the container
    if filename and record_id:
        copy_file_to_cantaloupe(record_id, filename)

def test_cantaloupe_access(record_id, filename):
    """Test if Cantaloupe can access and process the file."""
    print(f"\nTesting Cantaloupe access for record {record_id}, file {filename}...")
    
    # Construct the URL patterns to try
    url_patterns = [
        f"http://localhost:8182/iiif/2/private%2F{record_id}%2F{filename}/info.json",
        f"http://localhost:8182/iiif/2/records%2F{record_id}%2F{filename}/info.json",
        f"http://localhost:8182/iiif/2/{record_id}%2F{filename}/info.json",
        f"http://localhost:8182/iiif/2/{filename}/info.json"
    ]
    
    success = False
    
    for url in url_patterns:
        print(f"Trying URL: {url}")
        try:
            response = requests.get(url)
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                success = True
                print("Success! Cantaloupe can access the file.")
                try:
                    info = response.json()
                    print(f"File information: {json.dumps(info, indent=2)}")
                except:
                    print(f"Response not JSON: {response.text[:200]}...")
                break
            else:
                print(f"Error: {response.text[:200]}...")
        except Exception as e:
            print(f"Error accessing URL: {str(e)}")
    
    if not success:
        print("\nAll URL patterns failed. Cantaloupe cannot access the file.")
        return False
    
    return True

def copy_file_to_cantaloupe(record_id, filename):
    """Try to copy a file from the host to the Cantaloupe container."""
    print(f"\nAttempting to copy file to Cantaloupe container...")
    
    # Locations to check for the file on the host
    host_locations = [
        f"./data/records/{record_id}/{filename}",
        f"./data/images/private/{record_id}/{filename}",
        f"./test_data/{filename}"
    ]
    
    for location in host_locations:
        print(f"Checking if file exists at {location}...")
        file_check = run_docker_command(f"ls -la {location} 2>/dev/null || echo 'File not found'")
        
        if file_check and "File not found" not in file_check:
            print(f"Found file on host at {location}")
            print(file_check)
            
            # If file exists in the host, create target directories in Cantaloupe
            cantaloupe_container = run_docker_command("docker compose ps -q cantaloupe")
            
            # Determine target path in Cantaloupe
            if "records" in location:
                target_dir = f"/opt/cantaloupe/images/records/{record_id}"
            elif "private" in location:
                target_dir = f"/opt/cantaloupe/images/private/{record_id}"
            else:
                target_dir = f"/opt/cantaloupe/images/test"
            
            print(f"Creating directory {target_dir} in Cantaloupe container...")
            mkdir_cmd = run_docker_command(f"docker exec {cantaloupe_container} mkdir -p {target_dir}")
            
            # Copy file to Cantaloupe
            print(f"Copying file to Cantaloupe container at {target_dir}/{filename}...")
            copy_cmd = run_docker_command(f"docker cp {location} {cantaloupe_container}:{target_dir}/{filename}")
            
            # Verify file was copied
            file_verify = run_docker_command(f"docker exec {cantaloupe_container} ls -la {target_dir}/{filename} 2>/dev/null || echo 'File not copied'")
            
            if file_verify and "File not copied" not in file_verify:
                print(f"✓ Successfully copied file to Cantaloupe at {target_dir}/{filename}")
                print(file_verify)
                
                # Set permissions to ensure Cantaloupe can read it
                run_docker_command(f"docker exec {cantaloupe_container} chmod 644 {target_dir}/{filename}")
                
                # Test Cantaloupe access
                if "records" in location:
                    test_cantaloupe_access(record_id, filename)
                elif "private" in location:
                    test_cantaloupe_access(record_id, filename)
                else:
                    test_cantaloupe_access("test", filename)
                
                return True
            else:
                print(f"Failed to copy file to Cantaloupe container")
    
    print("Could not find the file on the host to copy to Cantaloupe")
    return False

def create_test_pdf():
    """Create a test PDF file if none exists."""
    print("\nCreating a test PDF file...")
    
    # Create a simple test PDF file
    pdf_content = """
%PDF-1.1
1 0 obj
<< /Type /Catalog
   /Pages 2 0 R
>>
endobj
2 0 obj
<< /Type /Pages
   /Kids [3 0 R]
   /Count 1
   /MediaBox [0 0 300 144]
>>
endobj
3 0 obj
<< /Type /Page
   /Parent 2 0 R
   /Resources
   << /Font
      << /F1
         << /Type /Font
            /Subtype /Type1
            /BaseFont /Times-Roman
         >>
      >>
   >>
   /Contents 4 0 R
>>
endobj
4 0 obj
<< /Length 55 >>
stream
BT
/F1 18 Tf
0 0 Td
(Zenodo RDM Test PDF File) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000018 00000 n
0000000077 00000 n
0000000178 00000 n
0000000457 00000 n
trailer
<< /Root 1 0 R
   /Size 5
>>
startxref
565
%%EOF
"""
    
    test_dir = "./test_data"
    test_file = f"{test_dir}/test.pdf"
    
    # Check if directory exists
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    # Create the test PDF
    with open(test_file, "w") as f:
        f.write(pdf_content)
    
    print(f"Created test PDF at {test_file}")
    
    # Copy to Cantaloupe
    cantaloupe_container = run_docker_command("docker compose ps -q cantaloupe")
    if cantaloupe_container:
        run_docker_command(f"docker exec {cantaloupe_container} mkdir -p /opt/cantaloupe/images/test")
        run_docker_command(f"docker cp {test_file} {cantaloupe_container}:/opt/cantaloupe/images/test/test.pdf")
        print("Copied test PDF to Cantaloupe container")
        
        # Test Cantaloupe access
        time.sleep(2)  # Give Cantaloupe a moment to process
        test_cantaloupe_access("test", "test.pdf")
    
    return True

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Check file locations in Cantaloupe Docker container")
    parser.add_argument("--record", "-r", help="Record ID to check")
    parser.add_argument("--filename", "-f", help="Filename to look for")
    parser.add_argument("--create-test", "-t", action="store_true", help="Create a test PDF file")
    
    args = parser.parse_args()
    
    if args.create_test:
        create_test_pdf()
    elif args.record and args.filename:
        check_cantaloupe_files(args.record, args.filename)
    else:
        check_cantaloupe_files(args.record)

if __name__ == "__main__":
    main() 
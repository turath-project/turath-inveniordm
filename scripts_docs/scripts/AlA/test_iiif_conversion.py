#!/usr/bin/env python3
"""
Test script to verify PTIF conversion and IIIF functionality.
Tests both custom conversion and Zenodo's built-in tools.
"""

import os
import sys
import json
import subprocess
import requests
import time

# Configuration
TEST_IMAGE = "test_image.png"  # Should exist in data/images/
TARGET_PTIF = "test_image.ptif"  # Will be generated
IIPSERVER_URL = "http://localhost:8080/fcgi-bin/iipsrv.fcgi"

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

def run_command(cmd):
    """Run a shell command and return its output."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False, result.stderr
    return True, result.stdout

def check_prerequisites():
    """Check if all prerequisites are met."""
    print_header("Checking Prerequisites")
    
    # Check if test image exists
    image_path = f"data/images/{TEST_IMAGE}"
    if not os.path.exists(image_path):
        print(f"❌ Test image not found: {image_path}")
        print(f"   Please copy a PNG image to this location")
        return False
    print(f"✅ Test image found: {image_path}")
    
    # Check if vips is installed (for custom conversion)
    success, output = run_command("which vips || echo 'vips not found'")
    if "not found" in output:
        print("❌ vips tool not installed")
        print("   Please install with 'brew install vips' (macOS) or 'apt-get install libvips-tools' (Linux)")
        return False
    print("✅ vips tool is installed")
    
    # Check if IIPServer is running
    try:
        response = requests.get(IIPSERVER_URL, timeout=5)
        print(f"✅ IIPServer is accessible at {IIPSERVER_URL}")
    except requests.exceptions.RequestException:
        print(f"❌ IIPServer is not accessible at {IIPSERVER_URL}")
        print("   Please make sure docker-compose is running with IIPServer container")
        return False
    
    return True

def test_custom_conversion():
    """Test the custom PTIF conversion method."""
    print_header("Testing Custom PTIF Conversion")
    
    # Remove existing PTIF file if it exists
    ptif_path = f"data/images/{TARGET_PTIF}"
    public_ptif_path = f"data/images/public/{TARGET_PTIF}"
    
    if os.path.exists(ptif_path):
        os.remove(ptif_path)
        print(f"Removed existing {ptif_path}")
    
    if os.path.exists(public_ptif_path):
        os.remove(public_ptif_path)
        print(f"Removed existing {public_ptif_path}")
    
    # Run the conversion script
    print("\nStep 1: Running custom conversion script")
    success, output = run_command("./convert_images.sh")
    if not success:
        print("❌ Custom conversion failed")
        return False
    print(output)
    
    # Check if PTIF file was created
    if not os.path.exists(ptif_path):
        print(f"❌ PTIF file not created: {ptif_path}")
        return False
    print(f"✅ PTIF file created: {ptif_path}")
    
    # Copy to public directory
    print("\nStep 2: Copying PTIF file to public directory")
    success, output = run_command(f"cp {ptif_path} data/images/public/")
    if not success:
        print("❌ Failed to copy PTIF file to public directory")
        return False
    print(f"✅ PTIF file copied to public directory")
    
    # Verify file exists in IIPServer container
    print("\nStep 3: Verifying file exists in IIPServer container")
    success, output = run_command("docker-compose exec iipserver ls -la /images/public/")
    if not success:
        print("❌ Failed to list files in IIPServer container")
        return False
    
    if TARGET_PTIF not in output:
        print(f"❌ {TARGET_PTIF} not found in IIPServer container")
        return False
    print(f"✅ {TARGET_PTIF} found in IIPServer container")
    
    return True

def test_iiif_functionality():
    """Test the IIIF functionality with the converted PTIF file."""
    print_header("Testing IIIF Functionality")
    
    # Test 1: Get info.json
    print("\nTest 1: Getting image info.json")
    info_url = f"{IIPSERVER_URL}?IIIF=/{TARGET_PTIF}/info.json"
    try:
        response = requests.get(info_url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Failed to get info.json: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
        
        try:
            info = response.json()
            print(f"✅ info.json accessible: {info_url}")
            print(f"   Image size: {info.get('width')}x{info.get('height')}")
        except json.JSONDecodeError:
            print(f"❌ info.json not valid JSON")
            print(f"   Response: {response.text[:200]}...")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing info.json: {e}")
        return False
    
    # Test 2: Get a thumbnail image
    print("\nTest 2: Getting thumbnail image")
    thumb_url = f"{IIPSERVER_URL}?IIIF=/{TARGET_PTIF}/full/200,/0/default.jpg"
    try:
        response = requests.get(thumb_url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Failed to get thumbnail: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
        
        thumb_size = len(response.content)
        print(f"✅ Thumbnail accessible: {thumb_url}")
        print(f"   Thumbnail size: {thumb_size} bytes")
        
        # Save the thumbnail for inspection
        with open("test_thumbnail.jpg", "wb") as f:
            f.write(response.content)
        print(f"   Saved thumbnail as test_thumbnail.jpg")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing thumbnail: {e}")
        return False
    
    # Test 3: Get a region of the image
    print("\nTest 3: Getting a region of the image")
    region_url = f"{IIPSERVER_URL}?IIIF=/{TARGET_PTIF}/0,0,100,100/full/0/default.jpg"
    try:
        response = requests.get(region_url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Failed to get image region: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
        
        region_size = len(response.content)
        print(f"✅ Image region accessible: {region_url}")
        print(f"   Region size: {region_size} bytes")
        
        # Save the region for inspection
        with open("test_region.jpg", "wb") as f:
            f.write(response.content)
        print(f"   Saved region as test_region.jpg")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing region: {e}")
        return False
    
    return True

def test_zenodo_built_in_conversion():
    """Test Zenodo's built-in conversion method (simulation)."""
    print_header("Testing Zenodo Built-in Conversion")
    print("\nNote: This is a simulated test since it requires a running Zenodo-RDM service")
    print("with database access and records with image files.")
    
    # Check if script exists
    if not os.path.exists("convert_existing_records.py"):
        print(f"❌ convert_existing_records.py not found")
        return False
    print(f"✅ convert_existing_records.py found")
    
    # Display usage instructions
    print("\nTo use the built-in conversion in a real environment:")
    print("1. Navigate to the site directory: cd site")
    print("2. Run the script with record IDs: python ../convert_existing_records.py RECORD_ID [RECORD_ID...]")
    print("3. The script will:")
    print("   - Resolve each record by ID")
    print("   - Use TilesProcessor to generate PTIF files")
    print("   - Extract image metadata")
    print("   - Update the record with IIIF information")
    
    return True

def run_all_tests():
    """Run all tests."""
    if not check_prerequisites():
        print("\n❌ Prerequisites check failed. Please fix the issues above.")
        return False
    
    custom_success = test_custom_conversion()
    iiif_success = test_iiif_functionality()
    built_in_success = test_zenodo_built_in_conversion()
    
    print_header("Test Summary")
    print(f"Custom PTIF Conversion: {'✅ PASSED' if custom_success else '❌ FAILED'}")
    print(f"IIIF Functionality: {'✅ PASSED' if iiif_success else '❌ FAILED'}")
    print(f"Zenodo Built-in Conversion (Simulation): {'✅ PASSED' if built_in_success else '❌ FAILED'}")
    
    if custom_success and iiif_success:
        print("\n🎉 IIIF functionality is working correctly!")
        print("You can now view IIIF images in a compatible viewer like Mirador.")
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
    
    return custom_success and iiif_success

if __name__ == "__main__":
    sys.exit(0 if run_all_tests() else 1) 
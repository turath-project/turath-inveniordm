#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test script to debug the workflow integration process
"""

import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('workflow-debug')

def test_upload_book():
    """Test only the book upload step of the workflow"""
    book_dir = "test_book_workflow/test_book"
    api_url = "https://localhost:5000/api"
    token = "GjjZoySCrOlEv1ce0eqqiRq8kMfZk0H29fY4oEQM1x1Kwftn7sOi9jwU6aNuAa2V6cfdfDmj2jhB1svzb5wms7El7gyn02Ocb5jj"
    
    logger.info(f"Testing upload_book.py with {book_dir}")
    
    # Prepare command
    cmd = [
        "python", "scripts/upload_book.py",
        "--book-dir", book_dir,
        "--api-url", api_url,
        "--token", token,
        "--no-verify-ssl",
        "--verbose"
    ]
    
    # Run with a timeout
    try:
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
        
        logger.info(f"Return code: {result.returncode}")
        logger.info(f"STDOUT: {result.stdout}")
        logger.info(f"STDERR: {result.stderr}")
        
        if result.returncode != 0:
            logger.error("Command failed")
            return False
        
        # Extract record ID
        record_id = None
        for line in result.stdout.splitlines():
            if "Created record with ID" in line:
                record_id = line.split("ID:")[-1].strip()
                break
            if "Record ID:" in line:
                record_id = line.split("ID:")[-1].strip()
                break
                
        if record_id:
            logger.info(f"Successfully extracted record ID: {record_id}")
            return record_id
        else:
            logger.error("Could not extract record ID")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Command timed out after 60 seconds")
        return False
    except Exception as e:
        logger.error(f"Error running command: {str(e)}")
        return False

def main():
    """Main function"""
    logger.info("Starting workflow debug test")
    
    # Test upload_book step
    record_id = test_upload_book()
    
    if not record_id:
        logger.error("Upload book test failed")
        return 1
    
    logger.info("Workflow debug test completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
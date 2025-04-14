#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to integrate external IIIF manifests with InvenioRDM.
This script creates a test record in InvenioRDM with an external IIIF manifest URL.
"""

import argparse
import json
import os
import sys
import requests
from urllib.parse import urljoin
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('iiif-integration-test')

class InvenioRDMIntegrationTest:
    """Test IIIF integration with InvenioRDM."""
    
    def __init__(self, api_url, token, verify_ssl=True):
        """Initialize the test client."""
        self.api_url = api_url.rstrip('/')
        self.token = token
        self.verify_ssl = verify_ssl
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
    def create_test_record(self, manifest_url, title="IIIF Test Record"):
        """Create a test record with an external IIIF manifest."""
        # Prepare minimal metadata
        metadata = {
            "metadata": {
                "title": title,
                "publication_date": "2023-01-01",
                "resource_type": {"id": "publication-book"},
                "creators": [
                    {
                        "person_or_org": {
                            "name": "IIIF Test",
                            "type": "personal"
                        }
                    }
                ],
                "languages": [{"id": "ara"}],
                "identifiers": [
                    {"scheme": "url", "identifier": manifest_url}
                ],
                "custom_fields": {
                    "iiif": {
                        "manifest": manifest_url
                    }
                }
            },
            "files": {"enabled": False}
        }
        
        logger.info(f"Creating test record with manifest URL: {manifest_url}")
        
        # Create record
        url = f"{self.api_url}/records"
        response = requests.post(
            url,
            headers=self.headers,
            json=metadata,
            verify=self.verify_ssl
        )
        
        if response.status_code == 201:
            record = response.json()
            record_id = record.get('id')
            logger.info(f"Created record with ID: {record_id}")
            
            # Publish the record
            publish_url = f"{self.api_url}/records/{record_id}/draft/actions/publish"
            publish_response = requests.post(
                publish_url,
                headers=self.headers,
                verify=self.verify_ssl
            )
            
            if publish_response.status_code == 202:
                logger.info(f"Published record: {record_id}")
                return True, record_id, "Record created and published successfully"
            else:
                logger.error(f"Failed to publish record: {publish_response.text}")
                return False, record_id, f"Record created but not published: {publish_response.text}"
        else:
            logger.error(f"Failed to create record: {response.text}")
            return False, None, f"Record creation failed: {response.text}"

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test IIIF Integration with InvenioRDM")
    parser.add_argument('--api-url', required=True, help='InvenioRDM API URL (e.g. https://inveniordm.yourdomain.com/api)')
    parser.add_argument('--token', required=True, help='InvenioRDM API token')
    parser.add_argument('--manifest-url', required=True, help='IIIF manifest URL to test')
    parser.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL verification')
    parser.add_argument('--title', default="IIIF Test Record", help='Title for the test record')
    return parser.parse_args()

def main():
    """Main entry point for the test script."""
    args = parse_args()
    
    test_client = InvenioRDMIntegrationTest(
        api_url=args.api_url,
        token=args.token,
        verify_ssl=not args.no_verify_ssl
    )
    
    success, record_id, message = test_client.create_test_record(
        manifest_url=args.manifest_url,
        title=args.title
    )
    
    if success:
        print(f"✓ Test successful! Record ID: {record_id}")
        record_url = f"{args.api_url.split('/api')[0]}/records/{record_id}"
        print(f"View record at: {record_url}")
    else:
        print(f"✗ Test failed: {message}")
        sys.exit(1)
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 
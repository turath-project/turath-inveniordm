#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Delete one or more records from InvenioRDM via the API.
"""

import os
import sys
import argparse
import requests
import logging
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('record_deleter')

# Default configuration values
DEFAULT_API_URL = os.environ.get("INVENIO_API_URL", "https://127.0.0.1:5000/api")
DEFAULT_API_TOKEN = os.environ.get("RDM_API_TOKEN", None)

def delete_record(api_url: str, token: str, record_id: str, verify_ssl: bool = True) -> bool:
    """Delete a single record.

    Args:
        api_url: Base API URL.
        token: API token for authentication.
        record_id: The ID of the record to delete.
        verify_ssl: Whether to verify SSL certificates.

    Returns:
        True if deletion was successful (or record didn't exist), False otherwise.
    """
    delete_url = f"{api_url}/records/{record_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    logger.info(f"Attempting to delete record: {record_id} at {delete_url}")

    try:
        response = requests.delete(
            delete_url,
            headers=headers,
            verify=verify_ssl
        )

        if response.status_code == 204:
            logger.info(f"Successfully deleted record: {record_id}")
            return True
        elif response.status_code == 404:
            logger.warning(f"Record not found (already deleted?): {record_id}")
            return True # Treat as success if it doesn't exist
        elif response.status_code == 403:
            logger.error(f"Permission denied to delete record: {record_id}")
            return False
        else:
            error_msg = f"Failed to delete record {record_id}. Status code: {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f" - {error_data.get('message', '')}"
                logger.debug(f"Full error response: {error_data}")
            except:
                error_msg += f" - {response.text}"
            logger.error(error_msg)
            return False

    except Exception as e:
        logger.error(f"Error during deletion request for {record_id}: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Delete one or more records from InvenioRDM via API.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "record_ids",
        metavar="RECORD_ID",
        nargs='+',
        help="One or more record IDs to delete."
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="InvenioRDM API URL (e.g., https://127.0.0.1:5000/api)"
    )
    parser.add_argument(
        "--token",
        default=DEFAULT_API_TOKEN,
        help="API token for authentication (reads RDM_API_TOKEN from env if not set)"
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        default=False,
        help="Don't verify SSL certificates"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if not args.token:
        logger.error("API token is required. Set RDM_API_TOKEN environment variable or use --token argument.")
        sys.exit(1)

    # Disable SSL verification warnings if requested
    verify_ssl = not args.no_verify_ssl
    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        logger.warning("SSL verification disabled.")

    # Normalize API URL
    api_url = args.api_url
    if not api_url.endswith('/api'):
         api_url = f"{api_url}/api"

    success_count = 0
    fail_count = 0

    for record_id in args.record_ids:
        if delete_record(api_url, args.token, record_id, verify_ssl):
            success_count += 1
        else:
            fail_count += 1

    logger.info(f"Deletion summary: {success_count} successful, {fail_count} failed.")

    if fail_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main() 
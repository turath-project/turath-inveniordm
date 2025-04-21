#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Delete ALL records from InvenioRDM via the API.

WARNING: This is a destructive operation. Use with extreme caution.
Requires the --yes-i-am-sure flag to proceed.
"""

import os
import sys
import argparse
import requests
import logging
import time
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('record_deleter_all')

# Default configuration values
DEFAULT_API_URL = os.environ.get("INVENIO_API_URL", "https://127.0.0.1:5000/api")
DEFAULT_API_TOKEN = os.environ.get("RDM_API_TOKEN", None)

def get_all_record_ids(api_url: str, token: str, verify_ssl: bool = True) -> list:
    """Fetch all record IDs using the search API.

    Args:
        api_url: Base API URL.
        token: API token for authentication.
        verify_ssl: Whether to verify SSL certificates.

    Returns:
        A list of all record IDs.
    """
    record_ids = []
    search_url = f"{api_url}/records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    params = {
        "size": 250,  # Fetch records in batches
        "page": 1,
        "allversions": "true", # Ensure we get all versions if needed
        "q": "*" # Add wildcard query to potentially broaden results
    }

    logger.info(f"Fetching record IDs from {search_url} using query '{params['q']}'...")
    total_fetched = 0

    while True:
        try:
            logger.debug(f"Fetching page {params['page']}...")
            response = requests.get(
                search_url,
                headers=headers,
                params=params,
                verify=verify_ssl
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch records (page {params['page']}). Status: {response.status_code}")
                try:
                    logger.error(f"Response: {response.json()}")
                except:
                    logger.error(f"Response: {response.text}")
                break # Stop fetching if there's an error

            data = response.json()
            hits = data.get('hits', {}).get('hits', [])
            total = data.get('hits', {}).get('total', 0)

            if not hits:
                logger.info("No more records found.")
                break # No more records

            page_ids = [hit['id'] for hit in hits]
            record_ids.extend(page_ids)
            total_fetched += len(page_ids)
            logger.info(f"Fetched {len(page_ids)} IDs (Total: {total_fetched}/{total})...")

            # Check if we have fetched all records
            if total_fetched >= total:
                logger.info(f"Finished fetching all {total} record IDs.")
                break

            # Go to the next page
            params['page'] += 1
            time.sleep(0.1) # Small delay between pages

        except Exception as e:
            logger.error(f"Error fetching record IDs (page {params['page']}): {str(e)}")
            logger.debug(traceback.format_exc())
            break # Stop fetching on error

    logger.info(f"Found {len(record_ids)} unique record IDs to target for deletion.")
    return record_ids

def delete_record(api_url: str, token: str, record_id: str, verify_ssl: bool = True) -> bool:
    """Delete a single record (reuse logic).
    Returns True if deletion was successful or record didn't exist, False otherwise.
    """
    delete_url = f"{api_url}/records/{record_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    logger.debug(f"Attempting DELETE {delete_url}")
    try:
        response = requests.delete(delete_url, headers=headers, verify=verify_ssl)
        if response.status_code == 204:
            logger.info(f"Successfully deleted record: {record_id}")
            return True
        elif response.status_code == 404:
            logger.warning(f"Record {record_id} not found (already deleted?). Treating as success.")
            return True
        elif response.status_code == 403:
            logger.error(f"Permission denied to delete record: {record_id}")
            return False
        else:
            error_msg = f"Failed to delete record {record_id}. Status: {response.status_code}"
            try: error_msg += f" - {response.json().get('message', '')}"
            except: error_msg += f" - {response.text}"
            logger.error(error_msg)
            return False
    except Exception as e:
        logger.error(f"Error during deletion request for {record_id}: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Delete ALL records from InvenioRDM via API. Requires --yes-i-am-sure.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
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
        "--yes-i-am-sure",
        action="store_true",
        help="Confirmation flag required to proceed with deleting ALL records."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (debug) output"
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if not args.token:
        logger.error("API token is required. Set RDM_API_TOKEN environment variable or use --token argument.")
        sys.exit(1)

    if not args.yes_i_am_sure:
        logger.error("FATAL: --yes-i-am-sure flag is required to delete all records.")
        logger.error("This action is irreversible. Re-run with the flag if you are absolutely sure.")
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

    # Get all IDs
    record_ids_to_delete = get_all_record_ids(api_url, args.token, verify_ssl)

    if not record_ids_to_delete:
        logger.info("No records found to delete.")
        sys.exit(0)

    logger.warning(f"Proceeding to delete {len(record_ids_to_delete)} records. This cannot be undone.")
    logger.warning("Sleeping for 5 seconds before starting...")
    time.sleep(5)

    success_count = 0
    fail_count = 0

    for i, record_id in enumerate(record_ids_to_delete):
        logger.info(f"Deleting record {i+1}/{len(record_ids_to_delete)}: {record_id}")
        if delete_record(api_url, args.token, record_id, verify_ssl):
            success_count += 1
        else:
            fail_count += 1
        time.sleep(0.1) # Small delay between deletions

    logger.info("--- Deletion Complete ---")
    logger.info(f"Deletion summary: {success_count} successful, {fail_count} failed.")

    if fail_count > 0:
        logger.error("Some records failed to delete. Check logs for details.")
        sys.exit(1)
    else:
        logger.info("All targeted records deleted successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main() 
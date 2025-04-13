"""Configuration for book import scripts."""
import os
from pathlib import Path

# Find project root (parent directory of the scripts directory)
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent

# InvenioRDM API configuration
API_BASE_URL = os.environ.get("INVENIO_API_URL", "https://127.0.0.1:5000/api")
# Get API token from environment, with fallback to None
API_TOKEN = os.environ.get("INVENIO_API_TOKEN", None)

# IIIF server configuration
IIIF_SERVER_URL = os.environ.get("IIIF_SERVER_URL", "http://localhost:8182/iiif/3")
IIIF_STORAGE_PATH = os.environ.get("IIIF_STORAGE_PATH", str(PROJECT_ROOT / "var" / "iiif-storage"))

# Ensure storage directory exists
os.makedirs(IIIF_STORAGE_PATH, exist_ok=True)
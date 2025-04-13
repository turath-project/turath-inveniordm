# Custom Script Documentation

This documentation covers custom scripts located in `scripts/AlA`

## Shell Scripts

### change_admin_password.sh

Change password for admin@zenodo.org user
pipenv run invenio shell -c "from change_password import change_user_password; change_user_password('admin@zenodo.org', '123456')"
echo "Password for admin@zenodo.org has been changed to 123456" 

```bash
./scripts/AlA/change_admin_password.sh
# or
make run SCRIPT=change_admin_password
```

### convert_images.sh

#!/bin/bash
Simple script to convert images to PTIF format for IIPServer
Requires vips to be installed: apt-get install -y libvips-tools
set -e
Default image directory
IMAGE_DIR="./data/images"
Check if vips is installed
if ! command -v vips &> /dev/null; then
    echo "Error: vips is not installed. Please install with 'apt-get install -y libvips-tools' or 'brew install vips'"
    exit 1
fi
Ensure the directory structure exists
mkdir -p "$IMAGE_DIR/public" "$IMAGE_DIR/private"
Process all PNG, JPG, and TIF files
echo "Searching for image files in $IMAGE_DIR..."

```bash
./scripts/AlA/convert_images.sh
# or
make run SCRIPT=convert_images
```

### converter-entrypoint.sh

#!/bin/bash
PTIF Converter entrypoint
Watches for image files and converts them to PTIF format
set -e
echo "Starting PTIF Converter service"
echo "================================"
echo "This container watches for image files and converts them to PTIF format"
echo "It's a substitute for the Zenodo worker service during development"
echo ""
Ensure directories exist
mkdir -p /images/public /images/private
Function to convert image to PTIF
convert_to_ptif() {
    local img="$1"
    local ptif_file="${img%.*}.ptif"
    

```bash
./scripts/AlA/converter-entrypoint.sh
# or
make run SCRIPT=converter-entrypoint
```

### create_admin.sh

Create admin role
pipenv run invenio roles create admin
Create admin user
pipenv run invenio users create admin@turath.com --password 123456 --active --confirm
Grant administration access to user
pipenv run invenio access allow administration-access user admin@turath.com
Add user to admin role
pipenv run invenio roles add admin@turath.com admin
Grant superuser access to admin role
pipenv run invenio access allow superuser-access role admin 

```bash
./scripts/AlA/create_admin.sh
# or
make run SCRIPT=create_admin
```

### create_missing_indices.sh

Script to create missing OpenSearch indices and fix common errors
echo "Creating missing OpenSearch indices..."
Stats indices
echo "Creating stats indices..."
pipenv run invenio index init --force zenodo-stats-file-download
pipenv run invenio index init --force zenodo-stats-record-view
Moderation indices
echo "Creating moderation indices..."
pipenv run invenio index init --force zenodo-moderation-queries-rdmrecords-records-record-v7.0.0
Search indices - in case they're missing
echo "Creating/refreshing search indices..."
pipenv run invenio index init --force --yes
Add note about DOI errors

```bash
./scripts/AlA/create_missing_indices.sh
# or
make run SCRIPT=create_missing_indices
```

### fix_admin_password.sh

Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
Change password for admin@zenodo.org user
cd "$SCRIPT_DIR"
echo "Creating temporary Python script..."
cat > temp_change_password.py << 'EOF'
from flask import current_app
from invenio_db import db
from invenio_accounts.models import User
from flask_security.utils import hash_password
def change_user_password(email, new_password):
    """Change password for a user."""
    user = User.query.filter_by(email=email).first()

```bash
./scripts/AlA/fix_admin_password.sh
# or
make run SCRIPT=fix_admin_password
```

### generate_new_token.sh

#
Script to reset admin password and generate a new API token
#
Get the current directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
Reset admin password first
echo "==== Step 1: Resetting admin password ===="
"${SCRIPT_DIR}/reset_admin_password.sh"
Change to project root
cd "$PROJECT_ROOT"
echo -e "\n==== Step 2: Generating new API token ===="
echo "Creating temporary Python script..."
cat > temp_create_token.py << 'EOF'

```bash
./scripts/AlA/generate_new_token.sh
# or
make run SCRIPT=generate_new_token
```

### reset_admin_password.sh

Get the project root directory (2 levels up from this script)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
Change to project root to ensure all invenio commands run from there
cd "$PROJECT_ROOT"
echo "Creating temporary Python script..."
cat > temp_change_password.py << 'EOF'
from flask import current_app
from invenio_db import db
from invenio_accounts.models import User
from flask_security.utils import hash_password
def change_user_password(email, new_password):
    """Change password for a user."""
    user = User.query.filter_by(email=email).first()

```bash
./scripts/AlA/reset_admin_password.sh
# or
make run SCRIPT=reset_admin_password
```

### setup_iiif_for_record.sh

#!/bin/bash
Setup IIIF for a record - automates PTIF conversion and IIPServer setup
if [ $# -lt 1 ]; then
    echo "Usage: $0 RECORD_ID [FILE_NAME]"
    echo "  RECORD_ID: Record ID to process"
    echo "  FILE_NAME: Optional specific file to process (otherwise all image files)"
    exit 1
fi
RECORD_ID=$1
SPECIFIC_FILE=$2
1. Check record and get files
echo "Checking record $RECORD_ID..."
python check_record.py $RECORD_ID
2. Create necessary directories
echo "Creating directories..."
docker-compose exec iipserver mkdir -p /images/public

```bash
./scripts/AlA/setup_iiif_for_record.sh
# or
make run SCRIPT=setup_iiif_for_record
```

## Python Scripts

### batch_convert.py


Batch script to convert all images in a Zenodo-RDM record to PTIF format for IIIF support.

import os
import sys
import requests
import json
import subprocess
import shutil
import time
from urllib3.exceptions import InsecureRequestWarning
Import our single file conversion script
from convert_to_ptif import convert_to_ptif, copy_to_iipserver
Disable SSL warnings for local testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

```bash
python scripts/AlA/batch_convert.py
# or
make run SCRIPT=batch_convert
```

### change_password.py

from flask import current_app
from flask.cli import with_appcontext
from invenio_db import db
from invenio_accounts.models import User
from flask_security.utils import hash_password
@with_appcontext
def change_user_password(email, new_password):
Change password for a user.
user = User.query.filter_by(email=email).first()
if not user:
print(f"User with email {email} not found.")
return False

user.password = hash_password(new_password)
db.session.commit()
print(f"Password for user {email} has been updated successfully.")
return True

```bash
python scripts/AlA/change_password.py
# or
make run SCRIPT=change_password
```

### check_iiif.py


Script to check IIIF functionality for a record.

import sys
import requests
import json
from urllib3.exceptions import InsecureRequestWarning
Disable SSL warnings for local testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
if len(sys.argv) < 2:
print(f"Usage: {sys.argv[0]} RECORD_ID")
sys.exit(1)
RECORD_ID = sys.argv[1]
print(f"Checking IIIF functionality for record {RECORD_ID}...")

```bash
python scripts/AlA/check_iiif.py
# or
make run SCRIPT=check_iiif
```

### check_record.py


Simple script to check record files.

import sys
import requests
import json
from urllib3.exceptions import InsecureRequestWarning
Disable SSL warnings for local testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
RECORD_ID = "202"  # Default record ID
if len(sys.argv) > 1:
RECORD_ID = sys.argv[1]
print(f"Checking record {RECORD_ID}...")
ry:
# Get record data

```bash
python scripts/AlA/check_record.py
# or
make run SCRIPT=check_record
```

### convert_existing_records.py


Script to convert existing records' images to PTIF format for IIIF support.
This utilizes Zenodo-RDM's built-in TilesProcessor class.

import sys
import os
from invenio_rdm_records.proxies import current_rdm_records_service as service
from invenio_rdm_records.records.processors.tiles import TilesProcessor
from invenio_records_resources.services.files.processors.image import ImageMetadataExtractor
from invenio_records_resources.services.uow import UnitOfWork, RecordCommitOp
def generate_iiif_tiles(recid):
Generate IIIF tiles for a record.
print(f"Processing record {recid}...")

with UnitOfWork() as uow:
ry:
record = service.record_cls.pid.resolve(recid)

```bash
python scripts/AlA/convert_existing_records.py
# or
make run SCRIPT=convert_existing_records
```

### convert_to_ptif.py


Script to convert an image file to PTIF format for IIIF support.
This uses the vips command-line tool directly.

import os
import sys
import subprocess
import shutil
def convert_to_ptif(input_file, output_file=None):
Convert an image file to PTIF format.
if not os.path.exists(input_file):
print(f"Error: Input file '{input_file}' does not exist.")
return False

if output_file is None:
# Replace the extension with .ptif
base, _ = os.path.splitext(input_file)

```bash
python scripts/AlA/convert_to_ptif.py
# or
make run SCRIPT=convert_to_ptif
```

### create_token.py


Create an API token programmatically for Zenodo RDM.
Usage:
python create_token.py [--user=your_email@example.com] [--password=your_password] [--name="Token name"] [--scopes="deposit:write deposit:actions"]
If arguments are not provided, the script will look for them in the .env file.

import argparse
import os
import sys
from datetime import datetime, timedelta
from flask import current_app
from invenio_app.factory import create_app
from invenio_db import db
from invenio_oauth2server.models import Client, Token
from invenio_accounts.models import User

```bash
python scripts/AlA/create_token.py
# or
make run SCRIPT=create_token
```

### create_token_cli.py


Create an API token via Flask CLI for Zenodo RDM.
Usage:
flask --app create_token_cli create-token --email=admin@zenodo.org --name="My API Token"

import click
import os
from flask import current_app
from flask.cli import with_appcontext
from invenio_db import db
from invenio_oauth2server.models import Client, Token
from invenio_accounts.models import User
from werkzeug.security import gen_salt
from datetime import datetime, timedelta
@click.group()

```bash
python scripts/AlA/create_token_cli.py
# or
make run SCRIPT=create_token_cli
```

### get_file.py


Script to download a file from a Zenodo-RDM record.

import sys
import requests
import os
from urllib3.exceptions import InsecureRequestWarning
Disable SSL warnings for local testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
if len(sys.argv) < 3:
print(f"Usage: {sys.argv[0]} RECORD_ID FILENAME [OUTPUT_DIR]")
sys.exit(1)
RECORD_ID = sys.argv[1]
FILENAME = sys.argv[2]
OUTPUT_DIR = sys.argv[3] if len(sys.argv) > 3 else "."

```bash
python scripts/AlA/get_file.py
# or
make run SCRIPT=get_file
```

### list_user_roles.py

from flask import current_app
from flask.cli import with_appcontext
from invenio_db import db
from invenio_accounts.models import User, Role
from invenio_access.models import ActionUsers, ActionRoles
@with_appcontext
def list_user_roles():
List all users and their roles in the database.
users = User.query.all()
roles = Role.query.all()

print("\n=== USERS ===")
print("Total users:", len(users))
print("ID | Email | Active | Confirmed")
print("-" * 50)
for user in users:
print(f"{user.id} | {user.email} | {user.active} | {user.confirmed_at is not None}")


```bash
python scripts/AlA/list_user_roles.py
# or
make run SCRIPT=list_user_roles
```

### list_users.py

from flask import current_app
from flask.cli import with_appcontext
from invenio_db import db
from invenio_accounts.models import User
@with_appcontext
def list_users():
List all users in the database.
users = User.query.all()
print("Total users:", len(users))
print("ID | Email | Active | Confirmed")
print("-" * 50)
for user in users:
print(f"{user.id} | {user.email} | {user.active} | {user.confirmed_at is not None}")
if __name__ == '__main__':
list_users() 

```bash
python scripts/AlA/list_users.py
# or
make run SCRIPT=list_users
```

### serve_viewer.py


Simple HTTP server to serve the IIIF viewer HTML page, handling CORS issues.

import http.server
import socketserver
import os
PORT = 3000
class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
Custom HTTP request handler with CORS headers.

def end_headers(self):
Add CORS headers to every response.
self.send_header('Access-Control-Allow-Origin', '*')
self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
self.send_header('Access-Control-Allow-Headers', 'Content-Type')
super().end_headers()

```bash
python scripts/AlA/serve_viewer.py
# or
make run SCRIPT=serve_viewer
```

### test_iiif_conversion.py


Test script to verify PTIF conversion and IIIF functionality.
Tests both custom conversion and Zenodo's built-in tools.

import os
import sys
import json
import subprocess
import requests
import time
Configuration
TEST_IMAGE = "test_image.png"  # Should exist in data/images/
TARGET_PTIF = "test_image.ptif"  # Will be generated
IIPSERVER_URL = "http://localhost:8080/fcgi-bin/iipsrv.fcgi"
def print_header(title):
Print a formatted header.

```bash
python scripts/AlA/test_iiif_conversion.py
# or
make run SCRIPT=test_iiif_conversion
```


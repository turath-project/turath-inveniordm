#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Script to reset admin password and generate a new API token
#

# Get the current directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Reset admin password first
echo "==== Step 1: Resetting admin password ===="
"${SCRIPT_DIR}/reset_admin_password.sh"

# Change to project root
cd "$PROJECT_ROOT"

echo -e "\n==== Step 2: Generating new API token ===="
echo "Creating temporary Python script..."
cat > temp_create_token.py << 'EOF'
#!/usr/bin/env python
import os
import re
from datetime import datetime
from flask import current_app
from invenio_db import db
from invenio_oauth2server.models import Client, Token
from invenio_accounts.models import User
from werkzeug.security import gen_salt

# Configuration
EMAIL = 'admin@zenodo.org'
NAME = f"API Token {datetime.now().strftime('%Y-%m-%d')}"
SCOPES = 'deposit:write deposit:actions'

def create_api_token():
    """Create an API token for the admin user."""
    # Find the user
    user = User.query.filter_by(email=EMAIL).first()
    if not user:
        print(f"User with email {EMAIL} not found")
        return None
    
    # Create a client for this token
    client = Client(
        client_id=gen_salt(40),
        client_secret=gen_salt(60),
        name=NAME,
        description=f"Personal API token for {EMAIL}",
        user_id=user.id,
        is_confidential=False,
        is_internal=True,
        _default_scopes=SCOPES,
    )
    
    # Create the token
    token = Token(
        client_id=client.client_id,
        user_id=user.id,
        token_type="bearer",
        access_token=gen_salt(100),
        refresh_token=None,
        expires=None,
        _scopes=SCOPES,
        is_personal=True,
        is_internal=False,
    )
    
    # Save to database
    db.session.add(client)
    db.session.add(token)
    db.session.commit()
    
    print(f"Token created successfully for {EMAIL}")
    print(f"Token name: {NAME}")
    print(f"Scopes: {SCOPES}")
    print("No expiration date")
    
    return token.access_token

# Create token and update .env file
token = create_api_token()
if token:
    print("\nYour API token:")
    print(token)
    
    try:
        env_path = '.env'
        if os.path.exists(env_path):
            with open(env_path, 'r') as file:
                env_content = file.read()
            
            if 'RDM_API_TOKEN=' in env_content:
                env_content = re.sub(
                    r'RDM_API_TOKEN=.*',
                    f'RDM_API_TOKEN={token}',
                    env_content
                )
            else:
                env_content += f"\nRDM_API_TOKEN={token}\n"
            
            with open(env_path, 'w') as file:
                file.write(env_content)
            
            print("\nUpdated .env file with the new token.")
        else:
            print("\nNo .env file found.")
    except Exception as e:
        print(f"\nError updating .env file: {str(e)}")
EOF

echo "Running invenio shell command..."
pipenv run invenio shell -c "$(cat temp_create_token.py)"

# Clean up
rm temp_create_token.py

echo -e "\n==== Complete! ===="
echo "Your admin password has been reset to '123456' and a new API token has been generated."
echo "The token has been saved to your .env file as RDM_API_TOKEN." 
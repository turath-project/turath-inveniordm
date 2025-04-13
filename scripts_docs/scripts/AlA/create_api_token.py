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

def update_env_file(token):
    """Update the .env file with the new token."""
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

if __name__ == "__main__":
    # Create token and update .env file
    token = create_api_token()
    if token:
        print("\nYour API token:")
        print(token)
        update_env_file(token) 
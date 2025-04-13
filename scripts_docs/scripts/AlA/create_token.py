#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create an API token programmatically for Zenodo RDM.

Usage:
    python create_token.py [--user=your_email@example.com] [--password=your_password] [--name="Token name"] [--scopes="deposit:write deposit:actions"]

If arguments are not provided, the script will look for them in the .env file.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from flask import current_app
from invenio_app.factory import create_app
from invenio_db import db
from invenio_oauth2server.models import Client, Token
from invenio_accounts.models import User
from invenio_access.permissions import system_identity
from flask_security.utils import verify_password
from werkzeug.security import gen_salt
from uuid import uuid4
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def create_api_token(email, password, name, scopes, expires_in=None):
    """
    Create an API token for the given user with the specified scopes.
    
    Args:
        email: User's email
        password: User's password
        name: Token name
        scopes: Space-separated list of scopes (e.g., "deposit:write deposit:actions")
        expires_in: Token expiration time in days (None for no expiration)
        
    Returns:
        The token string or None if creation failed
    """
    # Find the user
    user = User.query.filter_by(email=email).first()
    if not user:
        print(f"User with email {email} not found")
        return None
    
    # Verify password
    if not verify_password(password, user.password):
        print("Invalid password")
        return None
    
    # Create a client for this token
    client = Client(
        client_id=gen_salt(40),
        client_secret=gen_salt(60),
        name=name,
        description=f"Personal API token for {email}",
        user_id=user.id,
        is_confidential=False,
        is_internal=True,
        _default_scopes=scopes,
    )
    
    # Calculate expiration if provided
    expires = datetime.utcnow() + timedelta(days=expires_in) if expires_in else None
    
    # Create the token
    token = Token(
        client_id=client.client_id,
        user_id=user.id,
        token_type="bearer",
        access_token=gen_salt(100),
        refresh_token=None,
        expires=expires,
        _scopes=scopes,
        is_personal=True,
        is_internal=False,
    )
    
    # Save to database
    db.session.add(client)
    db.session.add(token)
    db.session.commit()
    
    print(f"Token created successfully for {email}")
    print(f"Token name: {name}")
    print(f"Scopes: {scopes}")
    if expires:
        print(f"Expires: {expires}")
    else:
        print("No expiration date")
    
    return token.access_token

def main():
    parser = argparse.ArgumentParser(description='Create an API token for Zenodo RDM')
    parser.add_argument('--user', help='User email (defaults to IIPSERVER_USERNAME in .env)')
    parser.add_argument('--password', help='User password (defaults to IIPSERVER_PASSWORD in .env)')
    parser.add_argument('--name', help='Token name (defaults to "API Token <current date>")')
    parser.add_argument('--scopes', help='Space-separated list of scopes (defaults to "deposit:write deposit:actions")')
    parser.add_argument('--expires', type=int, help='Expiration time in days (default: no expiration)')
    
    args = parser.parse_args()
    
    # Get values from environment variables if not provided as arguments
    email = args.user or os.getenv('IIPSERVER_USERNAME')
    password = args.password or os.getenv('IIPSERVER_PASSWORD')
    name = args.name or f"API Token {datetime.now().strftime('%Y-%m-%d')}"
    scopes = args.scopes or os.getenv('API_TOKEN_SCOPES', 'deposit:write deposit:actions')
    expires = args.expires or int(os.getenv('API_TOKEN_EXPIRES_DAYS', '0')) or None
    
    # Validate required values
    if not email:
        print("Error: User email is required. Provide it with --user or set IIPSERVER_USERNAME in .env")
        return 1
    
    if not password:
        print("Error: Password is required. Provide it with --password or set IIPSERVER_PASSWORD in .env")
        return 1
    
    # Create the Flask application
    app = create_app()
    with app.app_context():
        token = create_api_token(
            email, 
            password, 
            name, 
            scopes,
            expires
        )
        if token:
            print("\nYour API token:")
            print(token)
            
            # Update .env file with the new token if requested
            update_env = input("\nDo you want to update RDM_API_TOKEN in your .env file? (y/n): ").lower()
            if update_env == 'y':
                try:
                    with open('.env', 'r') as file:
                        env_content = file.read()
                    
                    if 'RDM_API_TOKEN=' in env_content:
                        env_content = env_content.replace(
                            f"RDM_API_TOKEN={os.getenv('RDM_API_TOKEN', '')}",
                            f"RDM_API_TOKEN={token}"
                        )
                    else:
                        env_content += f"\nRDM_API_TOKEN={token}\n"
                    
                    with open('.env', 'w') as file:
                        file.write(env_content)
                    
                    print("Updated .env file with the new token.")
                except Exception as e:
                    print(f"Error updating .env file: {str(e)}")
            
            return 0
    
    return 1

if __name__ == "__main__":
    sys.exit(main()) 
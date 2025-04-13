#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create an API token via Flask CLI for Zenodo RDM.

Usage:
    flask --app create_token_cli create-token --email=admin@zenodo.org --name="My API Token"
"""

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
def tokens_cli():
    """Token management commands."""
    pass

@tokens_cli.command('create-token')
@click.option('--email', required=True, help='User email')
@click.option('--name', required=True, help='Token name')
@click.option('--scopes', default='deposit:write deposit:actions', help='Space-separated list of scopes')
@click.option('--expires', type=int, help='Expiration time in days (default: no expiration)')
@with_appcontext
def create_token(email, name, scopes, expires):
    """Create a new API token for a user."""
    # Find the user
    user = User.query.filter_by(email=email).first()
    if not user:
        click.echo(f"User with email {email} not found")
        return
    
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
    expires_at = datetime.utcnow() + timedelta(days=expires) if expires else None
    
    # Create the token
    token = Token(
        client_id=client.client_id,
        user_id=user.id,
        token_type="bearer",
        access_token=gen_salt(100),
        refresh_token=None,
        expires=expires_at,
        _scopes=scopes,
        is_personal=True,
        is_internal=False,
    )
    
    # Save to database
    db.session.add(client)
    db.session.add(token)
    db.session.commit()
    
    click.echo(f"Token created successfully for {email}")
    click.echo(f"Token name: {name}")
    click.echo(f"Scopes: {scopes}")
    if expires_at:
        click.echo(f"Expires: {expires_at}")
    else:
        click.echo("No expiration date")
    
    click.echo("\nYour API token:")
    click.echo(token.access_token)
    
    # Update .env file with the new token if requested
    update_env = click.confirm("Do you want to update RDM_API_TOKEN in your .env file?")
    if update_env:
        try:
            env_path = os.path.join(os.getcwd(), '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r') as file:
                    env_content = file.read()
                
                if 'RDM_API_TOKEN=' in env_content:
                    import re
                    env_content = re.sub(
                        r'RDM_API_TOKEN=.*',
                        f'RDM_API_TOKEN={token.access_token}',
                        env_content
                    )
                else:
                    env_content += f"\nRDM_API_TOKEN={token.access_token}\n"
                
                with open(env_path, 'w') as file:
                    file.write(env_content)
                
                click.echo("Updated .env file with the new token.")
            else:
                click.echo("No .env file found.")
        except Exception as e:
            click.echo(f"Error updating .env file: {str(e)}")

if __name__ == '__main__':
    tokens_cli() 
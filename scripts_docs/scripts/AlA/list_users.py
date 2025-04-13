#!/usr/bin/env python
from flask import current_app
from flask.cli import with_appcontext
from invenio_db import db
from invenio_accounts.models import User

@with_appcontext
def list_users():
    """List all users in the database."""
    users = User.query.all()
    print("Total users:", len(users))
    print("ID | Email | Active | Confirmed")
    print("-" * 50)
    for user in users:
        print(f"{user.id} | {user.email} | {user.active} | {user.confirmed_at is not None}")

if __name__ == '__main__':
    list_users() 
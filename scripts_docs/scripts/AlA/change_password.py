#!/usr/bin/env python
from flask import current_app
from flask.cli import with_appcontext
from invenio_db import db
from invenio_accounts.models import User
from flask_security.utils import hash_password

@with_appcontext
def change_user_password(email, new_password):
    """Change password for a user."""
    user = User.query.filter_by(email=email).first()
    if not user:
        print(f"User with email {email} not found.")
        return False
    
    user.password = hash_password(new_password)
    db.session.commit()
    print(f"Password for user {email} has been updated successfully.")
    return True

if __name__ == '__main__':
    change_user_password('admin@zenodo.org', '123456') 
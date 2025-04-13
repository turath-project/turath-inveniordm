#!/usr/bin/env python
from flask import current_app
from flask.cli import with_appcontext
from invenio_db import db
from invenio_accounts.models import User, Role
from invenio_access.models import ActionUsers, ActionRoles

@with_appcontext
def list_user_roles():
    """List all users and their roles in the database."""
    users = User.query.all()
    roles = Role.query.all()
    
    print("\n=== USERS ===")
    print("Total users:", len(users))
    print("ID | Email | Active | Confirmed")
    print("-" * 50)
    for user in users:
        print(f"{user.id} | {user.email} | {user.active} | {user.confirmed_at is not None}")
    
    print("\n=== ROLES ===")
    print("Total roles:", len(roles))
    print("ID | Name | Description")
    print("-" * 50)
    for role in roles:
        print(f"{role.id} | {role.name} | {role.description}")
    
    print("\n=== USER ROLES ===")
    print("User | Roles")
    print("-" * 50)
    for user in users:
        roles_str = ", ".join([role.name for role in user.roles])
        print(f"{user.email} | {roles_str}")
    
    print("\n=== ACTION USERS ===")
    print("Action | User")
    print("-" * 50)
    action_users = ActionUsers.query.all()
    for au in action_users:
        user = User.query.get(au.argument)
        email = user.email if user else "Unknown"
        print(f"{au.action} | {email}")
    
    print("\n=== ACTION ROLES ===")
    print("Action | Role")
    print("-" * 50)
    action_roles = ActionRoles.query.all()
    for ar in action_roles:
        role = Role.query.get(ar.argument)
        name = role.name if role else "Unknown"
        print(f"{ar.action} | {name}")

if __name__ == '__main__':
    list_user_roles() 
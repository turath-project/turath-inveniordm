#!/usr/bin/env bash
# -*- coding: utf-8 -*-

# Get the project root directory (2 levels up from this script)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Change to project root to ensure all invenio commands run from there
cd "$PROJECT_ROOT"

echo "Creating temporary Python script..."
cat > temp_change_password.py << 'EOF'
#!/usr/bin/env python
from flask import current_app
from invenio_db import db
from invenio_accounts.models import User
from flask_security.utils import hash_password

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

change_user_password('admin@zenodo.org', '123456')
EOF

echo "Running invenio shell command..."
pipenv run invenio shell -c "$(cat temp_change_password.py)"

# Clean up
rm temp_change_password.py

echo "Password for admin@zenodo.org has been changed to 123456" 
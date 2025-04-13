#!/bin/bash

# Make the script exit on any error
set -e

echo "Setting up admin user and permissions..."

# Skip role creation since it already exists
echo "Using existing admin role..."

# Check if user exists first
if pipenv run invenio users show admin@turath.com > /dev/null 2>&1; then
    echo "$(tput setaf 2)✓ Admin user exists$(tput sgr0)"
else
    echo "Creating admin user..."
    pipenv run invenio users create admin@turath.com --password 123456 --active --confirm
fi

# Check if user has admin role before trying to add it
echo "Setting up permissions..."
if ! pipenv run invenio roles list admin@turath.com | grep -q "admin"; then
    echo "Adding admin role to user..."
    pipenv run invenio access allow administration-access user admin@turath.com
    pipenv run invenio roles add admin@turath.com admin
    pipenv run invenio access allow superuser-access role admin
else
    echo "$(tput setaf 2)✓ Admin permissions already set$(tput sgr0)"
fi

echo "$(tput setaf 2)✓ Admin setup completed successfully!$(tput sgr0)"

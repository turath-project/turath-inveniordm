#!/usr/bin/env bash
# -*- coding: utf-8 -*-

# Create admin role
pipenv run invenio roles create admin

# Create admin user
pipenv run invenio users create admin@turath.com --password 123456 --active --confirm

# Grant administration access to user
pipenv run invenio access allow administration-access user admin@turath.com

# Add user to admin role
pipenv run invenio roles add admin@turath.com admin

# Grant superuser access to admin role
pipenv run invenio access allow superuser-access role admin 
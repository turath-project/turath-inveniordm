#!/usr/bin/env bash
# -*- coding: utf-8 -*-

# Change password for admin@zenodo.org user
pipenv run invenio shell -c "from change_password import change_user_password; change_user_password('admin@zenodo.org', '123456')"

echo "Password for admin@zenodo.org has been changed to 123456" 
#!/usr/bin/env bash
# -*- coding: utf-8 -*-

# Script to create missing OpenSearch indices and fix common errors
echo "Creating missing OpenSearch indices..."

# Stats indices
echo "Creating stats indices..."
pipenv run invenio index init --force zenodo-stats-file-download
pipenv run invenio index init --force zenodo-stats-record-view

# Moderation indices
echo "Creating moderation indices..."
pipenv run invenio index init --force zenodo-moderation-queries-rdmrecords-records-record-v7.0.0

# Search indices - in case they're missing
echo "Creating/refreshing search indices..."
pipenv run invenio index init --force --yes

# Add note about DOI errors
echo ""
echo "NOTE: DataCite DOI registration errors are expected in a development environment"
echo "These errors appear as: 'DataCite error: The resource you are looking for doesn't exist'"
echo "They won't affect basic functionality of the system unless you need DOI registration"
echo ""

echo "Done! Missing indices have been created." 
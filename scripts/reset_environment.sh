#!/bin/bash
#
# Reset InvenioRDM Database and Search Indices
#
# WARNING: This script destroys existing search indices.
# Use after commands like 'docker compose down' that might reset data volumes,
# or when you need a clean database/search state.
#
# Ensure your .env file is correctly configured before running.

set -e # Exit immediately if a command exits with a non-zero status.

echo "==== Resetting InvenioRDM Environment ===="

# 1. Initialize Database (Create Tables)
echo "--- Initializing database tables... ---"
pipenv run invenio db init create

# 2. Load Database Fixtures (Default Data)
echo "--- Loading database fixtures (vocabularies, etc.)... ---"
pipenv run invenio rdm-records fixtures

# 2.5 Create Default File Location
echo "--- Creating default file storage location... ---"
pipenv run invenio files location create default file:///opt/invenio/var/instance/data --default

# 2.6 Fix Data Directory Permissions in Container
echo "--- Ensuring correct permissions in web-ui container data directory... ---"
docker compose exec web-ui chown -R invenio /opt/invenio/var/instance/data || echo "Warning: Failed to chown data directory in web-ui container. This might be okay if permissions are already correct."

# 3. Destroy Existing Search Indices (for clean slate)
echo "--- Destroying existing search indices... ---"
pipenv run invenio index destroy --force --yes-i-know

# 4. Initialize Search Indices (Create Structure)
echo "--- Initializing search indices... ---"
pipenv run invenio index init

# 5. Initialize and Purge Indexing Queue
echo "--- Initializing and purging indexing queue... ---"
pipenv run invenio index queue init purge

# 6. Run Indexer (Populate Search Indices)
echo "--- Running indexer to populate search indices... ---"
pipenv run invenio index run

echo "==== Environment Reset Complete! ====" 
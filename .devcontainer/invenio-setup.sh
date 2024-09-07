#!/bin/bash

# Install invenio-cli using pip
pip install invenio-cli

# Run the invenio-cli install command
invenio-cli install

# Run the invenio-cli services setup command
invenio-cli services setup --no-demo-data

# Install the Flask-Debugtoolbar
pipenv run pip install Flask-Debugtoolbar
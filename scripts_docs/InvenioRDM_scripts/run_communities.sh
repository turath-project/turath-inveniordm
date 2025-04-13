#!/bin/bash

# Script to run the communities scripts

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." &> /dev/null && pwd )"
COMMUNITIES_DIR="$SCRIPT_DIR/communities"

# Set up environment
export PYTHONPATH="$PROJECT_ROOT:$COMMUNITIES_DIR:$PYTHONPATH"
export FLASK_APP=invenio_app.factory:create_app

# Check command
if [ "$1" == "list" ]; then
    echo "Running list_communities.py..."
    cd "$COMMUNITIES_DIR"
    python list_communities.py
elif [ "$1" == "setup" ]; then
    echo "Running setup_chronicles.py..."
    cd "$COMMUNITIES_DIR"
    python setup_chronicles.py
elif [ "$1" == "test" ]; then
    echo "Running test_chronicles_grouping.py..."
    cd "$COMMUNITIES_DIR"
    python test_chronicles_grouping.py
else
    echo "Unknown command: $1"
    echo "Usage: $0 [list|setup|test]"
    exit 1
fi 
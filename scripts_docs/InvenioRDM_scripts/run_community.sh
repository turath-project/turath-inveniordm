#!/bin/bash

# Script to run community scripts with the correct Python path

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." &> /dev/null && pwd )"

# Set up Python path
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
export FLASK_APP=invenio_app.factory:create_app

# Check which script to run
if [ "$1" == "list" ]; then
    echo "Running list_communities.py..."
    SCRIPT="list_communities.py"
elif [ "$1" == "setup" ]; then
    echo "Running setup_chronicles.py..."
    SCRIPT="setup_chronicles.py"
elif [ "$1" == "test" ]; then
    echo "Running test_chronicles_grouping.py..."
    SCRIPT="test_chronicles_grouping.py"
else
    echo "Unknown command: $1"
    echo "Usage: $0 [list|setup|test]"
    exit 1
fi

# Execute the script
cd "$PROJECT_ROOT"
python "$SCRIPT_DIR/communities/$SCRIPT" 
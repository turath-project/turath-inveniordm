#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." &> /dev/null && pwd )"

# Add the project root to the Python path
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
export FLASK_APP=invenio_app.factory:create_app

# Run the community script
SCRIPT_NAME=$1
shift

# Check if script exists
if [ ! -f "$SCRIPT_DIR/communities/$SCRIPT_NAME" ]; then
  echo "Error: Script $SCRIPT_NAME not found in $SCRIPT_DIR/communities"
  exit 1
fi

# Execute the script
cd "$PROJECT_ROOT"
python "$SCRIPT_DIR/communities/$SCRIPT_NAME" "$@" 
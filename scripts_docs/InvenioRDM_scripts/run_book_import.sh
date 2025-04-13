#!/bin/bash

# Script to run book importer with the correct Python path

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." &> /dev/null && pwd )"

# Set up environment
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
export FLASK_APP=invenio_app.factory:create_app

# Default values
BOOK_PATH=""
TOKEN=""
TOKEN_SOURCE=""
USERNAME=""
PASSWORD=""
DRY_RUN=0
VERBOSE=0

# Parse command line options
while [[ $# -gt 0 ]]; do
  case $1 in
    --book)
      BOOK_PATH="$2"
      shift 2
      ;;
    --token)
      TOKEN="$2"
      shift 2
      ;;
    --token-file)
      TOKEN_SOURCE="$2"
      shift 2
      ;;
    --username)
      USERNAME="$2"
      shift 2
      ;;
    --password)
      PASSWORD="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --verbose)
      VERBOSE=1
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Check if book path is provided
if [ -z "$BOOK_PATH" ]; then
  echo "Error: Book path not provided"
  echo "Usage: $0 --book <path_to_book_directory> [--token <api_token> | --username <username> --password <password>] [--token-file <token_file_path>] [--dry-run] [--verbose]"
  exit 1
fi

# Check if book path exists
if [ ! -d "$BOOK_PATH" ]; then
  echo "Error: Book directory not found: $BOOK_PATH"
  exit 1
fi

# Get token from file if specified
if [ -n "$TOKEN_SOURCE" ]; then
  if [ -f "$TOKEN_SOURCE" ]; then
    TOKEN=$(cat "$TOKEN_SOURCE")
  else
    echo "Error: Token file not found: $TOKEN_SOURCE"
    exit 1
  fi
fi

# Check authentication method
if [ -n "$TOKEN" ]; then
  AUTH_METHOD="token"
elif [ -n "$USERNAME" ] && [ -n "$PASSWORD" ]; then
  AUTH_METHOD="basic"
else
  # If no auth provided, prompt user for credentials
  echo "No authentication provided. Please choose an authentication method:"
  echo "1) API Token"
  echo "2) Username and Password"
  read -p "Enter choice (1 or 2): " AUTH_CHOICE
  
  if [ "$AUTH_CHOICE" = "1" ]; then
    read -p "Enter API token: " TOKEN
    AUTH_METHOD="token"
  elif [ "$AUTH_CHOICE" = "2" ]; then
    read -p "Enter username: " USERNAME
    read -s -p "Enter password: " PASSWORD
    echo # Add a newline after password input
    AUTH_METHOD="basic"
  else
    echo "Invalid choice. Exiting."
    exit 1
  fi
fi

# Build command arguments
ARGS=""

if [ "$AUTH_METHOD" = "token" ]; then
  ARGS="$ARGS --token $TOKEN"
elif [ "$AUTH_METHOD" = "basic" ]; then
  ARGS="$ARGS --username $USERNAME --password $PASSWORD"
fi

if [ "$DRY_RUN" -eq 1 ]; then
  ARGS="$ARGS --dry-run"
fi

if [ "$VERBOSE" -eq 1 ]; then
  ARGS="$ARGS --verbose"
fi

# Run the book import command
echo "Importing book from $BOOK_PATH"
cd "$PROJECT_ROOT"
python "$SCRIPT_DIR/book_importer.py" "$BOOK_PATH" $ARGS 
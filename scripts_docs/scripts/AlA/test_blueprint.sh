#!/bin/bash

# Set record ID and filename
RECORD_ID=212
FILENAME=history00871.pdf
BASE_URL="https://127.0.0.1:5000/api/iiif"

# Test direct PDF manifest endpoint
echo "Testing direct PDF manifest endpoint..."
curl -k "$BASE_URL/pdf/$RECORD_ID/$FILENAME" | python -m json.tool

echo -e "\n\n"
sleep 1

# Test debug endpoint
echo "Testing debug endpoint..."
curl -k "$BASE_URL/debug/$RECORD_ID/$FILENAME" | python -m json.tool

echo -e "\n\nAll tests completed." 
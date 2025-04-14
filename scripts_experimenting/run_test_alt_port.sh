#!/bin/bash
# Test IIIF service connectivity with InvenioRDM using an alternative port

# Use port 9443 instead of 8443
HTTPS_PORT=9443

# Make scripts executable
chmod +x iiif_test_server.py upload_manifest.py

# Start the test server with custom port
echo "Starting IIIF test server on port $HTTPS_PORT..."
python ./iiif_test_server.py --port $HTTPS_PORT &
SERVER_PID=$!

# Wait for server to start
sleep 2

# Test server connection
echo "Testing server connection..."
if ! curl --insecure https://localhost:$HTTPS_PORT/ >/dev/null 2>&1; then
    echo "Error: Could not connect to the test server."
    kill $SERVER_PID
    exit 1
fi

echo "IIIF test server is running. Visit https://localhost:$HTTPS_PORT/ in your browser."
echo "Accept the security certificate warning when prompted."
echo ""
echo "To upload the manifest to InvenioRDM, use this command:"
echo "./upload_manifest.py --manifest-file simplified_manifest.json --token YOUR_TOKEN"
echo ""
echo "Remember to update the manifest URLs to use port $HTTPS_PORT instead of 8443."
echo ""
echo "Press Ctrl+C to stop the server when done."

# Wait for Ctrl+C
trap "echo 'Stopping server...'; kill $SERVER_PID; exit 0" INT
while true; do
    sleep 1
done 
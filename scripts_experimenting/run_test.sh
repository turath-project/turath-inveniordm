#!/bin/bash
# Test IIIF service connectivity with InvenioRDM

# Make scripts executable
chmod +x iiif_test_server.py upload_manifest.py

# More reliable port check
PORT_CHECK=$(nc -z localhost 8443 2>/dev/null; echo $?)
if [ "$PORT_CHECK" -eq 0 ]; then
    echo "A service is already running on port 8443. Please stop it first."
    echo "You can find and stop it with: lsof -i :8443 and then kill <PID>"
    exit 1
fi

# Start the test server
echo "Starting IIIF test server..."
./iiif_test_server.py &
SERVER_PID=$!

# Wait for server to start
sleep 2

# Test server connection
echo "Testing server connection..."
if ! curl --insecure https://localhost:8443/ >/dev/null 2>&1; then
    echo "Error: Could not connect to the test server."
    kill $SERVER_PID
    exit 1
fi

echo "IIIF test server is running. Visit https://localhost:8443/ in your browser."
echo "Accept the security certificate warning when prompted."
echo ""
echo "To upload the manifest to InvenioRDM, use this command:"
echo "./upload_manifest.py --manifest-file simplified_manifest.json --token YOUR_TOKEN"
echo ""
echo "Press Ctrl+C to stop the server when done."

# Wait for Ctrl+C
trap "echo 'Stopping server...'; kill $SERVER_PID; exit 0" INT
while true; do
    sleep 1
done 
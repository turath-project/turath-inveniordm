#!/bin/bash

# Kill any existing processes on port 9443
PID=$(lsof -ti:9443)
if [ ! -z "$PID" ]; then
  echo "Killing process $PID using port 9443"
  kill $PID
fi

# Kill any existing HTTP server
PID=$(lsof -ti:8000)
if [ ! -z "$PID" ]; then
  echo "Killing process $PID using port 8000"
  kill $PID
fi

# Start the IIIF test server in the background with HTTP mode
echo "Starting IIIF test server on port 9443 (HTTP mode)..."
python3 scripts_experimenting/iiif_test_server.py --http --port 9443 &
SERVER_PID=$!

# Wait for server to start
sleep 2

# Determine the correct command to open URLs based on the OS
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  OPEN_CMD="open"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  # Linux
  OPEN_CMD="xdg-open"
elif [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "win32" ]]; then
  # Windows
  OPEN_CMD="start"
else
  echo "Unsupported OS: $OSTYPE"
  echo "Please open the test viewer manually at: http://localhost:8000/scripts_experimenting/test_viewer.html"
  OPEN_CMD=""
fi

# Start a simple HTTP server for the test viewer
echo "Starting HTTP server for the test viewer on port 8000..."
cd $(dirname "$0")/..
python3 -m http.server 8000 &
HTTP_PID=$!

# Wait for the HTTP server to start
sleep 2

# Open the test viewer in the browser
if [ ! -z "$OPEN_CMD" ]; then
  echo "Opening test viewer in browser..."
  $OPEN_CMD "http://localhost:8000/scripts_experimenting/test_viewer.html"
fi

echo ""
echo "IIIF test server running at: http://localhost:9443/"
echo "Test viewer available at: http://localhost:8000/scripts_experimenting/test_viewer.html"
echo ""
echo "Press Ctrl+C to stop the servers"

# Wait for user to press Ctrl+C
trap "echo 'Stopping servers...'; kill $SERVER_PID $HTTP_PID 2>/dev/null; exit" INT
wait 
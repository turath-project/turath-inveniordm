#!/bin/bash

# Create directory if it doesn't exist
mkdir -p static/js/mirador3-dist

# Download Mirador
curl -L https://github.com/ProjectMirador/mirador/releases/download/v3.4.0/mirador.min.js -o static/js/mirador3-dist/mirador.min.js

echo "Mirador viewer assets downloaded successfully!" 
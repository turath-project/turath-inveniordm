#!/bin/bash

# Exit on error
set -e

echo "Running post-installation setup for Turath InvenioRDM..."

# 1. No need to copy Makefile.local as it's now in the root as 'Makefile'
echo "Setting up management files..."
# Make script files executable
chmod +x app_data/scripts/*.sh

# 2. Setup admin user
echo "Setting up admin user..."
./app_data/scripts/setup-admin.sh

# 3. Install site package with configurations
echo "Installing site package..."
cd site && pip install -e .
cd ..

# 4. Download Mirador viewer
echo "Downloading Mirador viewer..."
./app_data/scripts/download-mirador.sh

# 5. Setup IIIF test environment
echo "Setting up IIIF test environment..."
mkdir -p test-images
mkdir -p var/iiif-storage

echo "Post-installation complete! Use 'make help' to see available commands" 
#!/bin/bash
# Simple script to convert images to PTIF format for IIPServer
# Requires vips to be installed: apt-get install -y libvips-tools

set -e

# Default image directory
IMAGE_DIR="./data/images"

# Check if vips is installed
if ! command -v vips &> /dev/null; then
    echo "Error: vips is not installed. Please install with 'apt-get install -y libvips-tools' or 'brew install vips'"
    exit 1
fi

# Ensure the directory structure exists
mkdir -p "$IMAGE_DIR/public" "$IMAGE_DIR/private"

# Process all PNG, JPG, and TIF files
echo "Searching for image files in $IMAGE_DIR..."
find "$IMAGE_DIR" -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.tif" -o -name "*.tiff" \) | while read img; do
    # Generate output filename with .ptif extension
    ptif_file="${img%.*}.ptif"
    
    # Skip if already converted
    if [ -f "$ptif_file" ]; then
        echo "Skipping already converted: $img"
        continue
    fi
    
    echo "Converting $img to $ptif_file"
    vips tiffsave "$img" "$ptif_file" --tile --pyramid || echo "Failed to convert $img"
done

echo "Conversion complete"
echo "Make sure docker volume mounting is working correctly with:"
echo "  docker-compose exec iipserver ls -la /images/public/"
echo ""
echo "Test a PTIF file with:"
echo "  curl \"http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/path/to/image.ptif/info.json\"" 
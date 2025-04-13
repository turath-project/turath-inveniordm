#!/bin/bash
# PTIF Converter entrypoint
# Watches for image files and converts them to PTIF format

set -e

echo "Starting PTIF Converter service"
echo "================================"
echo "This container watches for image files and converts them to PTIF format"
echo "It's a substitute for the Zenodo worker service during development"
echo ""

# Ensure directories exist
mkdir -p /images/public /images/private

# Function to convert image to PTIF
convert_to_ptif() {
    local img="$1"
    local ptif_file="${img%.*}.ptif"
    
    # Skip if already converted
    if [ -f "$ptif_file" ]; then
        echo "$(date): Skipping already converted: $img"
        return 0
    fi
    
    echo "$(date): Converting $img to $ptif_file"
    if vips tiffsave "$img" "$ptif_file" --tile --pyramid; then
        echo "$(date): ✓ Successfully converted $img to $ptif_file"
        return 0
    else
        echo "$(date): ✗ Failed to convert $img"
        return 1
    fi
}

# Initial conversion of existing files
echo "Scanning for existing image files..."
find /images -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.tif" -o -name "*.tiff" \) | while read img; do
    convert_to_ptif "$img"
done

# Main loop to watch for new files
echo "$(date): Watching for new image files..."
while true; do
    # Check public directory
    find /images/public -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.tif" -o -name "*.tiff" \) -not -path "*.ptif" | while read img; do
        if [ ! -f "${img%.*}.ptif" ]; then
            convert_to_ptif "$img"
        fi
    done
    
    # Check private directories (record-specific)
    find /images/private -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.tif" -o -name "*.tiff" \) -not -path "*.ptif" | while read img; do
        if [ ! -f "${img%.*}.ptif" ]; then
            convert_to_ptif "$img"
            
            # For record directories, also create a symlink to public
            # This helps with testing, but in a real system this would
            # respect access controls
            dir=$(dirname "$img")
            record_id=$(basename "$dir")
            mkdir -p "/images/public/$record_id"
            ptif_file="${img%.*}.ptif"
            ln -sf "$ptif_file" "/images/public/$record_id/$(basename "$ptif_file")" 2>/dev/null || true
        fi
    done
    
    # Wait before checking again
    sleep 5
done 
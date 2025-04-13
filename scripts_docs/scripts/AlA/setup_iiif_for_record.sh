#!/bin/bash
# Setup IIIF for a record - automates PTIF conversion and IIPServer setup

if [ $# -lt 1 ]; then
    echo "Usage: $0 RECORD_ID [FILE_NAME]"
    echo "  RECORD_ID: Record ID to process"
    echo "  FILE_NAME: Optional specific file to process (otherwise all image files)"
    exit 1
fi

RECORD_ID=$1
SPECIFIC_FILE=$2

# 1. Check record and get files
echo "Checking record $RECORD_ID..."
python check_record.py $RECORD_ID

# 2. Create necessary directories
echo "Creating directories..."
docker-compose exec iipserver mkdir -p /images/public

# 3. Download and convert files
if [ -n "$SPECIFIC_FILE" ]; then
    echo "Processing specific file: $SPECIFIC_FILE"
    python get_file.py $RECORD_ID "$SPECIFIC_FILE" .
    python convert_to_ptif.py "$SPECIFIC_FILE" $RECORD_ID
else
    # Extract file information using a temporary file to avoid parsing issues
    python check_record.py $RECORD_ID > /tmp/record_info.txt
    
    # Use awk to extract filenames that match image extensions
    # Format in check_record.py output: "- filename.ext (size bytes)"
    cat /tmp/record_info.txt | awk '/^- .*\.(jpg|jpeg|tif|tiff|png) / {
        # Extract just the filename part between "- " and " ("
        filename = $0
        gsub(/^- /, "", filename)
        gsub(/ \(.*$/, "", filename)
        print filename
    }' > /tmp/image_files.txt
    
    # Process each file in the clean list
    while IFS= read -r FILE; do
        echo "Processing file: $FILE"
        python get_file.py $RECORD_ID "$FILE" .
        python convert_to_ptif.py "$FILE" $RECORD_ID
    done < /tmp/image_files.txt
    
    # Clean up temp files
    rm -f /tmp/record_info.txt /tmp/image_files.txt
fi

# 4. Verify IIIF manifest
echo "Verifying IIIF manifest..."
curl -k -s "https://127.0.0.1:5000/api/iiif/record:$RECORD_ID/manifest" | grep -q "sequences"
if [ $? -eq 0 ]; then
    echo "✅ IIIF manifest is accessible"
else
    echo "❌ Could not verify IIIF manifest"
fi

echo "Setup complete. You can view the manifest at: https://127.0.0.1:5000/api/iiif/record:$RECORD_ID/manifest" 
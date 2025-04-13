# Simplified Testing Guide for IIIF Components in Zenodo-RDM

This guide provides a simplified approach to testing the IIIF components in Zenodo-RDM, focusing on basic availability tests that don't require all components to be perfectly configured or available.

## Understanding the Testing Challenges

Testing the IIIF components in Zenodo-RDM presents several challenges:

1. **Circular Dependencies**: 
   - To test IIIF manifests, we need records with PTIF files
   - To create PTIF files, we need the full application stack running
   - To verify manifests, we need authentication credentials

2. **Component Separation**:
   - Different components (IIPServer, API server, worker) need to be tested separately
   - Some components rely on others to function properly

## Step 1: Basic IIPServer Availability Test

The simplest test is to verify that the IIPServer is running and accepting connections. This doesn't require PTIF files or authentication.

```bash
# From the project directory
cd site
source ../.venv/bin/activate
export IIPSERVER_URL="http://localhost:8080"
python tests/iiif/test_simple_iipserver.py
```

This test will:
- Check if the IIPServer is running
- Verify the FastCGI endpoint exists
- Provide a summary of findings and recommendations

## Step 2: Manual Web Interface Testing

If you need to test the full IIIF functionality, the easiest approach is to use the web interface:

1. Start the full application stack:
   ```bash
   docker-compose -f docker-compose.full.yml up -d
   ```

2. Create a test user account through the web interface (http://localhost:5000/signup)

3. Upload test images through the web interface:
   - Log in with your test account
   - Create a new record
   - Upload image files (JPG, PNG, TIFF)
   - Submit the record

4. Check the worker logs to monitor PTIF conversion:
   ```bash
   docker-compose logs -f worker
   ```

5. Once processing is complete, view the images in the Mirador viewer through the web interface

## Step 3: Authentication for API Testing

To test the API endpoints, you need authentication:

1. Log in to the web interface
2. Go to your user profile settings
3. Create an API token
4. Use the token in API tests:

```bash
export ZENODO_BASE_URL="http://localhost:5000"
export TEST_RECORD_ID="[your record id]"
export AUTH_TOKEN="[your token]"
python tests/iiif/test_authenticated_manifest.py
```

## Simple Diagnostic Checks

When things aren't working, try these diagnostic checks:

### 1. Check Container Status
```bash
docker-compose ps
```

### 2. Check IIPServer Logs
```bash
docker-compose logs iipserver
```

### 3. Check Worker Logs
```bash
docker-compose logs worker | grep "tile"
```

### 4. Verify PTIF File Creation
```bash
docker-compose exec worker ls -la /opt/invenio/var/instance/images/
```

### 5. Test Direct Image Access
```bash
# Replace [record_id] and [filename] with your values
curl -v -H "Authorization: Bearer [your_token]" \
  "http://localhost:5000/api/iiif/record:[record_id]:[filename]/info.json"
```

## Alternative Testing Approach

If you're unable to set up the full testing environment, you can focus on documenting the IIIF components and their interactions instead. This documentation will be valuable for:

1. Understanding the system architecture
2. Planning future development work
3. Troubleshooting issues

The tests we've created in this project serve as a starting point for this documentation, providing insights into how the IIIF manifest generation process works and how the different components interact. 
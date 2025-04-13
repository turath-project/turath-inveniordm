# Manual IIIF Testing Guide

This guide provides step-by-step instructions for manually testing the complete IIIF workflow in Zenodo-RDM, including creating test records, obtaining authentication tokens, and validating manifests.

## Prerequisites

Our automated tests have confirmed:
- ✅ The IIPServer is running
- ✅ The web server is running
- ✅ The FastCGI endpoint is available

## Step 1: Create a Test Record with Images

1. Log in to your Zenodo-RDM instance at http://localhost:5000
2. Create a new record:
   - Click "Upload" or "New Upload" on the homepage
   - Fill in the basic metadata (title, description, etc.)
   - Upload at least 2-3 image files (preferably JPG or PNG)
   - Set appropriate access rights
   - Publish the record (or save as draft if you prefer to test with drafts)
3. Note the record ID from the URL: `http://localhost:5000/records/<record-id>`

## Step 2: Obtain an Authentication Token

1. Go to your user profile
2. Navigate to "Applications" or "API Tokens"
3. Create a new token with appropriate scopes:
   - Ensure it has at least read access to records
   - Copy the token when it's displayed (you won't be able to see it again)

## Step 3: Run the Authenticated Manifest Test

With your record ID and token, run the authenticated manifest test:

```bash
cd site
source ../.venv/bin/activate
RDM_TOKEN="your-token-here" RECORD_ID="your-record-id" python tests/iiif/test_authenticated_manifest.py
```

Example:
```bash
RDM_TOKEN="oPJ5jw9K8tx6SJoUibrJXZ3CJtE9yN3ZnS4wRhSZ" RECORD_ID="abcde-fghij" python tests/iiif/test_authenticated_manifest.py
```

## Step 4: Check for PTIF Conversion

If the manifest test fails with missing images, you may need to trigger or wait for the PTIF conversion:

1. Check the status of the file processing:
   ```bash
   docker-compose logs --tail=100 worker
   ```

2. Look for logs indicating PTIF conversion:
   ```
   Processing file for IIIF conversion...
   ```

3. Check if PTIF files exist in the IIPServer directory:
   ```bash
   docker-compose exec iipserver ls -la /images/private/<record-id>/
   ```

## Step 5: Test the Mirador Viewer

Once the manifest test passes:

1. Open your record in the browser: `http://localhost:5000/records/<record-id>`
2. Look for the IIIF button/icon in the record view
3. Click the button to open the Mirador viewer
4. Verify:
   - Images load correctly
   - You can navigate between multiple images
   - Zoom functionality works
   - The manifest information is displayed correctly

## Troubleshooting

### Authentication Issues
- Verify your token has the correct scopes
- Check that the token is valid and not expired
- Ensure you're properly formatting the Authorization header

### Missing PTIF Files
- The asynchronous conversion may still be in progress
- Check worker logs for errors: `docker-compose logs worker`
- Verify the file types are supported (JPG, PNG, TIFF)

### Mirador Viewer Issues
- Check browser console for JavaScript errors
- Verify that the manifest URL is correctly formed
- Ensure the record has public or appropriate access rights

## Conclusion

After completing these steps, you will have validated the complete IIIF workflow:
1. Record creation and image upload
2. PTIF conversion process
3. Manifest generation
4. Image serving via IIPServer
5. Integration with the Mirador viewer

This end-to-end testing confirms that all components of the IIIF implementation are working together correctly. 
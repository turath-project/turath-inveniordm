# IIIF Service Connectivity Test

This directory contains scripts for testing if InvenioRDM can access external IIIF services.

## What This Tests

When using IIIF in InvenioRDM, the Mirador viewer may need to access external IIIF services like:
- Search services
- Annotation services 
- Image services

These services are referenced in the IIIF manifest by URL. Since InvenioRDM uses HTTPS, 
we need to ensure any referenced services also use HTTPS to avoid mixed content issues.

## Files Included

- `iiif_test_server.py` - HTTPS server that simulates IIIF services
- `simplified_manifest.json` - IIIF manifest that references our test server
- `upload_manifest.py` - Script to upload the manifest to InvenioRDM
- `run_test.sh` - Helper script to run the test

## Running the Test

### Quick Start

For a quick test, just run:

```bash
cd scripts_experimenting
./run_test.sh
```

This will:
1. Start the IIIF test server on port 8443
2. Test the connection 
3. Display instructions for uploading the manifest

### Manual Testing

#### Step 1: Start the IIIF Test Server

```bash
cd scripts_experimenting
python iiif_test_server.py
```

#### Step 2: Accept the Certificate Warning

Open https://localhost:8443/ in your browser and accept the security warning for the self-signed certificate.

#### Step 3: Upload the Manifest to InvenioRDM

You can use the upload script:

```bash
python upload_manifest.py --manifest-file simplified_manifest.json --token YOUR_API_TOKEN
```

Or manually:
1. Log in to InvenioRDM at https://127.0.0.1:5000
2. Create a new record
3. Upload `simplified_manifest.json` as a file
4. Set the IIIF manifest URL to: https://localhost:8443/simplified_manifest
5. Publish the record

#### Step 4: Test in Mirador

1. View the record in InvenioRDM
2. Mirador should load the manifest and attempt to access the services
3. Check the browser console (F12) for any CORS or connection errors

## Command Line Options

### IIIF Test Server

```
python iiif_test_server.py [--http]
```

Options:
- `--http` - Run in HTTP mode (on port 8090) instead of HTTPS (not recommended)

### Upload Script

```
python upload_manifest.py --manifest-file FILE [OPTIONS]
```

Required:
- `--manifest-file FILE` - Path to the manifest file

Optional:
- `--token TOKEN` - API token for authentication
- `--api-url URL` - InvenioRDM API URL (default: https://127.0.0.1:5000/api)
- `--title TITLE` - Custom title for the record
- `--description DESC` - Custom description for the record
- `--publish` - Publish the record after uploading
- `--no-verify-ssl` - Don't verify SSL certificates

## Troubleshooting

- **Certificate warnings**: Since we're using a self-signed certificate, you need to accept the security warning in your browser. Visit https://localhost:8443/ directly first.
- **Mixed content errors**: Check browser console (F12) for any mixed content warnings.
- **CORS issues**: The test server sets CORS headers to allow all origins, but check the console for any CORS-related errors.
- **Network connectivity**: Ensure your browser can connect to localhost:8443 and that the InvenioRDM container can reach this service.

## Next Steps

Once this basic connectivity test works, you can:

1. Set up proper IIIF services using this same approach
2. Modify your manifest generation script to use HTTPS URLs for all services
3. Configure a reverse proxy if needed for production use 
# IIIF Troubleshooting Guide

This comprehensive troubleshooting guide addresses common issues, error messages, and solutions encountered during IIIF integration with Zenodo-RDM.

## Table of Contents

1. [Diagnosing Problems](#diagnosing-problems)
2. [Common Error Messages](#common-error-messages)
3. [Step-by-Step Troubleshooting](#step-by-step-troubleshooting)
4. [Advanced Debugging Techniques](#advanced-debugging-techniques)
5. [Known Issues and Workarounds](#known-issues-and-workarounds)

## Diagnosing Problems

### Diagnostic Flowchart

Follow this flowchart to identify and resolve common IIIF issues:

```
┌─────────────────┐
│ Start           │
└────────┬────────┘
         │
         ▼
┌────────────────────┐     ┌────────────────────┐
│ Can you access     │ No  │ Check Zenodo-RDM   │
│ Zenodo-RDM web UI?│────▶│ is running          │
└────────┬───────────┘     └────────────────────┘
         │ Yes
         ▼
┌────────────────────┐     ┌────────────────────┐
│ Can you access     │ No  │ Check record exists│
│ the record?        │────▶│ and permissions    │
└────────┬───────────┘     └────────────────────┘
         │ Yes
         ▼
┌────────────────────┐     ┌────────────────────┐
│ Can you download   │ No  │ Check file access  │
│ image files?       │────▶│ permissions        │
└────────┬───────────┘     └────────────────────┘
         │ Yes
         ▼
┌────────────────────┐     ┌────────────────────┐
│ Is IIPServer       │ No  │ Check IIPServer    │
│ running?           │────▶│ container status   │
└────────┬───────────┘     └────────────────────┘
         │ Yes
         ▼
┌────────────────────┐     ┌────────────────────┐
│ Are PTIF files     │ No  │ Run conversion     │
│ created?           │────▶│ scripts            │
└────────┬───────────┘     └────────────────────┘
         │ Yes
         ▼
┌────────────────────┐     ┌────────────────────┐
│ Can you access     │ No  │ Check file paths   │
│ IIIF info.json?    │────▶│ and IIPServer config│
└────────┬───────────┘     └────────────────────┘
         │ Yes
         ▼
┌────────────────────┐     ┌────────────────────┐
│ Can you access     │ No  │ Check IIIF URLs    │
│ IIIF thumbnails?   │────▶│ and file access    │
└────────┬───────────┘     └────────────────────┘
         │ Yes
         ▼
┌────────────────────┐     ┌────────────────────┐
│ Can you access the │ No  │ Use direct image   │
│ IIIF manifest?     │────▶│ access instead     │
└────────┬───────────┘     └────────────────────┘
         │ Yes
         ▼
┌────────────────────┐
│ IIIF is working!   │
└────────────────────┘
```

### Visual Indicators of Problems

| Problem Area | Visual Indicators | Possible Causes |
|--------------|-------------------|----------------|
| Image Display | Broken image icon | PTIF file missing or inaccessible |
| Image Display | Loads but no zoom | PTIF conversion failed or incorrect format |
| IIIF Manifest | Error message | Manifest endpoint issues |
| IIIF Manifest | Empty viewer | Manifest endpoint not returning canvases |
| Viewer | JavaScript errors | OpenSeadragon configuration issues |
| Thumbnails | Missing thumbnails | PTIF files not accessible via IIIF |

## Common Error Messages

### 1. "File not found" from IIPServer

```
"/images/public/private/202/page-001.ptif is neither a file nor part of an image sequence%"
```

**Cause**: The IIPServer cannot find the PTIF file at the expected location.

**Solutions**:
1. Check if the file exists in the correct location
   ```bash
   docker-compose exec iipserver ls -la /images/public/
   ```
2. Verify the file path matches the URL path
3. Ensure file permissions allow IIPServer to read the file
4. Check that the filename in the URL matches exactly (case-sensitive)

### 2. "Invalid 'Accept' header" in Manifest Endpoint

```
{
  "status": 406,
  "message": "Invalid 'Accept' header. Expected one of: application/ld+json"
}
```

**Cause**: The IIIF manifest endpoint expects a specific Accept header.

**Solutions**:
1. Try different Accept headers:
   ```bash
   curl -H "Accept: application/json" "https://127.0.0.1:5000/api/iiif/record/202/manifest" -k
   curl -H "Accept: application/ld+json" "https://127.0.0.1:5000/api/iiif/record/202/manifest" -k
   ```
2. Use direct IIIF image access instead of the manifest

### 3. "kdu_compress not found"

```
❌ Error: kdu_compress not found. Please install kakadu tools.
```

**Cause**: The Kakadu JPEG2000 compression tools are not installed or not in PATH.

**Solutions**:
1. Install Kakadu tools
2. Add Kakadu tools to PATH
3. Use a container with Kakadu pre-installed

### 4. Empty or Invalid PTIF Files

```
❌ Error: Output file page-001.ptif was not created or is empty.
```

**Cause**: The PTIF conversion failed or produced an invalid file.

**Solutions**:
1. Check input file format and validity
2. Verify kdu_compress command parameters
3. Try using different conversion parameters

### 5. IIPServer Container Issues

```
Error response from daemon: No such container: iipserver
```

**Cause**: The IIPServer container is not running.

**Solutions**:
1. Start the Docker container
   ```bash
   docker-compose up -d iipserver
   ```
2. Check container logs for errors
   ```bash
   docker-compose logs iipserver
   ```

### 6. CORS Errors in Browser

```
Access to fetch at 'http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/private_202_page-001.ptif/info.json' from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Cause**: The IIPServer is not configured to allow cross-origin requests.

**Solutions**:
1. Configure IIPServer with proper CORS headers
2. Use a proxy server that adds CORS headers
3. Use the provided `serve_viewer.py` which handles CORS issues

## Step-by-Step Troubleshooting

### Problem: PTIF Files Not Being Created

1. **Check Dependencies**:
   ```bash
   which kdu_compress
   kdu_compress -v
   ```

2. **Verify Input Files**:
   ```bash
   file data/images/private/202/page-001.tif
   ```

3. **Test Direct Conversion**:
   ```bash
   kdu_compress -i data/images/private/202/page-001.tif -o test.ptif -rate 2.4,1.48331273,.91673033,.56657224,.35016049,.21641118,.13374944,.08266171 -jp2_space sRGB
   ```

4. **Check Output File**:
   ```bash
   file test.ptif
   ls -la test.ptif
   ```

### Problem: Files Not Accessible in IIPServer

1. **Check IIPServer Configuration**:
   ```bash
   docker-compose exec iipserver env | grep -i filesystem
   ```

2. **Inspect IIPServer Directories**:
   ```bash
   docker-compose exec iipserver ls -la /images/
   docker-compose exec iipserver ls -la /images/public/
   ```

3. **Check File Permissions**:
   ```bash
   docker-compose exec iipserver ls -la /images/public/private_202_page-001.ptif
   ```

4. **Verify File Copy Process**:
   ```bash
   cp page-001.ptif /tmp/
   docker-compose exec iipserver cp /tmp/page-001.ptif /images/public/private_202_page-001.ptif
   ```

### Problem: IIIF URLs Not Working

1. **Test Basic IIPServer Access**:
   ```bash
   curl http://localhost:8080/fcgi-bin/iipsrv.fcgi
   ```

2. **Check IIIF Info Endpoint**:
   ```bash
   curl "http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/private_202_page-001.ptif/info.json"
   ```

3. **Verify Image Access**:
   ```bash
   curl "http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/private_202_page-001.ptif/full/200,/0/default.jpg" --output test.jpg
   file test.jpg
   ```

4. **Test Different IIIF Parameters**:
   ```bash
   curl "http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/private_202_page-001.ptif/0,0,100,100/full/0/default.jpg" --output region.jpg
   ```

### Problem: Custom Viewer Not Working

1. **Check Browser Console for Errors**
2. **Test IIIF URLs Directly in Browser**
3. **Verify OpenSeadragon Script Loading**
4. **Test with Different Images**

## Advanced Debugging Techniques

### 1. Debug IIPServer with Verbose Logging

```bash
# Check current logging level
docker-compose exec iipserver grep VERBOSITY /etc/iipsrv.conf

# Increase logging level
docker-compose exec iipserver bash -c "echo 'VERBOSITY=10' >> /etc/iipsrv.conf"

# Restart IIPServer
docker-compose restart iipserver

# View logs
docker-compose logs -f iipserver
```

### 2. Trace Network Requests

Use browser developer tools (F12) to:
1. Check Network tab for IIIF requests
2. Look for failing requests (red)
3. Examine response headers and bodies
4. Test requests directly using cURL

### 3. Debug PTIF Creation

```bash
# Run conversion with verbose output
kdu_compress -i input.tif -o output.ptif -rate 2.4,1.48331273,.91673033,.56657224,.35016049,.21641118,.13374944,.08266171 -jp2_space sRGB -quiet -record /tmp/conversion.log

# Check conversion log
cat /tmp/conversion.log
```

### 4. Use IIPServer Test Mode

```bash
# Test IIPServer with a simple IIIF request
curl "http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/test.tif/info.json"
```

## Known Issues and Workarounds

### Issue 1: Zenodo-RDM IIIF Manifest Endpoint Confusion

**Problem**: The IIIF manifest endpoint in Zenodo-RDM returns conflicting information about the expected Accept header.

**Workaround**: Use direct IIIF image access instead of the manifest endpoint.

```javascript
// Instead of loading a manifest
viewer.open("https://127.0.0.1:5000/iiif/202/manifest");

// Load individual images directly
viewer.open("http://localhost:8080/fcgi-bin/iipsrv.fcgi?IIIF=/private_202_page-001.ptif/info.json");
```

### Issue 2: PTIF Files in Wrong Location

**Problem**: IIPServer is looking in `/images/public` but files are placed in `/images/private/202/`.

**Workaround**: Use a naming convention that puts files directly in `/images/public`.

```python
# Instead of this path
target_path = f"/images/private/{record_id}/{filename}.ptif"

# Use this path
target_path = f"/images/public/private_{record_id}_{filename}.ptif"
```

### Issue 3: CORS Issues with IIPServer

**Problem**: IIPServer doesn't include CORS headers by default, causing issues with web viewers.

**Workaround**: Use a proxy server or the provided `serve_viewer.py` which adds CORS headers.

```python
# Add CORS headers in your server
self.send_header('Access-Control-Allow-Origin', '*')
self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
self.send_header('Access-Control-Allow-Headers', 'Content-Type')
```

### Issue 4: Failed IIIF Manifest Access Reporting

**Problem**: The `verify_iiif_manifest()` function reports success even when the manifest is inaccessible.

**Workaround**: Implement better error handling and check the HTTP status code.

```python
if response.status_code != 200:
    print(f"❌ IIIF manifest not accessible: HTTP {response.status_code}")
    return False
```

### Issue 5: Missing Worker for Automatic PTIF Conversion

**Problem**: Zenodo-RDM expects a worker process to automatically convert images to PTIF format, but this is not set up in our deployment.

**Workaround**: Use our manual conversion scripts until the worker process is properly configured.

```bash
# Batch convert all images in a record
python batch_convert.py 202
``` 
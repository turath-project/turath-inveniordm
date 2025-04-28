# IIIF and InvenioRDM Troubleshooting Cheatsheet

## Quick Reference for Common Errors

| Error Message | Likely Cause | Quick Fix |
|---------------|--------------|-----------|
| `Fetch API cannot load due to access control checks` | Missing CORS headers | Add proper CORS headers to your IIIF server responses |
| `Mixed Content: The page was loaded over HTTPS, but requested an insecure resource` | HTTP URLs in manifest | Convert all URLs in manifest to HTTPS |
| `net::ERR_CERT_AUTHORITY_INVALID` | Untrusted self-signed certificate | Manually accept the certificate in browser or use a proper SSL cert |
| `Failed to load resource: the server responded with a status of 404` | Incorrect URL in manifest OR Issue with Invenio file API resolution (see below) | Check manifest URLs. If checking API directly, ensure you query `/content` or file metadata, not sub-paths. |
| `SyntaxError: Unexpected token in JSON` | Invalid JSON in manifest | Validate your manifest JSON with a JSON validator |
| `IndentationError` (in Python script) | Incorrect Python indentation | Fix script indentation. Use linters/IDEs. |
| `WARNING - Invalid date format...` (in `upload_book.py`) | `metadata.json` date format mismatch | Correct date in `metadata.json` or adjust script validation logic. |
| `No HOCR files found` (in `upload_book.py`) | `--pdf-only` flag used | Remove `--pdf-only` or use `--skip-tiff` / `--skip-hocr` instead. |

## CORS Header Checklist

- [ ] `Access-Control-Allow-Origin: *` or specific origin
- [ ] `Access-Control-Allow-Methods: GET, OPTIONS, HEAD`
- [ ] `Access-Control-Allow-Headers: Content-Type, Origin, Authorization`
- [ ] `Access-Control-Allow-Credentials: true` (if needed)
- [ ] `Cross-Origin-Resource-Policy: cross-origin`

## Common IIIF Manifest Issues

1. Missing required fields in manifest:
   - `@context`
   - `@id`
   - `@type`
   - `label`
   - `sequences` with at least one canvas

2. Incorrect URL structure:
   - All URLs must be absolute
   - URLs must match the protocol (HTTP/HTTPS) of the requesting page
   - Canvas and image IDs must match

## Certificate Commands

```bash
# Generate self-signed certificate
openssl genrsa -out key.pem 2048
openssl req -new -x509 -key key.pem -out cert.pem -days 365 -subj "/CN=localhost"

# Run IIIF server with SSL
python scripts_experimenting/iiif_test_server.py

# Run InvenioRDM with SSL
invenio run --https --cert ./cert.pem --key ./key.pem
```

## Testing CORS and HTTP Status

```bash
# Test CORS headers
curl -H "Origin: https://localhost:5000" -I -k https://localhost:8443/manifest

# Test HTTP status code
curl -I -k https://localhost:8443/manifest
```

## InvenioRDM Configuration Check

Check your `invenio.cfg` file for:

```python
# IIIF viewer configuration
IIIF_VIEWER_ENABLED = True
IIIF_PREVIEW_TEMPLATE = "invenio_app_rdm/records/details/iiif.html"
IIIF_VIEWER_CONFIG = {
    "manifest_field": "custom.iiif_manifest",
    "viewer": "mirador",
    "options": {
        "showTitle": True,
        "allowFullscreen": True
    }
}
```

## Browser Debugging Tips

1. Open browser developer tools (F12 in most browsers)
2. Go to the Network tab
3. Filter for the problematic requests (e.g., filter by "manifest" or "info.json")
4. Check:
   - Status code (200, 404, etc.)
   - Response headers (look for CORS headers)
   - Response content (valid JSON?)

## Quick Fixes for CORS Issues

Add this Python snippet to your IIIF server:

```python
def do_OPTIONS(self):
    self.send_response(200)
    origin = self.headers.get('Origin')
    if origin:
        self.send_header('Access-Control-Allow-Origin', origin)
    else:
        self.send_header('Access-Control-Allow-Origin', '*')
    self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS, HEAD')
    self.send_header('Access-Control-Allow-Headers', 'Content-Type, Origin, Authorization')
    self.send_header('Access-Control-Max-Age', '3600')
    self.end_headers()
```

## Protocol Check

If your InvenioRDM is running on HTTPS, ensure:

1. Your IIIF server is also using HTTPS
2. All URLs in the manifest use HTTPS
3. All service URLs in the manifest use HTTPS
4. Any external resources linked in the manifest use HTTPS

## Manifest URL Quick Conversion

Search and replace in your manifest file:

```
Find: "http://localhost:9443/
Replace: "https://localhost:8443/
```

## Command Line HTTPS/CORS Testing

```bash
# Test if server is responding
curl -k https://localhost:8443/manifest

# Test CORS headers with specific origin
curl -H "Origin: https://localhost:5000" -I -k https://localhost:8443/manifest | grep -i "Access-Control"

# Check SSL certificate
openssl s_client -connect localhost:8443
```

## Script (`upload_book.py`) Specific Issues

**1. Problem: Script fails immediately (e.g., running `--help`) with `IndentationError`.**

*   **Cause:** Incorrect Python indentation.
*   **Solution:** Carefully check and correct Python indentation. Use a linter or IDE. Manual correction might be needed.
*   **Lesson:** Python syntax, especially indentation, is critical.

**2. Problem: Manifest `@id` and Canvas `@id` links give 404 errors when checked via API.**

*   **Cause:** Script uploaded manifest with temporary filename (`tmpXXX.json`) but internal links pointed to `manifest.json`.
*   **Solution:** Script was modified to save as `manifest.json` and upload using that key.
*   **Lesson:** Ensure consistency between internal IIIF `@id` links and the actual filename/key used for storing the manifest file.

**3. Problem: Log shows "no HOCR files found" even though they exist.**

*   **Cause:** Script run with `--pdf-only` flag.
*   **Solution:** Remove `--pdf-only`. Use `--skip-tiff` or `--skip-hocr` for specific exclusions.
*   **Lesson:** Understand script flags.

**4. Problem: Log shows `WARNING - Invalid date format 'YYYY-MM-DD', using current date.`**

*   **Cause:** `metadata.json` date format didn't match script validation.
*   **Solution:** Correct source data or adjust script validation.
*   **Lesson:** Ensure source metadata format matches script expectations.

## General Command/Tool Issues

**1. Problem: `run_terminal_cmd` tool fails with "missing required argument is_background".**

*   **Cause (Assistant Error):** Assistant forgot the mandatory `is_background` parameter.
*   **Solution:** Ensure all required parameters are provided.
*   **Lesson:** Double-check tool schema for required arguments.

**2. Problem: Automated code edits fail or produce incorrect results.**

*   **Cause:** Editing model struggles with complex changes (e.g., indentation).
*   **Solution:** Verify diff, retry, provide clearer instructions, or make manual changes.
*   **Lesson:** Review automated changes; be prepared for manual intervention.

## API Endpoint Testing Notes

*   **Manifest/Canvas `@id`:** Testing `.../files/manifest.json` or `.../manifest.json/canvas/pXXX` via `curl` against the Invenio API *file metadata endpoint* (`/api/records/.../files/...`) might return 404. This endpoint doesn't parse file content for sub-paths.
*   **Testing Manifest Content:** Fetch content via `.../files/manifest.json/content`.
*   **Testing Other Links:** Test direct links to services (Cantaloupe, Annotation/Search Proxy) or other files (`.../files/XXX.hocr`, `.../files/book.pdf`) directly. 
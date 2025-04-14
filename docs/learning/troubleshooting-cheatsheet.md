# IIIF and InvenioRDM Troubleshooting Cheatsheet

## Quick Reference for Common Errors

| Error Message | Likely Cause | Quick Fix |
|---------------|--------------|-----------|
| `Fetch API cannot load due to access control checks` | Missing CORS headers | Add proper CORS headers to your IIIF server responses |
| `Mixed Content: The page was loaded over HTTPS, but requested an insecure resource` | HTTP URLs in manifest | Convert all URLs in manifest to HTTPS |
| `net::ERR_CERT_AUTHORITY_INVALID` | Untrusted self-signed certificate | Manually accept the certificate in browser or use a proper SSL cert |
| `Failed to load resource: the server responded with a status of 404` | Incorrect URL in manifest | Check manifest URLs and ensure resources exist at the specified paths |
| `SyntaxError: Unexpected token in JSON` | Invalid JSON in manifest | Validate your manifest JSON with a JSON validator |

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
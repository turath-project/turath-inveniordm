# Configuring Cantaloupe with HTTPS for InvenioRDM

When using the IIIF manifest with InvenioRDM over HTTPS, you must also serve Cantaloupe over HTTPS to avoid mixed content errors. This document explains how to properly configure HTTPS for Cantaloupe.

## The Mixed Content Problem

If your InvenioRDM instance runs on HTTPS (e.g., `https://127.0.0.1:5000`), but your Cantaloupe image server runs on HTTP (e.g., `http://localhost:8182`), browsers will block the images due to mixed content security restrictions.

This will cause the IIIF viewer (Mirador) to fail to load images from the manifest.

## Solution 1: Configure HTTPS directly in Cantaloupe

### 1. Generate SSL certificates for Cantaloupe

```bash
# Create a directory for certificates
mkdir -p cantaloupe-ssl

# Generate a self-signed certificate for development
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout cantaloupe-ssl/cantaloupe.key \
  -out cantaloupe-ssl/cantaloupe.crt \
  -subj "/CN=localhost"
```

### 2. Update docker-compose.yml for Cantaloupe

```yaml
services:
  cantaloupe:
    image: edirom/cantaloupe
    ports:
      - "8182:8182"
    volumes:
      - ./test-images:/opt/cantaloupe/images
      - ./cantaloupe-ssl:/opt/cantaloupe/ssl
      - ./cantaloupe.properties:/etc/cantaloupe.properties
    environment:
      - CANTALOUPE_ENDPOINT_ADMIN_ENABLED=true
      - CANTALOUPE_ENDPOINT_ADMIN_SECRET=admin-secret
```

### 3. Create or update cantaloupe.properties

```properties
# Enable HTTPS
endpoint.http.port = 8182
endpoint.https.enabled = true
endpoint.https.port = 8183
endpoint.https.keystore.type = JKS
endpoint.https.keystore.password = changeit
endpoint.https.keystore.path = /opt/cantaloupe/ssl/cantaloupe.keystore
endpoint.https.key.password = changeit
```

### 4. Convert certificates to JKS format for Java

```bash
# Convert to PKCS12
openssl pkcs12 -export -in cantaloupe-ssl/cantaloupe.crt \
  -inkey cantaloupe-ssl/cantaloupe.key \
  -out cantaloupe-ssl/cantaloupe.p12 \
  -name cantaloupe \
  -password pass:changeit

# Convert to JKS
keytool -importkeystore -deststorepass changeit \
  -destkeystore cantaloupe-ssl/cantaloupe.keystore \
  -srckeystore cantaloupe-ssl/cantaloupe.p12 \
  -srcstoretype PKCS12 \
  -srcstorepass changeit
```

## Solution 2: Use a Reverse Proxy (Recommended for Production)

This approach is more flexible and easier to manage with proper SSL certificates.

### 1. Use Nginx as a reverse proxy

Create an nginx configuration file:

```nginx
server {
    listen 443 ssl;
    server_name cantaloupe.yourdomain.com;

    ssl_certificate /path/to/ssl/certificate.crt;
    ssl_certificate_key /path/to/ssl/private.key;

    location / {
        proxy_pass http://localhost:8182;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. Use Let's Encrypt for valid certificates

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d cantaloupe.yourdomain.com
```

### 3. Update IIIF manifest URLs

Ensure your manifest generator points to the HTTPS URL:

```python
CANTALOUPE_URL = "https://cantaloupe.yourdomain.com"
```

## Solution 3: Use Traefik for Docker (Recommended for Docker Environments)

### 1. Configure docker-compose.yml with Traefik

```yaml
version: '3'

services:
  traefik:
    image: traefik:v2.5
    command:
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.myresolver.acme.httpchallenge=true"
      - "--certificatesresolvers.myresolver.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.myresolver.acme.email=your-email@example.com"
      - "--certificatesresolvers.myresolver.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./letsencrypt:/letsencrypt"

  cantaloupe:
    image: edirom/cantaloupe
    volumes:
      - ./test-images:/opt/cantaloupe/images
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.cantaloupe.rule=Host(`cantaloupe.yourdomain.com`)"
      - "traefik.http.routers.cantaloupe.entrypoints=websecure"
      - "traefik.http.routers.cantaloupe.tls.certresolver=myresolver"
      - "traefik.http.services.cantaloupe.loadbalancer.server.port=8182"
```

## Testing Your HTTPS Setup

1. Verify direct HTTPS access:
   ```
   curl -k https://localhost:8183/iiif/3/test.jpg/info.json  # For direct Cantaloupe HTTPS
   # or
   curl https://cantaloupe.yourdomain.com/iiif/3/test.jpg/info.json  # For proxy
   ```

2. Update your copy_to_cantaloupe.py script to use the HTTPS URL:
   ```bash
   python scripts_experimenting/copy_to_cantaloupe.py --record-id test-123 \
     --file-path ./test.pdf \
     --cantaloupe-url https://cantaloupe.yourdomain.com/iiif/3 \
     --test
   ```

3. Test in a browser:
   - Open your InvenioRDM instance: `https://127.0.0.1:5000/records/{record-id}`
   - Verify the IIIF viewer loads the manifest and images correctly

## Important Security Notes

1. Self-signed certificates will cause browser warnings and may still be blocked
2. For production, always use valid certificates from a trusted CA
3. Let's Encrypt offers free certificates that are trusted by all browsers
4. The reverse proxy approach (Solutions 2 and 3) is recommended for production 
# Turath Book Upload System: Architecture, Workflow, and Troubleshooting Guide

This document provides a comprehensive guide to the system designed for uploading digitized books (PDFs with associated HOCR files) to the Turath InvenioRDM instance. It covers the chosen architecture, the workflow of the upload script, necessary configurations, troubleshooting steps for common issues, and commands used.

## 1. System Architecture & Workflow Overview

The current system utilizes a **static IIIF manifest generation** approach combined with supporting microservices for annotations and search.

**Core Components:**

1.  **InvenioRDM:** The central repository platform. It stores record metadata, the primary PDF file, HOCR files, and the generated IIIF manifest file. It runs on HTTPS on port 5000 locally.
2.  **`scripts/upload_book.py`:** A Python script responsible for orchestrating the entire upload process. It reads local book directories, prepares metadata, interacts with the InvenioRDM API, generates a static IIIF manifest, and copies files for other services.
3.  **Cantaloupe IIIF Image Server:** Runs in a Docker container (`turath-inveniordm-cantaloupe-1`) on port 8182. It serves images dynamically based on source files (PDFs in this case) via the IIIF Image API. It reads source files from a dedicated host directory (`./cantaloupe-files`) mounted into its container.
4.  **Annotation Service:** A Flask microservice (`turath-inveniordm-annotation-service-1`) running in Docker on internal port 5002. It reads HOCR files (from `./hocr_mount` on the host) and generates IIIF Annotation Lists for text content.
5.  **Search Service:** A Flask microservice (`turath-inveniordm-search-service-1`) running in Docker on internal port 5001. It provides IIIF Content Search API endpoints (search and autocomplete) based on HOCR files (also from `./hocr_mount`).
6.  **Nginx Frontend:** Runs in a Docker container (`turath-inveniordm-frontend-1`) on ports 80/443. It acts as a reverse proxy:
    *   Serves the main InvenioRDM UI/API (via `web-ui` uWSGI service).
    *   Proxies `/annotations/` requests to the Annotation Service.
    *   Proxies `/search/` and `/autocomplete/` requests to the Search Service.
    *   Handles SSL termination (using a self-signed certificate locally).
7.  **Docker Compose:** Manages the orchestration and networking of all the containerized services (`docker-compose.yml`, `docker-services.yml`, `docker-compose.override.yml`).
8.  **Pipenv:** Manages Python dependencies for the InvenioRDM backend and the upload script.
9.  **`.env` file:** Contains essential environment variables for InvenioRDM (database connection, secret key, API token, etc.).

**Simplified Workflow Diagram:**

```mermaid
graph LR
    A[User runs upload_book.py] --> B(Script reads book files);
    B --> C{Prepare Metadata};
    C --> D[Script POSTs to Invenio API /api/records];
    D -- Creates Draft Record --> E[InvenioRDM];
    E -- Returns Record ID --> D;
    D --> F[Script uploads PDF/HOCR/Manifest files];
    F --> E;
    D --> G[Script copies PDF to ./cantaloupe-files];
    D --> H[Script copies HOCR to ./hocr_mount];
    D --> I[Script POSTs to Invenio API /publish];
    I --> E;

    subgraph "IIIF Viewing"
        J[IIIF Viewer] -- Requests Manifest --> K(Nginx :443);
        K -- Serves Static Manifest File --> J;
        J -- Requests Image (e.g., /iiif/2/...) --> L(Cantaloupe :8182);
        L -- Reads PDF from ./cantaloupe-files --> L;
        L -- Serves Image --> J;
        J -- Requests Annotations (e.g., /annotations/...) --> K;
        K -- Proxies to Annotation Svc :5002 --> M(Annotation Service);
        M -- Reads HOCR from ./hocr_mount --> M;
        M -- Returns Annotation List --> K;
        K --> J;
        J -- Requests Search (e.g., /search/...) --> K;
        K -- Proxies to Search Svc :5001 --> N(Search Service);
        N -- Reads HOCR from ./hocr_mount --> N;
        N -- Returns Search Results --> K;
        K --> J;
    end

    style E fill:#f9f,stroke:#333,stroke-width:2px
    style L fill:#ccf,stroke:#333,stroke-width:2px
    style M fill:#cfc,stroke:#333,stroke-width:2px
    style N fill:#cfc,stroke:#333,stroke-width:2px
    style K fill:#fcf,stroke:#333,stroke-width:2px
```

**Explanation of Workflow:**

1.  The user executes `pipenv run python scripts/upload_book.py ...`.
2.  The script collects PDF, HOCR, and metadata files from the specified book directory.
3.  It prepares the InvenioRDM metadata structure.
4.  It makes an authenticated `POST` request to the InvenioRDM API (`https://127.0.0.1:5000/api/records`) to create a draft record.
5.  If successful, it receives the new `record_id`.
6.  It uploads the PDF, HOCR, and any other specified files to the draft record via the API.
7.  **Crucially**, it copies the primary PDF file to the `./cantaloupe-files` directory on the host, renaming it to `{record_id}_{original_pdf_filename}.pdf`. This makes it discoverable by Cantaloupe.
8.  **Also**, it copies the HOCR files to the `./hocr_mount/books/{book_id}/hocr/` directory on the host. This makes them accessible to the Annotation and Search services.
9.  It generates a static IIIF Presentation API manifest (`manifest.json`), including links that point to:
    *   The Cantaloupe server (`http://localhost:8182`) for images.
    *   The Nginx proxy (`https://localhost`) for annotations and search.
    *   The InvenioRDM file endpoints (`https://127.0.0.1:5000`) for HOCR `seeAlso` links and the related PDF download.
10. It uploads this generated `manifest.json` file to the record.
11. It makes a `POST` request to publish the draft record.
12. When a user accesses the record via a IIIF viewer, the viewer fetches the static manifest file. The viewer then uses the links within the manifest to request images from Cantaloupe and annotations/search results via the Nginx proxy, which directs them to the appropriate backend services.

## 2. Static vs. Dynamic Manifest Generation

*(This section summarizes the content from `docs/learning/manifest_generation_approaches.md`)*

*   **Static (Current Approach):** The `upload_book.py` script generates a complete `manifest.json` file during the upload.
    *   **Pros:** Full control over structure, works even if backend IIIF components are down at view time.
    *   **Cons:** Manifest doesn't auto-update, requires extra upload step, needs robust discovery mechanism (e.g., storing URL in record metadata - *this part needs implementation/verification*), relies on script having access to necessary info (like Cantaloupe dimensions, with fallbacks).
*   **Dynamic (`invenio-iiif`):** InvenioRDM generates the manifest on-the-fly when requested (e.g., via `/api/iiif/record:{record_id}/manifest`).
    *   **Pros:** Always reflects current record state, no extra file upload, standard discovery endpoint.
    *   **Cons:** Requires fully configured `invenio-iiif`, Cantaloupe, and potentially Celery running correctly at view time; less direct control over structure; customization involves Invenio signals/overrides.

We are currently using the **Static** approach primarily because it allows for a highly customized manifest structure needed for integrating HOCR annotations and search via separate microservices.

## 3. Configuration & File Modifications

Several files were modified or created during troubleshooting:

*   **`.env` (Created):**
    *   **Problem:** Missing file caused failures in DB connection and token generation as commands couldn't find `INVENIO_SQLALCHEMY_DATABASE_URI`.
    *   **Solution:** Created `.env` in the project root with standard Invenio variables (DB URI, Secret Key, Cache/MQ URLs) and user-provided ones (like `IIPSERVER_URL`, initial `RDM_API_TOKEN`). Ensured `INVENIO_SQLALCHEMY_DATABASE_URI` pointed to the correct PostgreSQL service (`postgresql://turath-inveniordm:turath-inveniordm@localhost/turath-inveniordm`).
*   **`Pipfile` / `Pipfile.lock` (Modified):**
    *   **Problem 1:** `ModuleNotFoundError: No module named 'PyPDF2'`.
    *   **Solution 1:** Ran `pipenv install PyPDF2` to add the dependency.
    *   **Problem 2:** Backend failed with `pkg_resources.ContextualVersionConflict` because `kombu` required `typing-extensions==4.12.2` but a newer version was installed.
    *   **Solution 2:** Ran `pipenv install "typing-extensions==4.12.2"` to pin the correct version. This updated `Pipfile.lock`. **Crucially, the backend server needed restarting after this.**
*   **`scripts/upload_book.py` (Modified):**
    *   **Problem 1:** Missing `process()` method.
    *   **Solution 1:** Restored the method definition from Git history.
    *   **Problem 2:** Needed to disable SSL verification for `requests` when talking to the local InvenioRDM HTTPS endpoint (using self-signed cert).
    *   **Solution 2:** Utilized the existing `--no-verify-ssl` command-line flag, which controls the `verify=self.verify_ssl` parameter passed to `requests`.
    *   **Problem 3:** Cantaloupe couldn't access PDFs stored within Invenio's internal volume structure.
    *   **Solution 3:** Added code to the `process()` method (after file uploads succeed) to copy the primary PDF to `./cantaloupe-files/{record_id}_{pdf_filename}.pdf`. Added `import os, shutil`.
*   **`scripts/create_admin.sh` (Modified):**
    *   **Problem:** Script failed due to invalid commands (`invenio roles list`) and non-idempotent actions (user/role creation).
    *   **Solution:** Removed invalid checks, used `|| echo ...` to handle existing roles gracefully, attempted user activation if creation failed, commented out `set -e`.
*   **`docker-compose.yml` (Modified):**
    *   **Problem:** Cantaloupe container couldn't access uploaded PDF files.
    *   **Solution:** Added a volume mount: `- ./cantaloupe-files:/opt/cantaloupe/images`. Changed environment variable `CANTALOUPE_FILESYSTEM_RESOLVER_LOOKUP_STRATEGY_PATH_PREFIX` to `/opt/cantaloupe/images`. Removed the previous incorrect attempt to mount the `data` volume directly.
*   **`services/annotation_service/app.py` (Modified):**
    *   **Problem:** Service looked for HOCR files named `pXXX.hocr` instead of `XXX.hocr`.
    *   **Solution:** Added `page_label = page_identifier.lstrip('p')` and used `page_label` to construct the filename.
*   **`docker/nginx/nginx.conf` (Verified):**
    *   **Problem:** Annotation/Search links returned 404.
    *   **Investigation:** Verified that `location /annotations/ { proxy_pass ...; }` and `location ~ ^/(search|autocomplete)/ { proxy_pass ...; }` blocks *were* present and correctly pointed to the respective service names and ports (`annotation-service:5002`, `search-service:5001`). The issue was downstream in the services themselves.

## 4. Common Commands (How-To)

*   **Start all services:**
    ```bash
    docker compose up -d
    ```
*   **Stop all services:**
    ```bash
    docker compose down
    ```
*   **Restart a specific service (e.g., Cantaloupe) after config change:**
    ```bash
    docker compose up -d --force-recreate --no-deps cantaloupe
    ```
*   **Rebuild and restart a service (e.g., Annotation Service) after code change:**
    ```bash
    docker compose up -d --build --force-recreate --no-deps annotation-service
    ```
*   **View logs for a specific service:**
    ```bash
    docker logs turath-inveniordm-cantaloupe-1
    docker logs turath-inveniordm-annotation-service-1
    # (Check 'docker ps' for exact container names)
    ```
*   **Install/Update Python dependencies:**
    ```bash
    pipenv install <package_name>
    pipenv install "<package_name>==<version>" # Pin version
    pipenv update
    ```
*   **Initialize/Reset Database Schema:**
    ```bash
    # Ensure .env file exists first!
    pipenv run invenio db init create
    ```
*   **Initialize Vocabularies/Fixtures (If needed - *Commands TBD*)**
    *   *Note: Standard commands like `invenio rdm-records vocabularies init` or `invenio fixtures init` did not work. The exact command for this project needs confirmation.*
*   **Create Admin User & Role:**
    ```bash
    bash scripts/create_admin.sh
    ```
*   **Generate API Token:**
    ```bash
    bash scripts/generate_api_token.sh
    # (Token is automatically saved to .env)
    ```
*   **Upload a Book:**
    ```bash
    pipenv run python scripts/upload_book.py \\
        --book-dir /path/to/your/book_folder \\
        --api-url https://127.0.0.1:5000/api \\
        --hocr-mount-point ./hocr_mount \\
        --verbose \\
        --no-verify-ssl \\
        # --skip-tiff # Optional
        # --skip-hocr # Optional
        # --no-publish # Optional
    ```
    *Note: Example book directories used during development (e.g., `history00871`, `history00872`) can be found in the `scripts_docs/books/` folder.*
*   **Delete a Record:**
    ```bash
    pipenv run python scripts/delete_records.py <record_id_1> <record_id_2> \
        --api-url https://127.0.0.1:5000/api \
        --no-verify-ssl
    ```
*   **Test API Endpoint (e.g., get user info):**
    ```bash
    # Replace <TOKEN> with token from .env or generate_api_token.sh output
    curl -k -H "Authorization: Bearer <TOKEN>" https://127.0.0.1:5000/api/users/me | cat
    ```
*   **Test Cantaloupe Image URL:**
    ```bash
    # Replace <IDENTIFIER> with {record_id}_{pdf_filename}.pdf
    curl -I http://localhost:8182/iiif/2/<IDENTIFIER>/full/full/0/default.jpg?page=1
    ```
*   **Test Annotation Service URL:**
    ```bash
    curl -k -I https://localhost/annotations/<book_id>/p001/line
    ```
*   **Test Search Service URL:**
    ```bash
    curl -k "https://localhost/search/<book_id>?q=test" | cat
    ```

## 5. Key Challenges & Error Patterns Encountered

*   **Database Initialization Failures:**
    *   **Cause:** Missing `.env` file preventing commands (`invenio db init create`, `invenio shell` used by scripts) from knowing the database URI. Also, potentially incomplete schema if `db init create` wasn't run successfully *after* `.env` was present.
    *   **Symptoms:** `ProgrammingError: relation "accounts_user" does not exist`, `ProgrammingError: relation "banners" does not exist`.
    *   **Solution:** Ensure `.env` exists and is correct, run `pipenv run invenio db init create`.
*   **Dependency Conflicts:**
    *   **Cause:** Incompatible versions of libraries installed (e.g., `typing-extensions` required by `kombu`).
    *   **Symptoms:** Backend server crashes on startup or request handling, `pkg_resources.ContextualVersionConflict` in backend logs, `Connection reset by peer` or `500 Internal Server Error` seen by clients (`upload_book.py`, `curl`).
    *   **Solution:** Identify the conflict from backend logs, pin the required version using `pipenv install "package==version"`, **restart the backend server**.
*   **HTTP vs. HTTPS Mismatch:**
    *   **Cause:** Trying to connect via HTTP to a server running on HTTPS, or vice-versa.
    *   **Symptoms:** Often `Connection refused` or SSL errors, but in our case, the HTTP attempt led to `Connection reset by peer` (likely because the backend crashed due to the dependency issue *before* protocol negotiation mattered), while the HTTPS attempt gave a `403 Permission Denied` initially (indicating the server *was* listening on HTTPS).
    *   **Solution:** Identify the correct protocol (HTTPS in this case) and use it in client URLs (`--api-url`).
*   **SSL Verification Failure:**
    *   **Cause:** Clients (like Python `requests`) refusing to connect to an HTTPS server using a self-signed certificate (common in local dev).
    *   **Symptoms:** `requests.exceptions.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate` in client script logs.
    *   **Solution:** Disable SSL verification in the client. For `upload_book.py`, use the `--no-verify-ssl` flag. For `curl`, use the `-k` flag.
*   **File Access Issues (Cantaloupe / Services):**
    *   **Cause:** Services running in separate Docker containers lacking access to files managed by another service (Invenio) or copied by a script. Incorrect volume mounts or file paths.
    *   **Symptoms:** Cantaloupe returning `404 Not Found` for image requests. Annotation/Search services returning `404 Not Found` or internal errors if they can't read HOCR files.
    *   **Solution (Cantaloupe):** Mount a host directory (`./cantaloupe-files`) accessible by Cantaloupe. Modify the upload script to copy the needed PDF (named `{record_id}_{filename}.pdf`) into this host directory. Configure Cantaloupe (`docker-compose.yml` environment variable `CANTALOUPE_FILESYSTEM_RESOLVER_LOOKUP_STRATEGY_PATH_PREFIX`) to look in the correct *container path* for this mount. Restart Cantaloupe container.
    *   **Solution (Annotation/Search):** Mount a host directory (`./hocr_mount`) accessible by these services (e.g., mounted to `/hocr_data`). Ensure the upload script copies HOCR files to the correct subdirectory structure (`./hocr_mount/books/{book_id}/hocr/`). Ensure the service code constructs the correct internal path (`/hocr_data/books/{book_id}/hocr/{page_label}.hocr`). Rebuild/restart service containers if code changes.
*   **Incorrect Script Logic:**
    *   **Cause:** Bugs or incorrect assumptions in custom scripts (`create_admin.sh`, `annotation_service/app.py`).
    *   **Symptoms:** Script errors (`command not found`, incorrect filename used), unexpected service behavior (404s).
    *   **Solution:** Debug the script/service code, check logs, correct the logic, rebuild/restart containers if necessary.

## 6. Mistakes Made & Lessons Learned

*   **Assuming Standard Commands:** Initially tried standard Invenio commands (`invenio rdm-records vocabularies init`, `invenio fixtures init`, `invenio roles list`) which were not applicable or had different syntax in this specific setup. *Lesson: Verify commands against the specific project version/customizations.*
*   **Overlooking `.env` Importance:** Didn't immediately check for the `.env` file when database errors occurred. *Lesson: `.env` is critical for database and service connectivity; check it early.*
*   **Incorrect `docker-compose` Volume Strategy:** Initially suggested mounting the Invenio `data` volume directly into Cantaloupe without accounting for Invenio's internal file structure vs. Cantaloupe's `FilesystemSource` expectation. *Lesson: Understand how each component expects to find files and configure mounts/copy steps accordingly.*
*   **Forgetting Service Restarts:** Didn't always explicitly mention the need to restart backend/docker services immediately after dependency or configuration changes. *Lesson: Always restart affected services after changing dependencies (`pipenv install`), configurations (`docker-compose.yml`, `.env`), or code.*
*   **Not Checking All Logs:** Focused initially on client script logs (`upload_book.py`) instead of immediately checking the relevant *backend* logs (Invenio, Cantaloupe, Annotation service) when connection/server errors occurred. *Lesson: Server-side logs are crucial for diagnosing backend failures indicated by client errors like "Connection reset".*
*   **Script Argument Errors:** Used incorrect flags (`--record-ids`) for `delete_records.py`. *Lesson: Double-check script `usage` or `--help` output.*

By following this guide and understanding the architecture and common pitfalls, future development and troubleshooting related to the book upload process should be significantly smoother. 
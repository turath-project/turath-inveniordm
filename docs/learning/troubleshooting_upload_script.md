## Troubleshooting `upload_book.py` for InvenioRDM

This document outlines the steps taken to diagnose and resolve issues preventing the successful execution of the `scripts/upload_book.py` script against a local InvenioRDM instance.

**Initial State:** The user wanted to run the upload script but encountered various errors.

### 1. Missing `process()` Method

*   **Symptom:** Script failed immediately with `AttributeError: 'BookUploader' object has no attribute 'process'`.
*   **Investigation:**
    *   Confirmed the `main()` function called `uploader.process()`.
    *   Searched Git history (`git log -- scripts/upload_book.py`). Found commits related to adding/removing the method.
*   **Resolution:** Restored the `process()` method definition (and its helper methods like `_generate_manifest_content`) into the `BookUploader` class in `scripts/upload_book.py` based on the Git history.

### 2. Initial Connection Errors & Database Setup

*   **Symptom:** Script failed with `requests.exceptions.ConnectionError: ('Connection aborted.', ConnectionResetError(54, 'Connection reset by peer'))` when trying to create a record via HTTP (`http://127.0.0.1:5000/api`). Suspected authentication or setup issues.
*   **Investigation:**
    *   Attempted to generate an API token using `scripts/generate_api_token.sh`.
    *   Token generation failed: `ProgrammingError: relation "accounts_user" does not exist`. This indicated the script couldn't connect to the database or the DB wasn't initialized.
    *   Identified that the `.env` file was missing, which prevented `pipenv run invenio shell` (used by the token script) from finding the `INVENIO_SQLALCHEMY_DATABASE_URI`.
    *   Attempted `pipenv run invenio db init create`, but it likely failed silently or couldn't connect without `.env`.
    *   Web UI also failed: `ProgrammingError: relation "banners" does not exist`. Confirmed incomplete DB setup.
*   **Resolution:**
    *   Manually created the `.env` file in the project root, populating it with essential variables like `INVENIO_SECRET_KEY`, `INVENIO_SQLALCHEMY_DATABASE_URI`, Redis/RabbitMQ URLs, and user-provided variables.
    *   **Crucially, re-ran `pipenv run invenio db init create` *after* the `.env` file was in place.** This allowed the command to connect to the database correctly and successfully create all necessary tables (`accounts_user`, `banners`, etc.).

### 3. Admin User and Role Setup (`scripts/create_admin.sh`)

*   **Symptom:** The `create_admin.sh` script failed with various errors:
    *   `Error: No such command 'list'` when trying `invenio roles list`.
    *   `Error: Error creating user. {'email': ['admin@turath.com is already associated with an account.']}`.
    *   Database `UniqueViolation` errors when trying to create the 'admin' role if it already existed.
*   **Investigation:** Analyzed script logic and error messages. Realized some commands were invalid or not idempotent.
*   **Resolution:** Modified `scripts/create_admin.sh`:
    *   Removed invalid checks (`invenio roles list`).
    *   Changed logic to simply *try* creating the role (`invenio roles create admin ...`) and let it fail gracefully (using `|| echo ...`) if it already exists.
    *   Changed user creation to try creating (`invenio users create ...`), and if that failed (because the user exists), attempt to activate (`invenio users activate ...`).
    *   Removed `set -e` temporarily to allow the script to continue even if role/user creation failed due to already existing entities.
    *   Ran the corrected script, which then completed successfully (ignoring the expected unique violation for the role).
    *   Re-ran `scripts/generate_api_token.sh` to ensure a valid token for the admin user was generated and saved to `.env`.

### 4. Python Dependency Issues

*   **Symptom 1:** Script failed with `ModuleNotFoundError: No module named 'PyPDF2'`.
*   **Resolution 1:** Installed the missing dependency using `pipenv install PyPDF2`. *(Note: The first attempt seemed interrupted but reported success; a second explicit install confirmed it).* 
*   **Symptom 2:** Backend server logs showed `pkg_resources.ContextualVersionConflict: (typing-extensions 4.13.2 ..., Requirement.parse('typing-extensions==4.12.2; python_version < "3.10"'), {'kombu'})`. This dependency conflict was crashing the backend application when it tried to load, causing the `Connection reset by peer` errors seen by the client script and `curl`.
*   **Resolution 2:** Forced the installation of the required version: `pipenv install "typing-extensions==4.12.2"`. **Crucially, the backend server process (`invenio run`) needed to be restarted after this fix.**

### 5. HTTP vs. HTTPS

*   **Symptom:** Even after fixing the dependency conflict and restarting the backend, connection attempts using HTTP (`http://127.0.0.1:5000`) still resulted in `Connection reset by peer`.
*   **Investigation:**
    *   Tested the API directly using `curl` with the token via HTTP: Failed (`Connection reset by peer`).
    *   Tested the API directly using `curl -k` (ignore self-signed cert) with the token via HTTPS: **Partially succeeded**, returning `{"status": 403, "message": "Permission denied."}`. This indicated the server *was* running on HTTPS.
*   **Resolution:** Switched the `--api-url` in the script command to use `https://127.0.0.1:5000/api`.

### 6. SSL Certificate Verification

*   **Symptom:** When using the HTTPS URL, the script failed with `requests.exceptions.SSLError: ... certificate verify failed: self signed certificate`.
*   **Investigation:** The Python `requests` library was correctly rejecting the self-signed certificate used by the local development server. Checked `upload_book.py` and found it used a `verify_ssl` parameter, controlled by a command-line flag.
*   **Resolution:** Added the `--no-verify-ssl` flag to the `pipenv run python scripts/upload_book.py ...` command.

### 7. Cantaloupe Errors (Informational)

*   **Symptom:** During the final successful upload, the logs showed multiple warnings: `Cantaloupe returned status 404 for http://localhost:8182/iiif/2/.../info.json?page=N`.
*   **Investigation:** These occurred during the IIIF manifest generation step when the script tried to query the Cantaloupe IIIF server (expected at `http://localhost:8182`) for image dimensions.
*   **Resolution (Implicit):** The script was designed to handle this failure gracefully by falling back to dimensions extracted directly from the PDF. The overall upload succeeded. This indicates Cantaloupe might not be running, accessible, or configured correctly at that address, which could be addressed separately if full IIIF functionality is required.

**Final Working Command:**

```bash
pipenv run python scripts/upload_book.py \
    --book-dir scripts_docs/books/history00872 \
    --api-url https://127.0.0.1:5000/api \
    --hocr-mount-point ./hocr_mount \
    --verbose \
    --skip-tiff \
    --no-verify-ssl
```

This detailed breakdown should help avoid similar issues in the future by highlighting the importance of database initialization (with `.env` present), correct dependency versions (and restarting the server after changes), admin user setup, and handling local HTTPS configurations (URL and SSL verification). 
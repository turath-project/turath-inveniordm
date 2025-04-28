## IIIF Manifest Generation: Static File vs. Dynamic Service

This document explains the two main approaches for providing IIIF Presentation API manifests within this InvenioRDM setup:

1.  **Static Generation:** Creating a manifest file (`manifest.json`) during the upload process (current approach with `upload_book.py`).
2.  **Dynamic Generation:** Using the `invenio-iiif` module to generate the manifest on-the-fly when requested.

### Approach 1: Static Manifest Generation (Current Method)

*   **What is it?**
    This approach involves creating a complete, static IIIF Presentation API v2 manifest as a JSON file. This file is generated *during* the book upload process by the `scripts/upload_book.py` script.

*   **How does it work (in `upload_book.py`)?**
    1.  The script gathers necessary information after creating the draft record and uploading primary files:
        *   Record metadata (from `metadata.json` or defaults).
        *   File information (PDF paths, HOCR paths, record ID).
        *   It queries the Cantaloupe server (e.g., at `http://localhost:8182`) for accurate image dimensions for each PDF page.
        *   It compares Cantaloupe dimensions with HOCR dimensions (if available) to calculate scale factors.
    2.  It constructs the IIIF manifest JSON structure, including:
        *   `@context`, `@id` (pointing to `.../files/manifest.json`), `@type`.
        *   `label`, `metadata` (from record metadata).
        *   `sequences` containing an array of `canvases` (one per page).
        *   Each canvas includes:
            *   Dimensions (`width`, `height`), potentially scaled based on HOCR/Cantaloupe comparison.
            *   `images` array pointing to the IIIF Image API endpoint for that page on the Cantaloupe server (`http://localhost:8182/iiif/2/{record_id}_{pdf_filename}.pdf/...?page=N`).
            *   `otherContent` pointing to annotation lists provided by the Nginx proxy (`https://localhost/annotations/...`).
            *   `seeAlso` pointing to the uploaded HOCR file within Invenio (`.../files/XXX.hocr`).
            *   `scaleFactor` property if calculated.
    3.  It adds other IIIF features like the search service (`service`) pointing to the Nginx proxy (`https://localhost/search/...`) and a related PDF download link (`related`) pointing to the Invenio file (`.../files/book.pdf`).
    4.  The script saves this generated JSON structure to a file named `manifest.json` in a temporary location.
    5.  This `manifest.json` file is then uploaded to the InvenioRDM record using the **key `manifest.json`**. (This fixed a previous bug where a temporary name was used).

*   **What's needed to make it work?**
    *   The script logic (`upload_book.py`) must correctly generate the manifest JSON.
    *   Source metadata must be available to the script.
    *   A running Cantaloupe instance accessible *by the script* during generation for accurate dimensions.
    *   The script needs the record ID after creating the draft.
    *   InvenioRDM instance to upload the file to.
    *   A mechanism for IIIF viewers (like Mirador) to *discover* the URL of this uploaded static manifest file. Currently, this relies on the standard file path `.../files/manifest.json` being requested by the viewer, possibly configured via `invenio.cfg` (`IIIF_VIEWER_CONFIG['manifest_field']` might need review if it was pointing to a custom metadata field).

*   **Pros & Cons:**
    *   **Pros:**
        *   Full control over the manifest structure; allows integration with external annotation/search services.
        *   Manifest content is fixed and doesn't depend on server-side generation logic at view time.
        *   Can pre-calculate complex scaling factors.
    *   **Cons:**
        *   Manifest is static; it won't automatically update if the record metadata or files change unless regenerated and re-uploaded.
        *   Requires custom script logic (`upload_book.py`) to be maintained.
        *   Requires uploading an extra file per record.
        *   Relies on Cantaloupe being available *during* the upload script execution.
        *   Discovery relies on the viewer knowing to look for `manifest.json` or configuration pointing to it.

### Approach 2: Dynamic Manifest Generation (`invenio-iiif`)

*   **What is it?**
    This approach uses an Invenio module (`invenio-iiif`) to dynamically generate the IIIF Presentation API manifest *when a client requests it*. It reads the record's current metadata and file information at the time of the request.

*   **How does it work?**
    1.  A client (e.g., a IIIF viewer) requests a specific URL, typically like `https://{your-invenio}/api/iiif/record:{record_id}/manifest`.
    2.  The `invenio-iiif` module intercepts this request.
    3.  It fetches the corresponding record (`record_id`) from the Invenio database.
    4.  It analyzes the record's metadata (`title`, `creator`, `description`, etc.).
    5.  It identifies the primary file(s) associated with the record that can be served via IIIF (e.g., the PDF `history00872.pdf`).
    6.  It communicates with the configured IIIF Image Server (Cantaloupe) to get technical details (dimensions, formats) for each page/image via the Image API `info.json` endpoint.
    7.  It constructs the manifest JSON dynamically based on the record metadata and the information gathered from the image server.
    8.  It returns the generated JSON manifest directly to the client.

*   **What's needed to make it work?**
    *   The `invenio-iiif` module must be installed and correctly configured within your InvenioRDM instance (`invenio.cfg`, environment variables).
    *   A running and correctly configured IIIF Image Server (like Cantaloupe) must be accessible *by the Invenio backend server*.
    *   **(Likely)** Running Celery background workers, as IIIF processing might involve asynchronous tasks.
    *   File storage must be configured such that both Invenio and the Image Server can access the source files (e.g., PDFs).
    *   The record metadata must be present and sufficiently detailed for `invenio-iiif` to populate the manifest fields.

*   **Pros & Cons:**
    *   **Pros:**
        *   Manifest always reflects the *current* state of the record's metadata and files.
        *   No need to generate or upload a separate manifest file.
        *   Uses standardized Invenio endpoints for discovery.
        *   Leverages a maintained community module (potentially less custom code).
    *   **Cons:**
        *   Requires `invenio-iiif`, Cantaloupe, and potentially Celery to be running and correctly configured *at view time*.
        *   Less direct control over the exact manifest structure compared to static generation.
        *   Customization requires interacting with Invenio's configuration, signals, or potentially overriding module components.
        *   Might have slightly higher latency for the first request as the manifest is generated on demand.
        *   The default generated manifest might be basic (as we saw with the empty `canvases` array when we hit the endpoint, likely because the setup wasn't complete).

### Customizing Dynamic Manifests (`invenio-iiif`)

Making customizations when using the dynamic approach involves working within the Invenio framework:

1.  **Configuration (`invenio.cfg` / Env Vars):** Check the `invenio-iiif` documentation for configuration variables. These might allow you to set default labels, control metadata inclusion, or configure image server interactions.
2.  **Record Metadata:** The primary way to influence the dynamic manifest is by ensuring the source Invenio record has rich and accurate metadata in the standard fields that `invenio-iiif` reads (title, creator, description, subjects, dates, etc.).
3.  **Custom Metadata Fields:** To include custom metadata fields (like your `turath:iiif_manifest`, although that specific one wouldn't be needed dynamically), you might need to configure `invenio-iiif` or use signals to tell it which custom fields to look for and how to map them into the manifest structure (e.g., into the `metadata` array).
4.  **Invenio Signals:** `invenio-iiif` likely emits signals (using Flask/Blinker signals) at various points during manifest generation (e.g., `before_manifest_render`). You can write custom Python code (a signal receiver) in your Invenio instance to listen for these signals and modify the manifest data dictionary just before it's converted to JSON. This is powerful for adding custom logic or fields.
5.  **Overriding Components:** For deep customization, you might need to override parts of `invenio-iiif`, such as its internal data serializers (e.g., Marshmallow schemas) or templates, using Invenio's module overriding mechanisms. This requires a good understanding of both Invenio and the `invenio-iiif` module's code.

In summary, the **static approach** is currently used to provide the necessary customization for integrating external services and calculated scaling factors, despite the need for careful script maintenance and an extra upload step. The dynamic approach remains an option but would require significant configuration and potentially custom development to replicate the current manifest features. 
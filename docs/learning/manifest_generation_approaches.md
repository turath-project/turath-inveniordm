## IIIF Manifest Generation: Static File vs. Dynamic Service

This document explains the two main approaches for providing IIIF Presentation API manifests within this InvenioRDM setup:

1.  **Static Generation:** Creating a manifest file (`manifest.json`) during the upload process (current approach with `upload_book.py`).
2.  **Dynamic Generation:** Using the `invenio-iiif` module to generate the manifest on-the-fly when requested.

### Approach 1: Static Manifest Generation (Current Method)

*   **What is it?**
    This approach involves creating a complete, static IIIF Presentation API v2 or v3 manifest as a JSON file. This file is generated *before* or *during* the book upload process by an external script (`scripts/upload_book.py` in this case).

*   **How does it work (in `upload_book.py`)?**
    1.  The script gathers necessary information:
        *   Record metadata (from `metadata.json` or defaults).
        *   File information (PDF paths, HOCR paths, dimensions).
        *   It attempts to query Cantaloupe (the IIIF Image Server, e.g., at `http://localhost:8182`) for accurate image dimensions for each page, but falls back to PDF-extracted dimensions if Cantaloupe is unavailable (as observed in our logs).
    2.  It constructs the IIIF manifest JSON structure, including:
        *   `@context`, `@id`, `@type`.
        *   `label`, `metadata`, `description` (from record metadata).
        *   `sequences` containing an array of `canvases` (one per page).
        *   Each canvas includes:
            *   Dimensions (`width`, `height`).
            *   `images` array pointing to the IIIF Image API endpoint for that page on the image server (e.g., Cantaloupe URL like `http://localhost:8182/iiif/2/{identifier}/full/full/0/default.jpg?page=N`).
            *   **(Optional)** `otherContent` pointing to annotation lists (e.g., `https://localhost/annotations/...`).
            *   **(Optional)** `seeAlso` pointing to related resources like the HOCR file for that page.
    3.  It might add other IIIF features like search service (`service`) or related links (`related`).
    4.  The script saves this generated JSON structure to a temporary file (e.g., `tmpXXXX.json`).
    5.  This manifest file is then uploaded to the InvenioRDM record like any other file (PDF, HOCR).

*   **What's needed to make it work?**
    *   The script logic (`upload_book.py`) must correctly generate the manifest JSON.
    *   Source metadata must be available to the script.
    *   **(Ideally)** A running Cantaloupe instance accessible *by the script* during generation for accurate dimensions (though the script has fallbacks).
    *   InvenioRDM instance to upload the file to.
    *   A mechanism for IIIF viewers (like Mirador) to *discover* the URL of this uploaded static manifest file. This typically involves storing the file's download URL in a specific field within the record's metadata (e.g., `custom_fields.turath:iiif_manifest`). *(Note: We observed this step wasn't working correctly, as the custom field wasn't present in the final record, likely due to the field not being defined in the Invenio data model).* 

*   **Pros & Cons:**
    *   **Pros:**
        *   Full control over the manifest structure; can include highly custom elements not supported by dynamic generators.
        *   Manifest content is fixed and doesn't depend on server-side generation logic at view time.
        *   Can potentially pre-generate complex manifests offline.
    *   **Cons:**
        *   Manifest is static; it won't automatically update if the record metadata or files change unless regenerated and re-uploaded.
        *   Requires custom script logic (`upload_book.py`) to be maintained.
        *   Requires uploading an extra file per record.
        *   Discovery mechanism (linking the record to its static manifest) needs to be robustly implemented and configured in Invenio.
        *   Can lead to inconsistencies if the generation script fails to get accurate info (like Cantaloupe dimensions).

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

In summary, the static approach offers maximum control but requires external generation and careful management, while the dynamic approach offers automatic updates and integration but requires a fully configured server environment and potentially more complex customization methods within Invenio. 
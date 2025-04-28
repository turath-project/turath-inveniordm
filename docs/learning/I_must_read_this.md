# Assistant Learning Summary: Key Takeaways & Pitfalls


## 5. Manifest Generation & Link Consistency

*   **Key Bug:** The `upload_book.py` script generated correct internal `@id` links (`.../manifest.json`) but uploaded the file using a temporary name (`tmpXXX.json`).
*   **Lesson:** When dealing with processes that generate structured data (like IIIF manifests) containing internal links, **ensure absolute consistency** between the generated links and the final storage key/filename used for the data itself. The mechanism for saving/uploading the generated file is critical.

## 6. Testing API/IIIF Links

*   **Lesson:** Understand the difference between Invenio API endpoints:
    *   `.../files/{filename}`: Returns file **metadata** (JSON).
    *   `.../files/{filename}/content`: Returns the actual file **content**.
    *   The file metadata endpoint **does not parse** file content. Therefore, testing a manifest's internal canvas ID (`.../manifest.json/canvas/p001`) against the metadata endpoint (`.../files/manifest.json`) will **incorrectly** result in a 404.
    *   To validate manifest links, test the *content* endpoint for the manifest itself, and test *other* links (Cantaloupe, HOCR files, PDF files, proxied services) directly using `curl -I` or `curl -k` as appropriate. 
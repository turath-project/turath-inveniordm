# Strategic Decision: Annotation and Search Service Implementation

This document outlines the discussion points regarding the implementation strategy for the HOCR-based annotation and search services within the Turath InvenioRDM project.

## Context

The goal is to provide IIIF Annotation and Content Search capabilities based on HOCR files associated with book records. Two primary approaches were considered:

1.  **Containerized Flask Services:** Standalone Python Flask applications for annotation and search, integrated into the main Docker Compose setup and accessed via an Nginx reverse proxy.
2.  **Elasticsearch Integration:** Leveraging InvenioRDM's built-in Elasticsearch instance to index HOCR content and potentially serve both search and annotation data.

## Approach 1: Containerized Flask Services (Current Implementation)

### Pros

*   Development work is largely complete (Dockerfiles, Compose integration, Nginx proxy).
*   Relatively straightforward Python logic using standard libraries (Flask, BeautifulSoup).
*   Clear separation of concerns between these services and the core InvenioRDM application.

### Cons

*   Requires managing additional Docker containers.
*   Relies on a host bind mount (`./hocr_mount`) for HOCR data sharing, which might have deployment or permission complexities.
*   The custom Flask-based search might be less powerful/scalable than Elasticsearch for large datasets.

### Difficulty

*   Low to Medium (mostly completed). Remaining work involves testing, refinement, and potentially improving the data sharing mechanism.

## Approach 2: Elasticsearch Integration (Proposed Alternative)

### Pros

*   Leverages existing, robust infrastructure (InvenioRDM's Elasticsearch).
*   Potentially more powerful, scalable, and feature-rich search capabilities (text analysis, relevance, complex queries).
*   May simplify deployment by reducing the number of custom containers.
*   Aligns better with InvenioRDM's architecture for indexing and search.

### Cons

*   **Significant Learning Curve:** Requires learning Elasticsearch (mappings, query DSL, analyzers) and InvenioRDM's indexing internals.
*   **Complex HOCR Indexing:** Getting InvenioRDM to index the *full content* and *structure* (coordinates) of HOCR files into Elasticsearch is non-trivial and likely requires custom development (indexing plugins/pipelines). Standard InvenioRDM primarily indexes record *metadata*.
*   **Annotation Data Suitability:** Elasticsearch might not be the ideal tool for efficiently storing and querying the precise word coordinates needed for the annotation service. A separate mechanism might still be required.
*   **Implementation Complexity:** Modifying InvenioRDM's core indexing behaviour is inherently complex.

### Difficulty

*   **High.** Requires significant research, learning, and custom development within the InvenioRDM framework.

## Recommendation / Considerations

*   **Search:** Elasticsearch offers superior long-term potential for search functionality.
*   **Annotations:** The current Flask service approach for generating coordinate annotations directly from HOCR might be more practical than forcing this data into Elasticsearch.
*   **Hybrid Approach:** Consider using Elasticsearch for *search* (requiring custom HOCR text indexing) while retaining the Flask service (or a similar component) for *annotations*.
*   **Trade-offs:** The decision involves balancing faster completion (current approach) against a potentially more integrated but significantly more complex architecture (Elasticsearch).

## Next Steps

*   Discuss these trade-offs with stakeholders.
*   If pursuing Elasticsearch:
    *   Initiate research into InvenioRDM custom indexing.
    *   Begin learning Elasticsearch fundamentals.
    *   Investigate examples of file content indexing in InvenioRDM.
*   If continuing the current approach:
    *   Complete testing of the Flask services via the Nginx proxy.
    *   Address the HOCR filename vs. URL path discrepancy (`001.hocr` vs. `p001`).
    *   Refine the HOCR data sharing mechanism if necessary. 
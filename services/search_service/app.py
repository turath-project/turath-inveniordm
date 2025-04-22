from flask import Flask, jsonify, request
from flask_cors import CORS
from bs4 import BeautifulSoup
import os
import json
import ssl
import logging
from urllib.parse import urlparse, urlunparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Configuration from Environment Variables ---
# Base directory for HOCR files inside the container
HOCR_BASE_DIR = os.environ.get('HOCR_BASE_DIR', '/hocr_data/books')
# Base URL for this search service (for constructing search result IDs)
SEARCH_SERVICE_BASE_URL = os.environ.get('SEARCH_SERVICE_BASE_URL', 'http://localhost:5001')
# Base URL for the IIIF Image/Presentation API server (needed if constructing canvas IDs directly)
# Often, the canvas ID comes from the HOCR data itself or the manifest.
# Let's rely on the HOCR data first, but have this as a fallback if needed.
IIIF_SERVER_BASE_URL = os.environ.get('IIIF_SERVER_BASE_URL', 'http://localhost:8000')
# --- End Configuration ---

# Configure CORS using environment variable or defaults
allowed_origins = os.environ.get('CORS_ALLOWED_ORIGINS', "https://localhost:3000,http://localhost:3000,http://127.0.0.1:3000,https://127.0.0.1:5000,https://localhost:8000,https://localhost:5000").split(',')
logger.info(f"Allowed CORS origins: {allowed_origins}")
CORS(app, resources={
    r"/*": {
        "origins": allowed_origins,
        "methods": ["GET", "OPTIONS"], # Search/Autocomplete are GET
        "allow_headers": ["Content-Type"]
    }
})

logger.info(f"HOCR Base Directory: {HOCR_BASE_DIR}")
logger.info(f"Search Service Base URL: {SEARCH_SERVICE_BASE_URL}")
logger.info(f"IIIF Server Base URL (Fallback): {IIIF_SERVER_BASE_URL}")

# --- Helper Functions ---

def extract_base_canvas_id(canvas_id_with_fragment):
    """Removes the #xywh=... fragment from a canvas ID."""
    parsed = urlparse(canvas_id_with_fragment)
    # Reconstruct the URL without the fragment
    base_id = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, ''))
    return base_id

def get_hocr_data_for_book(book_id):
    """Loads and parses all HOCR files for a given book ID, extracting word data."""
    book_hocr_dir = os.path.join(HOCR_BASE_DIR, book_id, 'hocr')
    logger.info(f"Looking for HOCR files in: {book_hocr_dir}")
    word_data = []

    if not os.path.isdir(book_hocr_dir):
        logger.error(f"HOCR directory not found for book_id '{book_id}' at {book_hocr_dir}")
        raise FileNotFoundError(f"HOCR directory not found for book_id: {book_id}")

    try:
        hocr_files = sorted([f for f in os.listdir(book_hocr_dir) if f.endswith('.hocr')])
    except Exception as e:
        logger.error(f"Error listing directory {book_hocr_dir}: {e}")
        raise

    if not hocr_files:
        logger.warning(f"No .hocr files found in {book_hocr_dir}")
        return [] # Return empty list if no HOCR files found

    logger.info(f"Found HOCR files: {hocr_files}")

    # Default Canvas ID construction (can be overridden by HOCR data if available)
    # Expected format: {IIIF_BASE_URL}/{book_id}/canvas/{page_identifier_without_ext}
    # Example: http://localhost:8000/history00871/canvas/p1

    for hocr_file in hocr_files:
        page_identifier = hocr_file.replace('.hocr', '') # e.g., 'p1' from 'p1.hocr'
        hocr_file_path = os.path.join(book_hocr_dir, hocr_file)

        try:
            with open(hocr_file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')

                # Attempt to find a base canvas ID from the HOCR header (less common)
                # Example: <meta name="DC.identifier" content="http://example.com/canvas/1" />
                base_canvas_meta = soup.find('meta', attrs={'name': 'DC.identifier'})
                if base_canvas_meta and base_canvas_meta.get('content'):
                    base_canvas_id_from_hocr = base_canvas_meta.get('content')
                    logger.debug(f"Found base canvas ID in HOCR meta: {base_canvas_id_from_hocr}")
                else:
                    # Fallback to constructing the canvas ID
                    base_canvas_id_from_hocr = f"{IIIF_SERVER_BASE_URL}/{book_id}/canvas/{page_identifier}"
                    logger.debug(f"Constructing canvas ID: {base_canvas_id_from_hocr}")


                for idx, word in enumerate(soup.find_all(class_='ocrx_word')):
                    text_content = word.get_text().strip()
                    if not text_content:
                        continue

                    if word.get('title'):
                        title_parts = word.get('title').split(';')
                        coords_part = title_parts[0].strip()

                        if coords_part.startswith('bbox'):
                            bbox = coords_part.split(' ')[1:]
                            if len(bbox) == 4:
                                try:
                                    x1, y1, x2, y2 = map(int, bbox)
                                    width = x2 - x1
                                    height = y2 - y1

                                    if width < 0 or height < 0:
                                        logger.warning(f"Skipping word with negative dimensions in {hocr_file_path}: bbox {bbox}")
                                        continue

                                    word_data.append({
                                        'text': text_content,
                                        'canvas': base_canvas_id_from_hocr, # Use the determined base canvas ID
                                        'page_id': page_identifier,
                                        'word_id': idx,
                                        'x': x1,
                                        'y': y1,
                                        'w': width,
                                        'h': height,
                                        'lang': word.get('lang', 'en') # Default lang
                                    })
                                except ValueError:
                                    logger.warning(f"Skipping word with invalid integer bbox values in {hocr_file_path}: {bbox}")
                                except Exception as e_inner:
                                    logger.warning(f"Skipping word due to error processing bbox/text in {hocr_file_path}: {e_inner}")
                            else:
                                logger.warning(f"Skipping word with incorrect number of bbox values in {hocr_file_path}: {bbox}")
                        else:
                             logger.warning(f"Skipping word with unexpected title format (no 'bbox') in {hocr_file_path}: {coords_part}")
                    else:
                        logger.warning(f"Skipping word missing 'title' attribute in {hocr_file_path}")

        except FileNotFoundError:
            logger.error(f"HOCR file {hocr_file_path} vanished while processing book {book_id}")
            # Continue to next file if one disappears mid-process?
            continue
        except Exception as e:
            logger.error(f"Error parsing HOCR file {hocr_file_path} for book {book_id}: {e}", exc_info=True)
            # Optionally raise an error or continue to next file
            continue # Continue with next file if one fails to parse

    logger.info(f"Loaded {len(word_data)} words for book '{book_id}'")
    return word_data

# --- IIIF Content Search API Implementation ---

# Base Search Endpoint (conforms to v0/v1 spec where possible)
@app.route('/search/<path:book_id>', methods=['GET', 'OPTIONS'])
def iiif_search(book_id):
    """IIIF Content Search API endpoint (v0/v1 compatible)."""
    if request.method == 'OPTIONS':
        logger.debug(f"Handling OPTIONS request for search/{book_id}")
        return '', 204

    query = request.args.get('q', '').strip()
    motivation = request.args.get('motivation', 'painting').strip() # Typically 'painting'
    page_param = request.args.get('page') # Optional page filtering

    logger.info(f"Search request for book '{book_id}', query='{query}', motivation='{motivation}', page='{page_param}'")

    if not query:
        # Return empty list if no query provided
        return jsonify({
            "@context": "http://iiif.io/api/search/1/context.json",
            "@id": f"{SEARCH_SERVICE_BASE_URL}/search/{book_id}?q={query}&motivation={motivation}",
            "@type": "sc:AnnotationList",
            "resources": [],
            "within": {
                "@type": "sc:Layer",
                "total": 0,
                # "first": ..., # Pagination links omitted for simplicity
                # "last": ...
            },
            "hits": []
        })

    try:
        # Load all word data for the book
        all_word_data = get_hocr_data_for_book(book_id)

        if not all_word_data:
             # Return empty list if no HOCR data found for the book
             return jsonify({"error": f"No HOCR data found or loaded for book '{book_id}'"}), 404

        search_results = []
        query_lower = query.lower()

        # Filter words by query and optionally by page
        for word in all_word_data:
            # Basic substring matching (case-insensitive)
            if query_lower in word['text'].lower():
                # Apply page filter if provided
                if page_param and str(word['page_id']) != page_param:
                    continue
                search_results.append(word)

        logger.info(f"Found {len(search_results)} matches for query '{query}' in book '{book_id}'")

        # --- Construct IIIF Search API Response --- 

        resources = [] # The annotations themselves
        hits = []      # Hit information with context

        # Group results by page to build context efficiently
        page_words_map = {}
        for word in all_word_data:
            canvas = word['canvas']
            if canvas not in page_words_map:
                # Store words sorted by y-coordinate for reading order context
                page_words_map[canvas] = sorted([w for w in all_word_data if w['canvas'] == canvas], key=lambda x: x['y'])

        processed_hit_indices = set()

        # Process matches to create annotations and hits
        for i, match in enumerate(search_results):
            if i in processed_hit_indices:
                continue # Skip if already part of a multi-word hit

            canvas_id = match['canvas']
            page_items = page_words_map.get(canvas_id, [])

            try:
                current_word_index_in_page = page_items.index(match)
            except ValueError:
                 logger.warning(f"Matched word not found in page_words_map for canvas {canvas_id}. Word: {match}")
                 continue # Should not happen if map is built correctly

            # --- Build Annotation --- 
            # Annotation ID needs to be unique
            annotation_id = f"{SEARCH_SERVICE_BASE_URL}/annotations/{book_id}/{match['page_id']}/{match['word_id']}"
            annotation = {
                "@id": annotation_id,
                "@type": "oa:Annotation",
                "motivation": "sc:painting", # Standard for search results
                "resource": {
                    "@type": "cnt:ContentAsText",
                    "chars": match['text'],
                    "format": "text/plain",
                    "language": match['lang']
                },
                "on": f"{canvas_id}#xywh={match['x']},{match['y']},{match['w']},{match['h']}"
            }
            resources.append(annotation)

            # --- Build Hit with Context --- 
            # Find context (surrounding words)
            context_words_before = 5
            context_words_after = 5
            start_idx = max(0, current_word_index_in_page - context_words_before)
            end_idx = min(len(page_items), current_word_index_in_page + context_words_after + 1)

            before_text = ' '.join(w['text'] for w in page_items[start_idx:current_word_index_in_page])
            after_text = ' '.join(w['text'] for w in page_items[current_word_index_in_page + 1:end_idx])

            # Create hit
            hit = {
                "@type": "search:Hit",
                "annotations": [annotation_id], # Link to the annotation
                "match": match['text'], # The exact word matched
                "before": before_text,
                "after": after_text,
                # Add selector for the hit if needed (might be same as annotation)
                # "selector": ...
            }
            hits.append(hit)
            processed_hit_indices.add(i) # Mark as processed


        # --- Final Response Structure (IIIF Search API v1) ---
        response_id = f"{SEARCH_SERVICE_BASE_URL}/search/{book_id}?q={query}&motivation={motivation}"
        if page_param:
            response_id += f"&page={page_param}"

        response = {
            "@context": "http://iiif.io/api/search/1/context.json",
            "@id": response_id,
            "@type": "sc:AnnotationList",
            "resources": resources,
            "within": {
                "@type": "sc:Layer",
                "total": len(resources), # Total annotations found
                # Pagination links (first, last) omitted for simplicity
            },
            "hits": hits
            # "termList": ... # If providing term suggestions
            # "ignored": [...] # If ignoring parameters
        }

        return jsonify(response)

    except FileNotFoundError as e:
        logger.error(f"HOCR data not found for book_id '{book_id}' during search: {e}")
        return jsonify({"error": f"HOCR data not found for book '{book_id}'. {e}"}), 404
    except Exception as e:
        logger.error(f"Error during search for book '{book_id}', query '{query}': {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred during search: {str(e)}", "type": type(e).__name__}), 500


# --- Autocomplete Endpoint --- 
@app.route('/autocomplete/<path:book_id>', methods=['GET', 'OPTIONS'])
def iiif_autocomplete(book_id):
    """IIIF Content Search Autocomplete endpoint."""
    if request.method == 'OPTIONS':
        logger.debug(f"Handling OPTIONS request for autocomplete/{book_id}")
        return '', 204

    query = request.args.get('q', '').strip()
    motivation = request.args.get('motivation', 'painting').strip()
    # date = request.args.get('date') # Other optional params
    # user = request.args.get('user')

    logger.info(f"Autocomplete request for book '{book_id}', query='{query}', motivation='{motivation}'")

    if not query:
        # Return empty list if no query provided
        return jsonify({
            "@context": "http://iiif.io/api/search/1/context.json",
            "@id": f"{SEARCH_SERVICE_BASE_URL}/autocomplete/{book_id}?q=&motivation={motivation}",
            "@type": "search:TermList",
            "terms": []
        })

    try:
        all_word_data = get_hocr_data_for_book(book_id)

        if not all_word_data:
             return jsonify({"error": f"No HOCR data found or loaded for book '{book_id}'"}), 404

        matches = set() # Use set for unique terms
        query_lower = query.lower()
        limit = 20 # Max number of suggestions

        for word in all_word_data:
            word_text_lower = word['text'].lower()
            if word_text_lower.startswith(query_lower):
                 matches.add(word['text']) # Add the original case term
                 if len(matches) >= limit:
                     break

        logger.info(f"Found {len(matches)} autocomplete suggestions for query '{query}' in book '{book_id}'")

        # Format terms according to IIIF Search API spec
        terms = []
        for term in sorted(list(matches)):
            term_entry = {
                "match": term,
                "url": f"{SEARCH_SERVICE_BASE_URL}/search/{book_id}?q={term}&motivation={motivation}",
                # "count": ... # Could add count if needed
            }
            terms.append(term_entry)

        response = {
            "@context": "http://iiif.io/api/search/1/context.json",
            "@id": f"{SEARCH_SERVICE_BASE_URL}/autocomplete/{book_id}?q={query}&motivation={motivation}",
            "@type": "search:TermList",
            "terms": terms
            # "ignored": [...] # If ignoring parameters
        }
        return jsonify(response)

    except FileNotFoundError as e:
        logger.error(f"HOCR data not found for book_id '{book_id}' during autocomplete: {e}")
        return jsonify({"error": f"HOCR data not found for book '{book_id}'. {e}"}), 404
    except Exception as e:
        logger.error(f"Error during autocomplete for book '{book_id}', query '{query}': {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred during autocomplete: {str(e)}", "type": type(e).__name__}), 500


# --- Simple Health Check / Info Endpoint ---
@app.route('/')
def info():
    return jsonify({
        "status": "running",
        "message": "IIIF Content Search Service (HOCR-based)",
        "search_endpoint_pattern": f"{SEARCH_SERVICE_BASE_URL}/search/<book_id>?q=<query>",
        "autocomplete_endpoint_pattern": f"{SEARCH_SERVICE_BASE_URL}/autocomplete/<book_id>?q=<query>",
        "configuration": {
             "hocr_base_dir": HOCR_BASE_DIR,
             "iiif_server_base_url_fallback": IIIF_SERVER_BASE_URL
        }
    })

# --- Legacy Endpoint Handling (Optional) ---
# Redirect or handle old /search and /autocomplete if necessary
# Example:
# @app.route('/search') -> redirect to info() or return error
# @app.route('/autocomplete') -> redirect to info() or return error


# --- SSL/Running ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001)) # Get port from environment or default
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    use_ssl = os.environ.get('USE_SSL', 'false').lower() == 'true'

    # Default cert paths relative to script, can be overridden by ENV
    cert_path_env = os.environ.get('SSL_CERT_PATH', 'certs/cert.pem')
    key_path_env = os.environ.get('SSL_KEY_PATH', 'certs/key.pem')
    # Resolve paths relative to the script's directory if they are relative
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cert_path = cert_path_env if os.path.isabs(cert_path_env) else os.path.join(script_dir, cert_path_env)
    key_path = key_path_env if os.path.isabs(key_path_env) else os.path.join(script_dir, key_path_env)

    logger.info(f"Starting Search Service on port {port} (Debug: {debug_mode}, SSL: {use_ssl})")

    if use_ssl and os.path.exists(cert_path) and os.path.exists(key_path):
        logger.info(f"Attempting to load SSL cert from: {cert_path}")
        logger.info(f"Attempting to load SSL key from: {key_path}")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            context.load_cert_chain(certfile=cert_path, keyfile=key_path)
            logger.info(f"Running HTTPS Search Service on https://0.0.0.0:{port}")
            # Use werkzeug reloader if debug=True, otherwise disable for production/docker
            use_reloader = debug_mode
            app.run(host='0.0.0.0', port=port, ssl_context=context, debug=debug_mode, use_reloader=use_reloader)
        except Exception as e:
            logger.error(f"Error starting HTTPS server: {e}", exc_info=True)
            logger.warning("Falling back to HTTP server...")
            logger.info(f"Running HTTP Search Service on http://0.0.0.0:{port}")
            app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=debug_mode)
    else:
        if use_ssl:
            logger.warning(f"SSL configured but cert ({cert_path}) or key ({key_path}) not found.")
        logger.info(f"Running HTTP Search Service on http://0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=debug_mode) 
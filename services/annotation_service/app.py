from flask import Flask, jsonify, request
from flask_cors import CORS
from bs4 import BeautifulSoup
import os
import ssl
import logging
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Configuration from Environment Variables ---
# Base directory for HOCR files inside the container
HOCR_BASE_DIR = os.environ.get('HOCR_BASE_DIR', '/hocr_data/books')
# Base URL for this annotation service (for constructing annotation list ID)
ANNOTATION_SERVICE_BASE_URL = os.environ.get('ANNOTATION_SERVICE_BASE_URL', 'http://localhost:5002')
# Base URL for the IIIF Image/Presentation API server (for constructing canvas IDs)
IIIF_SERVER_BASE_URL = os.environ.get('IIIF_SERVER_BASE_URL', 'http://localhost:8000')
# --- End Configuration ---

# Configure CORS using environment variable or defaults
allowed_origins = os.environ.get('CORS_ALLOWED_ORIGINS', "https://localhost:3000,http://localhost:3000,http://127.0.0.1:3000,https://127.0.0.1:5000,https://localhost:8000,https://localhost:5000").split(',')
logger.info(f"Allowed CORS origins: {allowed_origins}")
CORS(app, resources={
    r"/*": {
        "origins": allowed_origins,
        "methods": ["GET", "OPTIONS"], # Annotation lists are usually GET
        "allow_headers": ["Content-Type"]
    }
})

logger.info(f"HOCR Base Directory: {HOCR_BASE_DIR}")
logger.info(f"Annotation Service Base URL: {ANNOTATION_SERVICE_BASE_URL}")
logger.info(f"IIIF Server Base URL: {IIIF_SERVER_BASE_URL}")


# Endpoint for serving annotations based on HOCR
# Example URL: /annotations/book123/p005/line -> serves annotations for page 'p005' of 'book123'
@app.route('/annotations/<book_id>/<page_identifier>/line', methods=['GET', 'OPTIONS'])
def get_page_annotations(book_id, page_identifier):
    """Serve IIIF Annotation List for a specific page based on its HOCR file."""
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        logger.debug(f"Handling OPTIONS request for {book_id}/{page_identifier}")
        # Standard CORS headers are handled by Flask-CORS extension
        return '', 204 # Use 204 No Content for OPTIONS response

    logger.info(f"Received annotation request for book: {book_id}, page: {page_identifier}")

    try:
        # Construct the expected HOCR file path using the base directory
        # Actual filename is like '001.hocr', but identifier in URL is like 'p001'
        page_label = page_identifier.lstrip('p') # Remove leading 'p' if present
        hocr_filename = f"{page_label}.hocr"
        hocr_path = os.path.join(HOCR_BASE_DIR, book_id, 'hocr', hocr_filename)
        logger.info(f"Attempting to read HOCR file from: {hocr_path}")

        if not os.path.exists(hocr_path):
            logger.error(f"HOCR file not found: {hocr_path}")
            return jsonify({"error": f"HOCR file not found for book '{book_id}', page '{page_identifier}' at {hocr_path}"}), 404

        # Construct the Canvas ID using the IIIF server base URL
        # Assuming format: {IIIF_BASE_URL}/{book_id}/canvas/{page_identifier}
        # Adjust if your manifest uses a different structure (e.g., with '/manifest.json/')
        canvas_id = f"{IIIF_SERVER_BASE_URL}/{book_id}/canvas/{page_identifier}" # Adjusted format
        logger.debug(f"Using Canvas ID: {canvas_id}")

        # Construct the Annotation List ID using this service's base URL
        annotation_list_id = f"{ANNOTATION_SERVICE_BASE_URL}/annotations/{book_id}/{page_identifier}/line"
        logger.debug(f"Using Annotation List ID: {annotation_list_id}")


        annotations = []
        with open(hocr_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

            # Find all words (or lines, depending on desired annotation granularity)
            for idx, word in enumerate(soup.find_all(class_='ocrx_word')):
                text_content = word.get_text().strip()
                if not text_content:
                    continue # Skip empty words

                if word.get('title'):
                    title_parts = word.get('title').split(';')
                    coords_part = title_parts[0].strip() # e.g., "bbox 100 200 150 220"

                    if coords_part.startswith('bbox'):
                        bbox = coords_part.split(' ')[1:]
                        if len(bbox) == 4:
                            try:
                                x1, y1, x2, y2 = map(int, bbox)
                                width = x2 - x1
                                height = y2 - y1

                                # Ensure non-negative dimensions
                                if width < 0 or height < 0:
                                     logger.warning(f"Skipping word with negative dimensions in {hocr_path}: bbox {bbox}")
                                     continue

                                # Construct unique annotation ID
                                annotation_id = f"{annotation_list_id}/anno-{idx}"

                                # Create IIIF Annotation (Presentation API v2/v3 context)
                                annotation = {
                                    "@id": annotation_id,
                                    "@type": "oa:Annotation",
                                    "motivation": "commenting", # or 'supplementing' or 'painting' depending on use case
                                    "resource": {
                                        "@type": "cnt:ContentAsText",
                                        "chars": text_content,
                                        "format": "text/plain",
                                        # Attempt to get language from hocr if available, default to 'en' or 'ar'
                                        "language": word.get('lang', 'en') # Defaulting to 'en', adjust as needed
                                    },
                                    "on": f"{canvas_id}#xywh={x1},{y1},{width},{height}" # Fragment selector on the canvas
                                }
                                annotations.append(annotation)

                            except ValueError:
                                logger.warning(f"Skipping word with invalid integer bbox values in {hocr_path}: {bbox}")
                            except Exception as e_inner:
                                logger.warning(f"Skipping word due to error processing bbox/text in {hocr_path}: {e_inner}")
                        else:
                            logger.warning(f"Skipping word with incorrect number of bbox values in {hocr_path}: {bbox}")
                    else:
                        logger.warning(f"Skipping word with unexpected title format (no 'bbox') in {hocr_path}: {coords_part}")
                else:
                    logger.warning(f"Skipping word missing 'title' attribute in {hocr_path}")


        logger.info(f"Generated {len(annotations)} annotations for {book_id}/{page_identifier}")

        # Create the IIIF Annotation List
        response = {
            # Using Presentation API v2 context, common for annotations
            "@context": "http://iiif.io/api/presentation/2/context.json",
            "@id": annotation_list_id,
            "@type": "sc:AnnotationList",
            "resources": annotations
        }

        return jsonify(response)

    except FileNotFoundError:
        # This case should be caught above, but as a fallback
        logger.error(f"HOCR file not found processing request for {book_id}/{page_identifier}")
        return jsonify({"error": f"HOCR data not found for {book_id}, page {page_identifier}"}), 404
    except Exception as e:
        logger.error(f"Error processing annotation request for {book_id}/{page_identifier}: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}", "type": type(e).__name__}), 500


# --- Simple Health Check / Info Endpoint ---
@app.route('/')
def info():
    return jsonify({
        "status": "running",
        "message": "IIIF Annotation Service (HOCR-based)",
        "annotation_endpoint_pattern": f"{ANNOTATION_SERVICE_BASE_URL}/annotations/<book_id>/<page_identifier>/line",
         "configuration": {
             "hocr_base_dir": HOCR_BASE_DIR,
             "iiif_server_base_url": IIIF_SERVER_BASE_URL
        }
    })

# --- SSL/Running ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002)) # Get port from environment or default
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    use_ssl = os.environ.get('USE_SSL', 'false').lower() == 'true'

    # Default cert paths relative to script, can be overridden by ENV
    cert_path_env = os.environ.get('SSL_CERT_PATH', 'certs/cert.pem')
    key_path_env = os.environ.get('SSL_KEY_PATH', 'certs/key.pem')
    # Resolve paths relative to the script's directory if they are relative
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cert_path = cert_path_env if os.path.isabs(cert_path_env) else os.path.join(script_dir, cert_path_env)
    key_path = key_path_env if os.path.isabs(key_path_env) else os.path.join(script_dir, key_path_env)

    logger.info(f"Starting Annotation Service on port {port} (Debug: {debug_mode}, SSL: {use_ssl})")

    if use_ssl and os.path.exists(cert_path) and os.path.exists(key_path):
        logger.info(f"Attempting to load SSL cert from: {cert_path}")
        logger.info(f"Attempting to load SSL key from: {key_path}")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            context.load_cert_chain(certfile=cert_path, keyfile=key_path)
            logger.info(f"Running HTTPS Annotation Service on https://0.0.0.0:{port}")
            # Use werkzeug reloader if debug=True, otherwise disable for production/docker
            use_reloader = debug_mode
            app.run(host='0.0.0.0', port=port, ssl_context=context, debug=debug_mode, use_reloader=use_reloader)
        except Exception as e:
            logger.error(f"Error starting HTTPS server: {e}", exc_info=True)
            logger.warning("Falling back to HTTP server...")
            logger.info(f"Running HTTP Annotation Service on http://0.0.0.0:{port}")
            app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=debug_mode)
    else:
        if use_ssl:
             logger.warning(f"SSL configured but cert ({cert_path}) or key ({key_path}) not found.")
        logger.info(f"Running HTTP Annotation Service on http://0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=debug_mode) 
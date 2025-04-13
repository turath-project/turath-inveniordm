#!/usr/bin/env python
# This script provides a simple IIIF extension for PDF support in a standalone Flask application

import os
import sys
import json
import requests
import traceback
from flask import Blueprint, jsonify, request, url_for, current_app

print("=== Registering Simple IIIF Extension ===")

# Create a blueprint for IIIF routes
blueprint = Blueprint('iiif', __name__, url_prefix='/api/iiif')

def register_blueprint(app):
    """Register the blueprint with the Flask app."""
    app.register_blueprint(blueprint)
    print("IIIF blueprint registered successfully")

@blueprint.route('/manifest/<record_id>')
def get_manifest(record_id):
    """Get IIIF manifest for a record.
    
    Args:
        record_id: Record ID to get manifest for
    """
    try:
        # Get record from API
        record_url = url_for('get_record', pid_value=record_id, _external=True)
        response = requests.get(record_url)
        if response.status_code != 200:
            return jsonify({"error": f"Record {record_id} not found"}), 404
        
        record_data = response.json()
        
        # Check if record has PDF files
        if not record_data.get('files', {}).get('entries'):
            return jsonify({"error": "Record has no files"}), 404
        
        # Find PDF files
        pdf_files = [f for f in record_data['files']['entries'] 
                    if f.get('mimetype') == 'application/pdf']
        
        if not pdf_files:
            return jsonify({"error": "Record has no PDF files"}), 404
        
        # Generate manifest for the first PDF file
        pdf_file = pdf_files[0]
        manifest = generate_pdf_manifest(record_id, pdf_file, record_data)
        
        return jsonify(manifest)
    
    except Exception as e:
        print(f"Error generating manifest: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def generate_pdf_manifest(record_id, file_metadata, record_data):
    """Generate IIIF manifest for PDF file.
    
    Args:
        record_id: Record ID
        file_metadata: Metadata for the PDF file
        record_data: Full record data
    
    Returns:
        IIIF manifest as dictionary
    """
    try:
        # Get PDF info (in a real implementation, this would be from Cantaloupe)
        file_key = file_metadata['key']
        num_pages = get_pdf_info(record_id, file_key)
        
        # Base URLs
        manifest_id = url_for('iiif.get_manifest', record_id=record_id, _external=True)
        base_image_url = url_for('iiif.get_image', record_id=record_id, file_key=file_key, _external=True)
        
        # Create manifest structure
        manifest = {
            "@context": "http://iiif.io/api/presentation/2/context.json",
            "@id": manifest_id,
            "@type": "sc:Manifest",
            "label": record_data.get('metadata', {}).get('title', f"Record {record_id}"),
            "metadata": [
                {"label": "Record ID", "value": record_id},
                {"label": "File Name", "value": file_key},
                {"label": "MIME Type", "value": file_metadata.get('mimetype')},
                {"label": "File Size", "value": f"{file_metadata.get('size', 0)} bytes"}
            ],
            "sequences": [
                {
                    "@id": f"{manifest_id}/sequence/normal",
                    "@type": "sc:Sequence",
                    "canvases": []
                }
            ]
        }
        
        # Add description if available
        if record_data.get('metadata', {}).get('description'):
            manifest["description"] = record_data['metadata']['description']
        
        # Add publication date if available
        if record_data.get('metadata', {}).get('publication_date'):
            manifest["metadata"].append({
                "label": "Publication Date", 
                "value": record_data['metadata']['publication_date']
            })
        
        # Add creators if available
        if record_data.get('metadata', {}).get('creators'):
            creators = [c.get('name') for c in record_data['metadata']['creators']]
            manifest["metadata"].append({
                "label": "Creators", 
                "value": ", ".join(creators)
            })
        
        # Create canvases for each page
        canvases = []
        for page in range(1, num_pages + 1):
            canvas_id = f"{manifest_id}/canvas/p{page}"
            image_id = f"{base_image_url}/page/{page}"
            
            canvas = {
                "@id": canvas_id,
                "@type": "sc:Canvas",
                "label": f"Page {page}",
                "width": 800,  # Default width
                "height": 1200,  # Default height
                "images": [
                    {
                        "@id": f"{image_id}/annotation",
                        "@type": "oa:Annotation",
                        "motivation": "sc:painting",
                        "resource": {
                            "@id": image_id,
                            "@type": "dctypes:Image",
                            "format": "image/jpeg",
                            "width": 800,
                            "height": 1200,
                            "service": {
                                "@context": "http://iiif.io/api/image/2/context.json",
                                "@id": image_id,
                                "profile": "http://iiif.io/api/image/2/level1.json"
                            }
                        },
                        "on": canvas_id
                    }
                ]
            }
            canvases.append(canvas)
        
        manifest["sequences"][0]["canvases"] = canvases
        return manifest
    
    except Exception as e:
        print(f"Error generating PDF manifest: {str(e)}")
        traceback.print_exc()
        raise

def get_pdf_info(record_id, file_key):
    """Get PDF information.
    
    In a real implementation, this would call Cantaloupe to get the number of pages.
    For this example, we'll just return a fixed number.
    
    Args:
        record_id: Record ID
        file_key: File key
    
    Returns:
        Number of pages in the PDF
    """
    try:
        # Check if the file exists
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test.pdf')
        if os.path.exists(file_path):
            # In a real implementation, we would parse the PDF to get the page count
            # For simplicity, we'll return a fixed number here
            return 3
        return 1
    except Exception as e:
        print(f"Error getting PDF info: {str(e)}")
        traceback.print_exc()
        return 1

@blueprint.route('/image/<record_id>/<path:file_key>')
def get_image(record_id, file_key):
    """Handle image requests.
    
    Args:
        record_id: Record ID
        file_key: File key
    """
    try:
        # Parse query parameters
        page = request.args.get('page', '1')
        region = request.args.get('region', 'full')
        size = request.args.get('size', 'full')
        rotation = request.args.get('rotation', '0')
        quality = request.args.get('quality', 'default')
        format_ext = request.args.get('format', 'jpg')
        
        # In a real implementation, this would call Cantaloupe to get the image
        # For this example, we'll just return a JSON response with the parameters
        response = {
            "record_id": record_id,
            "file_key": file_key,
            "page": page,
            "iiif_params": {
                "region": region,
                "size": size,
                "rotation": rotation,
                "quality": quality,
                "format": format_ext
            },
            "message": "This is a demo IIIF image API response. In a real implementation, " 
                       "this would return the actual image from Cantaloupe."
        }
        
        return jsonify(response)
    
    except Exception as e:
        print(f"Error handling image request: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500 
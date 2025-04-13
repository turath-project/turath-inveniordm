#!/usr/bin/env python
import os
import json
import sys
import datetime
from flask import Flask, jsonify, request, send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import traceback

# Import our IIIF extension
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import simple_iiif_extension

# Initialize Flask app
app = Flask(__name__)
app.config['SERVER_NAME'] = '127.0.0.1:5002'
app.config['PREFERRED_URL_SCHEME'] = 'http'

# Sample records
SAMPLE_RECORDS = {
    "202": {
        "id": "202",
        "metadata": {
            "title": "Sample PDF Document",
            "description": "A test PDF document for IIIF integration",
            "creators": [
                {"name": "Test User", "type": "personal"}
            ],
            "publication_date": "2023-01-01"
        },
        "files": {
            "enabled": True,
            "entries": [
                {
                    "key": "test.pdf",
                    "mimetype": "application/pdf",
                    "size": 12345,
                    "checksum": "md5:1234567890abcdef1234567890abcdef"
                }
            ]
        }
    }
}

# Routes
@app.route('/')
def index():
    """Root endpoint."""
    return jsonify({
        "status": "running",
        "message": "IIIF test server is running",
        "endpoints": {
            "records": "/api/records/<id>",
            "manifest": "/api/iiif/manifest/<id>",
            "image": "/api/iiif/image/<id>/<file_key>"
        }
    })

@app.route('/api/records/<pid_value>')
def get_record(pid_value):
    """Get record by ID."""
    if pid_value in SAMPLE_RECORDS:
        return jsonify(SAMPLE_RECORDS[pid_value])
    return jsonify({"error": f"Record {pid_value} not found"}), 404

@app.route('/files/<path:file_path>')
def serve_file(file_path):
    """Serve a file."""
    # For simplicity, only serve the test.pdf file
    if file_path.endswith('test.pdf'):
        pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test.pdf')
        if os.path.exists(pdf_path):
            return send_file(pdf_path, mimetype='application/pdf')
    return jsonify({"error": f"File {file_path} not found"}), 404

def create_test_pdf(filename='test.pdf', num_pages=3):
    """Create a test PDF file with the specified number of pages."""
    try:
        # Check if ReportLab is available
        import reportlab
        print(f"Creating test PDF with {num_pages} pages")
        
        # Create a PDF with the specified number of pages
        pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        c = canvas.Canvas(pdf_path, pagesize=letter)
        
        # Add pages
        for i in range(1, num_pages + 1):
            # Add some content to each page
            c.drawString(100, 750, f"Test PDF - Page {i} of {num_pages}")
            c.drawString(100, 730, "Generated for IIIF testing")
            c.drawString(100, 710, f"Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Draw a rectangle
            c.rect(100, 600, 400, 100, stroke=1, fill=0)
            c.drawString(250, 650, f"Page {i}")
            
            # Save page
            c.showPage()
        
        # Save the PDF
        c.save()
        print(f"Test PDF created at {pdf_path}")
        return pdf_path
    except ImportError:
        print("ReportLab is not installed. Cannot create test PDF.")
        print("Install with: pip install reportlab")
        return None
    except Exception as e:
        print(f"Error creating test PDF: {str(e)}")
        traceback.print_exc()
        return None

if __name__ == '__main__':
    # Register the IIIF blueprint
    with app.app_context():
        simple_iiif_extension.register_blueprint(app)

    # Check if test.pdf exists, create it if not
    pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test.pdf')
    if not os.path.exists(pdf_path):
        create_test_pdf(num_pages=3)

    # Run the Flask app
    app.run(debug=True, host='127.0.0.1', port=5002) 
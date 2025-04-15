# PDF Book Upload and IIIF Manifest Generation Implementation Plan

## Overview

This plan outlines the steps to implement a complete workflow for:
1. Uploading PDF books to InvenioRDM
2. Generating IIIF manifests that link to a Cantaloupe image server
3. Viewing the books page by page in the Mirador viewer

## Phase 1: Environment Setup and Testing

### 1.1 Verify Cantaloupe Image Server Configuration
- Ensure Cantaloupe is running properly with HTTPS enabled
- Test direct access to Cantaloupe using a sample PDF
- Verify CORS headers are properly configured
- Test URL format: `https://localhost:8182/iiif/3/bookid.pdf/full/full/0/default.jpg?page=1`

### 1.2 Test Current Upload Process
- Upload a sample PDF book using `scripts/upload_book.py`
- Verify record creation and file storage in InvenioRDM
- Document the record ID format for later use in manifest generation

### 1.3 Test Manifest Generation
- Run `scripts/generate_manifest.py` on a sample book directory
- Verify the manifest structure follows IIIF Presentation API 2.1
- Ensure all URLs in the manifest use HTTPS

## Phase 2: Link Generation and Scale Factor Calculation

### 2.1 Develop Cantaloupe URL Generator
- Create a utility function to generate proper HTTPS links to Cantaloupe
- Ensure the URL format includes the record ID from InvenioRDM
- Test the URL generator with various PDF files

### 2.2 Implement Scale Factor Calculation
- Test the auto-scaling feature in `generate_manifest.py`
- Extract dimensions from HOCR files (using BeautifulSoup)
- Get dimensions from PDF pages (using PyPDF2)
- Retrieve rendering dimensions from Cantaloupe
- Calculate and verify scale factors for accurate text highlighting

## Phase 3: Workflow Integration

### 3.1 Create End-to-End Test Script
- Develop a script that:
  - Takes a PDF book from a specified directory
  - Uploads it to InvenioRDM
  - Captures the generated record ID
  - Creates a IIIF manifest pointing to Cantaloupe with the record ID
  - Uploads the manifest to InvenioRDM
  - Verifies everything is accessible

### 3.2 Test Verification Process
- Develop verification steps to ensure:
  - PDF pages are properly rendered by Cantaloupe
  - Manifest is correctly formatted and all links work
  - Scale factors are accurate for text highlighting
  - HTTPS and CORS are properly configured
  - No mixed content issues occur

## Phase 4: Mirador Integration and Final Testing

### 4.1 Test Mirador Integration
- Access the book record in InvenioRDM
- Verify Mirador loads the manifest correctly
- Test page navigation and zooming functionality
- Verify text highlighting if HOCR files are used

### 4.2 Address Edge Cases
- Test with very large PDFs (hundreds of pages)
- Test with PDFs of various resolutions and dimensions
- Test with non-standard characters in filenames or metadata

### 4.3 Performance Optimization
- Evaluate load times for different PDF sizes
- Consider caching strategies for frequently accessed books
- Optimize scale factor calculation for better performance

## Phase 5: Documentation and Deployment

### 5.1 Update Documentation
- Document the complete workflow
- Create a troubleshooting guide
- Document scale factor calculation methodology
- Provide examples of valid manifests

### 5.2 Prepare for Production Deployment
- Replace localhost URLs with production server URLs
- Ensure proper HTTPS certificates for production
- Set up monitoring for the image server
- Create backup and recovery procedures

## Implementation Timeline

1. **Phase 1**: 1-2 days
2. **Phase 2**: 2-3 days
3. **Phase 3**: 2-3 days
4. **Phase 4**: 1-2 days
5. **Phase 5**: 1 day

## Success Criteria

1. PDF books can be uploaded to InvenioRDM
2. IIIF manifests are automatically generated with correct HTTPS links
3. Books can be viewed page by page in Mirador
4. Text highlighting works correctly if HOCR files are provided
5. All components work securely with HTTPS
6. The system handles books of various sizes and formats

## Testing Methodology

Throughout the implementation, we'll follow a step-by-step approach:
1. Test each component individually
2. Verify outputs at each stage
3. Create integration tests for the full workflow
4. Document any issues and solutions
5. Ensure all HTTP URLs are converted to HTTPS
6. Validate manifest format against IIIF specifications 
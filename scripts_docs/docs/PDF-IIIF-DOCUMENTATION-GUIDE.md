# PDF IIIF Documentation Guide

![PDF IIIF Documentation Map](https://mermaid.ink/img/pako:eNp1ksFuwjAMhl_FyhnaHtAk0E6V2GHaYdIO0w5RFKVpdqzaJDQJUpn27ksSaGFjh8Txb3-24zjjpLUBA2tbH95tAxdaJ5heWK7AbgEuW0b0KByrrcWwC0VQ1FvKV4TO-FxbOId-u2LjXXzUog4ROiA1irAWc54a6bzWnIcMPDtXGiZcwN7qQZ-eOc1N9jhgqHWBlhVBURCma-l5VfQdppW3fHM4N9HrcLOP7gumA0zLNyfwKTmiMeY4MxRO6Zw5RxVY9DdR9MpzyTu4JBsapJ106PXCc5C1d6HX82QdWwvusTlDT9qI-mlpg2aPIGP0WLsM-QrbXWsgD5A3tqnpXLeR4Q-WYhMsueBc_j5Rv7vYKhR2b7RRcNF7Ov60Y112V9btPXh0Eb-YnybLKCb5OJ9ms3w3n-W5GHNkQyigp7U4EgUXum21CjVZOZq-bNuxyPshanJeix5fR3oMrTmETG-hYNuFKmJzgovKNOu2Z74BHNLGOw?type=png)

## Introduction

This guide provides an overview of our comprehensive PDF IIIF documentation for Zenodo RDM. The documentation is organized to support different user needs, from getting started to advanced troubleshooting.

## Documentation Overview

Our PDF IIIF documentation is divided into several interconnected documents, each serving a specific purpose:

| Document | Purpose | Target Audience |
|----------|---------|-----------------|
| [PDF IIIF Support Guide](PDF-IIIF-SUPPORT.md) | Overview of PDF support in IIIF | All users |
| [PDF IIIF Developer Guide](PDF-IIIF-DEVELOPER-GUIDE.md) | Technical implementation details | Developers |
| [PDF IIIF Testing Guide](PDF-IIIF-TESTING-GUIDE.md) | Step-by-step testing procedures | QA, Testers, Admins |
| [PDF IIIF Troubleshooting](PDF-IIIF-TROUBLESHOOTING.md) | Solutions to common issues | Admins, Support |
| [PDF IIIF By Example](PDF-IIIF-BY-EXAMPLE.md) | Practical examples with code | Developers, Integrators |
| [Cantaloupe PDF Integration](CANTALOUPE-PDF-INTEGRATION.md) | Cantaloupe server integration | DevOps, Admins |
| [Cantaloupe Working Config](CANTALOUPE-WORKING.md) | Verified configuration | DevOps, Admins |

## How the Documents Connect

Here's how these documents relate to each other:

1. **Start with [PDF IIIF Support Guide](PDF-IIIF-SUPPORT.md)** for a general overview of PDF support in IIIF for Zenodo RDM.

2. **Then branch based on your role**:
   - Developers should proceed to [PDF IIIF Developer Guide](PDF-IIIF-DEVELOPER-GUIDE.md)
   - Testers should go to [PDF IIIF Testing Guide](PDF-IIIF-TESTING-GUIDE.md)
   - DevOps should check [Cantaloupe PDF Integration](CANTALOUPE-PDF-INTEGRATION.md)

3. **For specific needs**:
   - Troubleshooting issues? See [PDF IIIF Troubleshooting](PDF-IIIF-TROUBLESHOOTING.md)
   - Need code examples? Visit [PDF IIIF By Example](PDF-IIIF-BY-EXAMPLE.md)
   - Setting up Cantaloupe? Use [Cantaloupe Working Config](CANTALOUPE-WORKING.md)

## Document Summaries

### [PDF IIIF Support Guide](PDF-IIIF-SUPPORT.md)

The entry point for understanding PDF support in IIIF for Zenodo RDM. Covers:
- Overview of Cantaloupe for PDF rendering
- Advantages over traditional PDF viewers
- Basic configuration requirements
- URL structure and access patterns

### [PDF IIIF Developer Guide](PDF-IIIF-DEVELOPER-GUIDE.md)

Technical documentation for developers implementing or modifying the PDF IIIF integration:
- Implementation details of the `CantaloupeProxy` class
- How the proxy integrates with Invenio RDM
- PDF URL handling and path mapping
- Extension points for custom functionality

### [PDF IIIF Testing Guide](PDF-IIIF-TESTING-GUIDE.md)

Comprehensive guide for testing PDF IIIF functionality:
- Step-by-step testing procedures
- Setting up test environments
- Creating test records with PDF files
- Verifying IIIF functionality
- Common testing challenges and solutions

### [PDF IIIF Troubleshooting](PDF-IIIF-TROUBLESHOOTING.md)

Solutions to common issues that may arise with PDF IIIF integration:
- Diagnostic approaches for different layers
- Common errors and their solutions
- Configuration issues
- API error reference
- Advanced debugging techniques

### [PDF IIIF By Example](PDF-IIIF-BY-EXAMPLE.md)

Practical examples and code for working with PDFs in IIIF:
- Uploading PDFs to records
- Accessing PDF pages through IIIF
- Creating thumbnails and contact sheets
- Integrating with viewers
- Python code examples for common tasks

### [Cantaloupe PDF Integration](CANTALOUPE-PDF-INTEGRATION.md)

Detailed guide for integrating Cantaloupe with Zenodo RDM for PDF support:
- Cantaloupe server setup and configuration
- Docker integration
- Performance tuning
- Security considerations
- Integration with existing IIIF infrastructure

### [Cantaloupe Working Config](CANTALOUPE-WORKING.md)

Verified configuration for Cantaloupe server with PDF support:
- Docker Compose configuration
- Cantaloupe properties file
- Directory structure
- Volume mounting
- Testing the configuration

## Key Concepts Across Documents

Several key concepts appear across multiple documents:

1. **PDF Path Structure**: How PDFs are stored and accessed
   ```
   data/images/private/<record_id>/<filename>.pdf
   ```

2. **IIIF URL Pattern for PDFs**:
   ```
   http://localhost:8182/iiif/2/images%2Fprivate%2F<record_id>%2F<filename>.pdf/full/full/0/default.jpg?page=1
   ```

3. **Page Selection with Query Parameter**:
   ```
   ?page=<page_number>  # Starting from 1
   ```

4. **CantaloupeProxy Class**: The central implementation for PDF support
   ```python
   class CantaloupeProxy(IIIFProxy):
       # Handles PDF files directly without conversion to PTIF
   ```

5. **Required Configuration Settings**:
   ```python
   # In invenio.cfg
   RDM_IIIF_MANIFEST_FORMATS = ["jpeg", "jpg", "png", "tiff", "tif", "pdf"]
   IIIF_PROXY_CLASS = "zenodo_rdm.iiif.proxy:CantaloupeProxy"
   ```

## Learning Path

For those new to PDF IIIF integration, we recommend the following learning path:

1. Start with [PDF IIIF Support Guide](PDF-IIIF-SUPPORT.md) for an overview
2. Continue with [PDF IIIF Testing Guide](PDF-IIIF-TESTING-GUIDE.md) to understand the functionality
3. Try out examples from [PDF IIIF By Example](PDF-IIIF-BY-EXAMPLE.md)
4. If you encounter issues, consult [PDF IIIF Troubleshooting](PDF-IIIF-TROUBLESHOOTING.md)
5. For deeper understanding, dive into [PDF IIIF Developer Guide](PDF-IIIF-DEVELOPER-GUIDE.md)

For those focused on deployment and operations:

1. Start with [Cantaloupe PDF Integration](CANTALOUPE-PDF-INTEGRATION.md)
2. Implement the configuration from [Cantaloupe Working Config](CANTALOUPE-WORKING.md)
3. Validate functionality using the [PDF IIIF Testing Guide](PDF-IIIF-TESTING-GUIDE.md)

---

*This guide was created to help navigate the PDF IIIF documentation for Zenodo RDM. If you find any gaps or have suggestions for improvement, please contribute to the documentation.* 
# Turath InvenioRDM

Welcome to your InvenioRDM instance customized for the Turath project.

## Getting started

Run the following commands in order to start your new InvenioRDM instance:

```console
invenio-cli containers start --lock --build --setup
```

The above command first builds the application docker image and afterwards
starts the application and related services (database, Elasticsearch, Redis
and RabbitMQ). The build and boot process will take some time to complete,
especially the first time as docker images have to be downloaded during the
process.

Once running, visit https://127.0.0.1 in your browser.

**Note**: The server is using a self-signed SSL certificate, so your browser
will issue a warning that you will have to by-pass.

## Features

### Custom Metadata Schema for Cultural Heritage Materials

Turath InvenioRDM includes an extended metadata schema customized for cultural heritage materials. The configuration uses the turath namespace to organize custom fields, ensuring clear data organization and avoiding name clashes.

#### Metadata Components

The custom schema includes:

- **Title Information**
  - Primary title with formatting guidelines
  - Alternative titles (particularly for Arabic script resources)
  - Alternative title script identification (controlled vocabulary)

- **Authorship Information**
  - Creator details including Arabic name variants
  - Contributor roles with specialized terminology
  - Author affiliations and identifiers

- **Cultural Heritage Specific Fields**
  - Format descriptors (medium, extent, dimensions)
  - Geographic and temporal coverage optimized for historical materials
  - Subject classifications using controlled vocabularies

- **Resource Relationships**
  - Special relationship types for cultural heritage materials
  - Hierarchical content relationships

These custom fields are defined in the `invenio.cfg` file using different field types:
- `TextCF` - For standard text fields
- `KeywordCF` - For filterable exact-match text
- `VocabularyCF` - For controlled vocabulary selections

#### Implementation

The metadata schema is configured through three main sections in `invenio.cfg`:
- `RDM_NAMESPACES` - Defines the turath namespace
- `RDM_CUSTOM_FIELDS` - Declares all custom fields with their validation rules
- `RDM_CUSTOM_FIELDS_UI` - Controls how fields appear in the UI

### IIIF Integration with Mirador Previewer

This repository includes an integrated Mirador IIIF viewer for previewing compatible documents and images. The Mirador previewer supports:

- Viewing high-resolution images with deep zoom capabilities
- Support for IIIF manifests
- Side-by-side comparison of images
- Annotations and bookmarking

#### Mirador Integration

The Mirador previewer is integrated directly into the project (not as a separate installable package). This was accomplished by:

1. Adding the package as an editable dependency in the Pipfile:
   ```
   invenio-previewer-mirador = {editable = true, path="./invenio-previewer-mirador"}
   ```

2. The previewer automatically registers itself through entry points, making it available for previewing compatible files.

3. Security settings have been configured to allow the previewer to function properly:
   ```python
   APP_DEFAULT_SECURE_HEADERS = {
       'content_security_policy': {
           'default-src': ["'self'", 'data:', "'unsafe-inline'", "'unsafe-eval'", "blob:", "unpkg.com", "*.iiif.io"],
           # Additional security settings...
       }
   }
   ```

## Project Structure

Following is an overview of the project files and folders:

| Name | Description |
|---|---|
| ``Dockerfile`` | Dockerfile used to build your application image. |
| ``Pipfile`` | Python requirements installed via [pipenv](https://pipenv.pypa.io) |
| ``Pipfile.lock`` | Locked requirements (generated on first install). |
| ``app_data`` | Application data including vocabularies for custom fields. |
| ``assets`` | Web assets (CSS, JavaScript, LESS, JSX templates) used in the Webpack build. |
| ``docker`` | Example configuration for NGINX and uWSGI. |
| ``docker-compose.full.yml`` | Example of a full infrastructure stack. |
| ``docker-compose.yml`` | Backend services needed for local development. |
| ``docker-services.yml`` | Common services for the Docker Compose files. |
| ``invenio.cfg`` | The Invenio application configuration, including custom fields. |
| ``invenio-previewer-mirador`` | Integrated IIIF Mirador previewer for document visualization. |
| ``logs`` | Log files. |
| ``static`` | Static files that need to be served as-is (e.g. images). |
| ``templates`` | Folder for your Jinja templates. |
| ``.invenio`` | Common file used by Invenio-CLI to be version controlled. |
| ``.invenio.private`` | Private file used by Invenio-CLI *not* to be version controlled. |

## Development

### Installing Dependencies

When adding new dependencies (like the Mirador previewer) or making changes to the configuration:

1. Update the appropriate files (Pipfile, invenio.cfg)
2. Run the installation process:
   ```
   invenio-cli install
   ```

3. For testing changes with Docker, rebuild the containers:
   ```
   invenio-cli containers start --lock --build
   ```

### Adding or Modifying Metadata Fields

Custom metadata fields are defined in the `invenio.cfg` file. The process involves:

1. **Define the namespace** in `RDM_NAMESPACES`
   ```python
   RDM_NAMESPACES = {
       "turath": "https://turath.org/terms/"
   }
   ```

2. **Configure the custom fields** in `RDM_CUSTOM_FIELDS`
   ```python
   from invenio_records_resources.services.custom_fields import TextCF, KeywordCF
   from invenio_vocabularies.services.custom_fields import VocabularyCF
   
   RDM_CUSTOM_FIELDS = [
       TextCF(
           name="turath:title",
           use_as_filter=True,
           # Additional configuration...
       ),
       # More field definitions...
   ]
   ```

3. **Configure the UI display** in `RDM_CUSTOM_FIELDS_UI`
   ```python
   RDM_CUSTOM_FIELDS_UI = [
       {
           "section": "Title Information",
           "fields": [
               dict(
                   field="turath:title",
                   ui_widget="Input",
                   props=dict(
                       label="Title",
                       # Additional UI properties...
                   )
               ),
               # More UI field configurations...
           ]
       },
       # More sections...
   ]
   ```

4. **Initialize the fields** to make them searchable:
   ```
   invenio-cli install
   ```

5. If needed, reindex existing records:
   ```
   pipenv run invenio rdm-records reindex
   ```

### Managing Controlled Vocabularies

For custom fields that use controlled vocabularies (`VocabularyCF`), you need to define the vocabulary terms in the `app_data/vocabularies` directory. After adding new vocabulary definition files:

1. Load the vocabulary terms into your instance:
   ```
   pipenv run invenio rdm-records fixtures
   ```

2. This command loads all vocabularies defined in `app_data/vocabularies.yaml` and their corresponding data files.

3. You can verify the loaded vocabularies through the API at `/api/vocabularies/<vocabulary_id>`.

## Documentation

To learn more about custom fields and other InvenioRDM customizations, visit
the [InvenioRDM Documentation](https://inveniordm.docs.cern.ch/customize/metadata/custom_fields/).

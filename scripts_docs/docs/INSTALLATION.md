# Zenodo RDM Local Installation Guide

This guide explains how to install and run Zenodo RDM locally, based on a modified version of the CERN Zenodo repository adapted to work on local development environments.

## Prerequisites

Before you begin, make sure you have the following installed:
- Docker and Docker Compose
- Python 3.9
- pip and pipenv
- Node.js and npm
- Git

## Quick Installation

### 1. Clone the Repository

```bash
git clone https://github.com/AlABarazi/zenodo-rdm.git
cd zenodo-rdm
```

### 2. Environment Setup

Create a local environment file:

```bash
cat > .env << EOF
INSTANCE_PATH=./data
EOF
```

### 3. Install Dependencies

There are two approaches to installing the application:

#### Option A: Using invenio-cli (Recommended)

This is the preferred method for local development:

```bash
# Check requirements
invenio-cli check-requirements --development

# Install the application
invenio-cli install

# Set up services
invenio-cli services setup

# Run the application
invenio-cli run
```

#### Option B: Using Docker Compose

This option is simpler but gives you less control:

```bash
# First, create necessary directories
mkdir -p data/images

# Start the services
docker-compose up -d
```

For a full deployment with web UI, API, and worker:

```bash
docker-compose -f docker-compose.full.yml up -d
```

### 4. Access the Application

After successful installation, you can access:
- Web UI: http://localhost:5000
- API: http://localhost:5000/api
- OpenSearch Dashboard: http://localhost:5601
- RabbitMQ Management: http://localhost:15672 (username: guest, password: guest)
- pgAdmin: http://localhost:5050 (username: info@zenodo.org, password: zenodo)

## Detailed Configuration

### Using local.cfg for Local Development

The repository includes a `local.cfg` file which provides sensible defaults for local development. You can modify this file to adjust configuration:

```python
# Site configuration
SITE_UI_URL = "http://127.0.0.1:5000"
SITE_API_URL = "http://127.0.0.1:5000/api"

# Database configuration
SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://zenodo:zenodo@localhost:5432/zenodo"

# Redis configuration
INVENIO_ACCOUNTS_SESSION_REDIS_URL = "redis://localhost:6379/1"
INVENIO_CACHE_REDIS_URL = "redis://localhost:6379/0"
INVENIO_RATELIMIT_STORAGE_URL = "redis://localhost:6379/3"

# Message queue
INVENIO_BROKER_URL = "amqp://guest:guest@localhost:5672/"
INVENIO_CELERY_BROKER_URL = "amqp://guest:guest@localhost:5672/"
INVENIO_CELERY_RESULT_BACKEND = "redis://localhost:6379/2"

# Search
INVENIO_SEARCH_HOSTS = ["localhost:9200"]
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: If you encounter errors about ports already in use, either:
   - Stop conflicting services on your machine
   - Modify the port mappings in `docker-compose.yml`

2. **Permission issues with Docker volumes**:
   ```bash
   mkdir -p data/images && chmod -R 777 data
   ```

3. **Dependencies issues**: If you encounter missing dependencies, add them to the Pipfile:
   ```bash
   pipenv install <package-name>
   pipenv lock
   ```

4. **Database connection issues**: Ensure PostgreSQL is running and accessible:
   ```bash
   docker-compose exec db psql -U zenodo -d zenodo
   ```

5. **Logs viewing**: Check logs for specific services:
   ```bash
   docker-compose logs -f <service-name>
   ```

## Key Differences from CERN Deployment

This repository has been modified from the original CERN Zenodo repository to make it more suitable for local development:

1. **Docker Images**: Using standard Docker Hub images instead of CERN-specific registry images
2. **Authentication**: Simplified authentication and removed CERN-specific OAuth
3. **Security Settings**: Disabled HTTPS requirements for local development
4. **Dependencies**: Added missing dependencies like `greenlet` for SQLAlchemy
5. **Configuration**: Added local-focused configuration defaults

## References

- [InvenioRDM Documentation](https://inveniordm.docs.cern.ch/install/)
- [Original Zenodo Repository](https://github.com/zenodo/zenodo-rdm) 
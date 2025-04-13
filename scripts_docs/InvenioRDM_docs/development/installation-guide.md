# Turath InvenioRDM Installation Guide

## Development Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/turath-project/turath-inveniordm.git
cd turath-inveniordm
```

2. Run post-installation setup:
```bash
# Make script executable
chmod +x app_data/scripts/post-install.sh

# Run setup
./app_data/scripts/post-install.sh
```

3. Start using the system:
```bash
# See all available commands
make help

# Setup development environment
make dev-setup  # Runs install-site, setup-admin, and builds assets
```

## Available Commands {#available-commands}

The following commands are available through the Makefile:

- `dev-setup`: Complete development environment setup (recommended for new installations)
- `install-site`: Install the site package in development mode
- `setup-admin`: Configure admin user and permissions
- `build-assets`: Build all static assets
- `start`: Start all services
- `stop`: Stop all services
- `restart`: Restart all services
- `test-iiif`: Test IIIF server with sample images

For a complete list of commands, run:
```bash
make help
```

## Default Admin Access
- Email: admin@turath.com
- Password: 123456 
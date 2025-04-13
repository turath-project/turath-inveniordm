# Custom Scripts Documentation

This project includes various custom scripts that help with administration, maintenance, and development tasks. These scripts are organized in the `scripts/AlA` directory.

## Quick Access

For a complete list of available scripts and detailed documentation, see:

- [scripts/AlA/README.md](../scripts/AlA/README.md) - Primary documentation with usage examples
- [docs/scripts/README.md](./scripts/README.md) - Auto-generated comprehensive documentation

## Using the Scripts

The easiest way to use these scripts is through the Makefile in the scripts/AlA directory:

```bash
# From the project root
cd scripts/AlA

# Get help
make help

# List all available scripts
make list

# Run common tasks
make reset-password   # Reset admin password
make new-token        # Generate new API token

# Run a specific script
make run SCRIPT=script_name   # (without extension)
```

## Key Scripts

Here are some of the most commonly used scripts:

### Token Management

- **generate_new_token.sh** - Reset admin password and create a new API token
- **create_token.py** - Create an API token with custom settings

### Password Management

- **reset_admin_password.sh** - Reset the admin user's password to "123456"

### Media Conversion

- **convert_images.sh** - Convert images to PTIF format for IIIF viewing
- **batch_convert.py** - Process files from multiple records

### Record Management

- **check_record.py** - Check a record's metadata, files, and IIIF status
- **get_file.py** - Download a file from a record

### User Management

- **list_users.py** - List all users in the system
- **list_user_roles.py** - Show roles assigned to a specific user

## Documentation

To generate or update the comprehensive documentation:

```bash
cd scripts/AlA && make docs
```

This will create detailed documentation at [docs/scripts/README.md](./scripts/README.md) with comprehensive information about all available scripts.

## Adding New Scripts

New scripts should be added to the `scripts/AlA` directory following the established conventions. See the [scripts/AlA/README.md](../scripts/AlA/README.md) file for guidelines on adding new scripts. 
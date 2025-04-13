# Makefile for AlA scripts
# This file provides standardized ways to call custom scripts

# Get the current directory
SCRIPT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
PROJECT_ROOT := $(shell cd $(SCRIPT_DIR)/../.. && pwd)

# Detect all scripts in the directory
SH_SCRIPTS := $(wildcard $(SCRIPT_DIR)/*.sh)
PY_SCRIPTS := $(wildcard $(SCRIPT_DIR)/*.py)
ALL_SCRIPTS := $(SH_SCRIPTS) $(PY_SCRIPTS)

# Default target
.PHONY: help
help:
	@echo "========== Zenodo RDM Script Helper =========="
	@echo ""
	@echo "This Makefile helps you run the custom scripts in the scripts/AlA directory."
	@echo ""
	@echo "Available commands:"
	@echo ""
	@echo "  make help                Show this help message"
	@echo "  make list                List all available scripts"
	@echo "  make reset-password      Reset admin password to '123456'"
	@echo "  make new-token           Generate new API token and update .env"
	@echo "  make run SCRIPT=name     Run a specific script (without extension)"
	@echo "  make setup-iiif RECORD=id   Set up IIIF for a record"
	@echo "  make check-iiif RECORD=id   Check IIIF functionality for a record"
	@echo "  make test-cantaloupe RECORD=id FILE=name.pdf   Test Cantaloupe PDF functionality"
	@echo "  make test-cantaloupe-pages RECORD=id FILE=name.pdf PAGES=page_numbers"
	@echo "  make test-cantaloupe-proxy RECORD=id FILE=name.pdf PAGE=page_number MANIFEST=manifest_name"
	@echo "  make test-iiif           Test IIIF implementation before installation"
	@echo ""
	@echo "Examples:"
	@echo ""
	@echo "  make list                        # See all available scripts"
	@echo "  make run SCRIPT=create_token     # Run create_token.py"
	@echo "  make run SCRIPT=convert_images   # Run convert_images.sh"
	@echo "  make setup-iiif RECORD=202       # Set up IIIF for record 202"
	@echo "  make test-cantaloupe RECORD=202 FILE=history00871.pdf  # Test Cantaloupe with a PDF"
	@echo "  make test-iiif                   # Test IIIF components before installation"
	@echo ""
	@echo "For detailed documentation on each script, see:"
	@echo "  $(SCRIPT_DIR)/README.md"
	@echo ""
	@echo "=============================================="

.PHONY: list
list:
	@echo "Available scripts:"
	@echo ""
	@echo "Shell scripts (.sh):"
	@for script in $(SH_SCRIPTS); do \
		echo "  $$(basename $$script .sh)"; \
	done
	@echo ""
	@echo "Python scripts (.py):"
	@for script in $(PY_SCRIPTS); do \
		echo "  $$(basename $$script .py)"; \
	done

.PHONY: docs
docs:
	@echo "Generating documentation for all scripts..."
	@mkdir -p $(PROJECT_ROOT)/docs/scripts
	@echo "# Custom Script Documentation" > $(PROJECT_ROOT)/docs/scripts/README.md
	@echo "" >> $(PROJECT_ROOT)/docs/scripts/README.md
	@echo "This documentation covers custom scripts located in \`scripts/AlA\`" >> $(PROJECT_ROOT)/docs/scripts/README.md
	@echo "" >> $(PROJECT_ROOT)/docs/scripts/README.md
	@echo "## Shell Scripts" >> $(PROJECT_ROOT)/docs/scripts/README.md
	@echo "" >> $(PROJECT_ROOT)/docs/scripts/README.md
	@for script in $(SH_SCRIPTS); do \
		name=$$(basename $$script); \
		echo "### $$name" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		head -n 20 $$script | grep -v "#!/usr/bin/env" | grep -v "# -\*-" | sed '/^$$/d' | sed 's/^# //' >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "\`\`\`bash" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "./scripts/AlA/$$name" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "# or" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "make run SCRIPT=$$(basename $$script .sh)" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "\`\`\`" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
	done
	@echo "## Python Scripts" >> $(PROJECT_ROOT)/docs/scripts/README.md
	@echo "" >> $(PROJECT_ROOT)/docs/scripts/README.md
	@for script in $(PY_SCRIPTS); do \
		name=$$(basename $$script); \
		echo "### $$name" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		head -n 20 $$script | grep -v "#!/usr/bin/env" | grep -v "# -\*-" | sed '/^$$/d' | sed 's/^# //' | sed 's/"""//g' | sed 's/^[ \t]*//' >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "\`\`\`bash" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "python scripts/AlA/$$name" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "# or" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "make run SCRIPT=$$(basename $$script .py)" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "\`\`\`" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
		echo "" >> $(PROJECT_ROOT)/docs/scripts/README.md; \
	done
	@echo "Documentation generated at: $(PROJECT_ROOT)/docs/scripts/README.md"

.PHONY: reset-password
reset-password:
	@echo "Resetting admin password..."
	@$(SCRIPT_DIR)/reset_admin_password.sh

.PHONY: new-token
new-token:
	@echo "Generating new API token..."
	@$(SCRIPT_DIR)/generate_new_token.sh

# IIIF commands
.PHONY: setup-iiif
setup-iiif:
	@echo "Setting up IIIF for record. Usage: make setup-iiif RECORD=<id>"
	@if [ -z "$(RECORD)" ]; then \
		echo "Error: RECORD parameter is required"; \
		echo "Usage: make setup-iiif RECORD=<id>"; \
		exit 1; \
	fi
	@$(SCRIPT_DIR)/setup_iiif_for_record.sh $(RECORD)

.PHONY: check-iiif
check-iiif:
	@echo "Checking IIIF functionality for record. Usage: make check-iiif RECORD=<id>"
	@if [ -z "$(RECORD)" ]; then \
		echo "Error: RECORD parameter is required"; \
		echo "Usage: make check-iiif RECORD=<id>"; \
		exit 1; \
	fi
	@python $(SCRIPT_DIR)/check_iiif.py $(RECORD)

.PHONY: test-cantaloupe
test-cantaloupe:
	@echo "Testing Cantaloupe PDF functionality. Usage: make test-cantaloupe RECORD=<id> FILE=<filename.pdf>"
	@if [ -z "$(RECORD)" ]; then \
		echo "Error: RECORD parameter is required"; \
		echo "Usage: make test-cantaloupe RECORD=<id> FILE=<filename.pdf>"; \
		exit 1; \
	fi
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE parameter is required"; \
		echo "Usage: make test-cantaloupe RECORD=<id> FILE=<filename.pdf>"; \
		exit 1; \
	fi
	@python $(PROJECT_ROOT)/test/test_cantaloupe_basic.py --record $(RECORD) --file $(FILE)

# Test Cantaloupe PDF page selection
.PHONY: test-cantaloupe-pages
test-cantaloupe-pages:
	@if [ -z "$(RECORD)" ]; then \
		echo "Error: RECORD is required. Usage: make test-cantaloupe-pages RECORD=<record_id> FILE=<filename> [PAGES=<page_numbers>]"; \
		exit 1; \
	fi
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE is required. Usage: make test-cantaloupe-pages RECORD=<record_id> FILE=<filename> [PAGES=<page_numbers>]"; \
		exit 1; \
	fi
	@echo "Testing page selection for PDF file $(FILE) in record $(RECORD)"
	@python ../../test/test_cantaloupe_page_selection.py --record $(RECORD) --file $(FILE) $(if $(PAGES),--pages $(PAGES),)

# Test CantaloupeProxy class
.PHONY: test-cantaloupe-proxy
test-cantaloupe-proxy:
	@if [ -z "$(RECORD)" ]; then \
		echo "Error: RECORD is required. Usage: make test-cantaloupe-proxy RECORD=<record_id> FILE=<filename>"; \
		exit 1; \
	fi
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE is required. Usage: make test-cantaloupe-proxy RECORD=<record_id> FILE=<filename>"; \
		exit 1; \
	fi
	@echo "Testing CantaloupeProxy with PDF file $(FILE) in record $(RECORD)"
	@python $(PROJECT_ROOT)/test/test_cantaloupe_proxy.py --record $(RECORD) --file $(FILE) $(if $(PAGE),--page $(PAGE),) $(if $(MANIFEST),--generate-manifest,)

# Test IIIF implementation before installation
.PHONY: test-iiif
test-iiif:
	@echo "Testing IIIF implementation before installation..."
	@python $(PROJECT_ROOT)/test/run_iiif_tests.py

.PHONY: run
run:
ifndef SCRIPT
	@echo "Error: SCRIPT parameter is required"
	@echo ""
	@echo "Usage: make run SCRIPT=script_name"
	@echo ""
	@echo "Where script_name is the name of the script without extension (.py or .sh)"
	@echo ""
	@echo "Available scripts:"
	@echo ""
	@echo "Shell scripts (.sh):"
	@for script in $(SH_SCRIPTS); do \
		echo "  $$(basename $$script .sh)"; \
	done
	@echo ""
	@echo "Python scripts (.py):"
	@for script in $(PY_SCRIPTS); do \
		echo "  $$(basename $$script .py)"; \
	done
else
	@if [ -f "$(SCRIPT_DIR)/$(SCRIPT).sh" ]; then \
		echo "Running shell script: $(SCRIPT).sh"; \
		$(SCRIPT_DIR)/$(SCRIPT).sh; \
	elif [ -f "$(SCRIPT_DIR)/$(SCRIPT).py" ]; then \
		echo "Running python script: $(SCRIPT).py"; \
		cd $(PROJECT_ROOT) && python $(SCRIPT_DIR)/$(SCRIPT).py; \
	else \
		echo "Error: Script '$(SCRIPT)' not found"; \
		echo ""; \
		echo "Available scripts:"; \
		echo ""; \
		echo "Shell scripts (.sh):"; \
		for script in $(SH_SCRIPTS); do \
			echo "  $$(basename $$script .sh)"; \
		done; \
		echo ""; \
		echo "Python scripts (.py):"; \
		for script in $(PY_SCRIPTS); do \
			echo "  $$(basename $$script .py)"; \
		done; \
	fi
endif 
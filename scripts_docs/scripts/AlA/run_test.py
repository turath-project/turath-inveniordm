#!/usr/bin/env python
"""
Run the IIIF integration test with specific parameters.

Usage:
    pipenv run invenio shell -c "exec(open('scripts/AlA/run_test.py').read())"
"""

import os
import sys

# When running via exec in shell, __file__ is not defined
# So we need to set it explicitly
file_path = 'scripts/AlA/run_test.py'
dir_path = os.path.dirname(os.path.abspath(file_path))

# Set parameters directly before importing the test script
sys.argv = [
    sys.argv[0],
    '--record-id=202',
    f'--pdf={os.path.join(dir_path, "test.pdf")}',
    '--pages=3'
]

# Execute the test script
print("=== Running IIIF Integration Test with Parameters ===")
print(f"Parameters: {sys.argv}")

# Load and execute the test script
test_script_path = os.path.join(dir_path, "test_iiif_integration.py")
if os.path.exists(test_script_path):
    print(f"Executing: {test_script_path}")
    with open(test_script_path) as f:
        exec(f.read())
else:
    print(f"Error: Test script not found at {test_script_path}")
    sys.exit(1) 
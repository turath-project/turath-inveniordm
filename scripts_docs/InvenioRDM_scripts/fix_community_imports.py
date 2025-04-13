#!/usr/bin/env python3
"""
Utility script to fix imports in community scripts.
This adds try/except blocks around imports to handle both old and new paths.
"""

import os
import re

def fix_imports(script_path):
    """Fix imports in a script."""
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Check for "from communities import" statements
    if 'from communities import' in content:
        # Add try/except block around imports
        fixed_content = re.sub(
            r'(from communities import [^;]+)',
            r'try:\n    \1\nexcept ImportError:\n    # Try with absolute import path\n    from app_data.scripts.communities.communities import \\1',
            content
        )
        
        # Write back to file
        with open(script_path, 'w') as f:
            f.write(fixed_content)
        
        print(f"Fixed imports in {script_path}")
    else:
        print(f"No import fixes needed in {script_path}")

def main():
    """Main function."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    community_dir = os.path.join(script_dir, 'communities')
    
    # Fix imports in .py files in the communities directory
    for filename in os.listdir(community_dir):
        if filename.endswith('.py'):
            fix_imports(os.path.join(community_dir, filename))

if __name__ == '__main__':
    main() 
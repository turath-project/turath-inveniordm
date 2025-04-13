"""
Chronicles Community Management Package.

This package provides functionality for creating and managing the Chronicles
community in InvenioRDM. It includes tools for community creation, verification,
and setup.

Available functions:
    - create_chronicles_community: Create a new Chronicles community
    - verify_community: Verify an existing community's configuration

Example:
    >>> from scripts.communities import create_chronicles_community, verify_community
    >>> community_id = create_chronicles_community()
    >>> if verify_community(community_id):
    ...     print("Community setup successful")
"""
from .create import create_chronicles_community
from .verify import verify_community

__all__ = [
    'create_chronicles_community',
    'verify_community',
]
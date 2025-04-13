"""
List All InvenioRDM Communities.

This script lists all communities in the InvenioRDM instance, showing their:
- ID
- Slug
- Title
- Description
- Access settings
- Creation date
- Available links

Usage:
    python scripts/list_communities.py

Returns:
    Prints community information and exits with status code 0 if successful, 1 if failed
"""

from invenio_app.factory import create_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities

def list_all_communities():
    """
    List all existing communities in the system.
    """
    app = create_app()
    
    with app.app_context():
        try:
            print("\n=== Listing All Communities ===\n")
            
            # Get the communities service
            community_service = current_communities.service
            
            # Search for all communities
            result = community_service.search(
                system_identity,
                params={
                    "size": 100,  # Adjust size as needed
                    "sort": "newest"
                }
            )
            
            # Print community details
            print(f"Total communities found: {result.total}\n")
            for hit in result.hits:
                print(f"ID: {hit['id']}")
                print(f"Slug: {hit.get('slug')}")
                print(f"Title: {hit.get('metadata', {}).get('title')}")
                print(f"Description: {hit.get('metadata', {}).get('description')}")
                print(f"Access: {hit.get('access')}")
                print(f"Created: {hit.get('created')}")
                print("Links:", hit.get('links', {}))
                print("-" * 80 + "\n")
                
        except Exception as e:
            print(f"Error listing communities: {e}")
            print(f"Error type: {type(e)}")
            return 1
            
        return 0

if __name__ == "__main__":
    exit(list_all_communities()) 
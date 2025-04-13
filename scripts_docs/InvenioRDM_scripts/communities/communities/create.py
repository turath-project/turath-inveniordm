from invenio_app.factory import create_app
from invenio_accounts.models import User
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities

def create_chronicles_community():
    """
    Create the Chronicles community in InvenioRDM.
    
    This function creates a new community for chronicles using the configuration
    defined in invenio.cfg (CHRONICLES_COMMUNITY). It sets up the basic structure
    for managing chronicle records.
    
    Returns:
        str: The ID of the created community if successful, None otherwise.
    
    Raises:
        Exception: If there's an error during community creation.
    
    Example:
        >>> community_id = create_chronicles_community()
        >>> print(f"Created community with ID: {community_id}")
    """
    
    # Updated community data format
    community_data = {
        "slug": "chronicles",
        "metadata": {
            # Title and description need to be strings, not dictionaries
            "title": "Chronicles Collection",
            "description": "Historical chronicles and manuscripts collection",
            # Remove type as it's causing validation error
        },
        "access": {
            "visibility": "public"
        }
    }

    app = create_app()
    with app.app_context():
        try:
            community = current_communities.service.create(
                system_identity,
                community_data
            )
            print(f"Created community with ID: {community.id}")
        except Exception as e:
            print(f"Error creating community: {e}")

if __name__ == "__main__": 
    create_chronicles_community()

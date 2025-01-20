from invenio_app.factory import create_app
from invenio_access.permissions import system_identity
from communities import create_chronicles_community, verify_community

def get_community_by_slug(slug):
    """
    Retrieve a community's ID using its slug.
    
    This function searches for a community in InvenioRDM using the provided slug
    and returns its ID if found.
    
    Args:
        slug (str): The slug/identifier of the community to find.
        
    Returns:
        str: The community ID if found, None otherwise.
        
    Raises:
        ValueError: If CHRONICLES_COMMUNITY configuration is not found.
    """
    app = create_app()
    with app.app_context():
        try:
            from invenio_communities.proxies import current_communities
            # Get the configuration
            config = app.config.get('CHRONICLES_COMMUNITY')
            if not config:
                raise ValueError("CHRONICLES_COMMUNITY configuration not found")
            
            # Search for the community
            search_result = current_communities.service.search(
                system_identity,
                params={"q": f"slug:{config['id']}"}
            )
            
            # Get the first result
            for hit in search_result.hits:
                return hit["id"]
            
            return None
            
        except Exception as e:
            print(f"Community not found: {e}")
            return None

def main():
    """
    Main setup function for the Chronicles community.
    
    This function orchestrates the setup process for the Chronicles community:
    1. Checks if the community already exists
    2. Creates it if it doesn't exist
    3. Verifies the community configuration
    
    The function uses the CHRONICLES_COMMUNITY configuration from invenio.cfg
    to ensure consistent community setup.
    
    Returns:
        None
    """
    print("Starting Chronicles setup...")
    
    # Get community by configured slug
    community_id = get_community_by_slug("chronicles")
    
    if community_id and verify_community(community_id):
        print("Chronicles community already exists!")
    else:
        print("Chronicles community not found, creating new one...")
        community_id = create_chronicles_community()
        if community_id:
            print(f"Verifying newly created community {community_id}...")
            verify_community(community_id)
        else:
            print("Failed to create community")

if __name__ == "__main__":
    main()
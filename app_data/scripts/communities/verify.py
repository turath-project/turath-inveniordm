from invenio_app.factory import create_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities

def verify_community(community_id):
    """
    Verify if a community exists and is properly configured.
    
    This function checks if a community exists in InvenioRDM and verifies its
    configuration. It attempts to read the community data and displays key
    information about the community.
    
    Args:
        community_id (str): The unique identifier of the community to verify.
        
    Returns:
        bool: True if community exists and is properly configured, False otherwise.
    
    Raises:
        Exception: If there's an error accessing the community data.
    
    Example:
        >>> success = verify_community("community-id-123")
        >>> if success:
        ...     print("Community verified successfully")
    """
    app = create_app()
    with app.app_context():
        try:
            # Try to read the community
            community = current_communities.service.read(
                system_identity,
                community_id
            )
            
            # Print verification details
            print("Community verification:")
            print(f"- ID: {community.id}")
            print(f"- Slug: {community.data.get('slug')}")
            print(f"- Title: {community.data.get('metadata', {}).get('title')}")
            print(f"- Description: {community.data.get('metadata', {}).get('description')}")
            
            return True
            
        except Exception as e:
            print(f"Error verifying community: {e}")
            return False

if __name__ == "__main__":
    # Example usage
    community_id = "ca106222-081b-47b3-b4e4-16859fffaddd"  # Replace with actual ID
    verify_community(community_id)
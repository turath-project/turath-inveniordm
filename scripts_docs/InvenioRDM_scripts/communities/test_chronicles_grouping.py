"""
Test Chronicles Community Grouping Mechanism.

This script tests whether InvenioRDM communities can effectively serve as a
grouping mechanism for the Chronicles initiative by:
1. Creating a test Chronicles community
2. Adding members to the community
3. Adding a sample manuscript record
4. Verifying the grouping functionality works as expected

Key concepts:
- Records in InvenioRDM have a parent-child relationship
- Community membership is stored at the parent record level
- The inclusion process uses InvenioRDM's request system
- Requests follow a create -> submit -> accept workflow

Usage:
    python scripts/test_chronicles_grouping.py

Returns:
    Prints test results and exits with status code 0 if successful, 1 if failed
"""

from invenio_app.factory import create_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_records_resources.proxies import current_service_registry
from invenio_accounts.proxies import current_datastore
import time
import inspect

def get_user_id(email):
    """Get user ID from email address."""
    try:
        user = current_datastore.get_user(email)
        if user:
            print(f"Found user: ID={user.id}, Email={user.email}, Active={user.active}")
            return str(user.id)
        else:
            print(f"\nCouldn't find user with email: {email}")
            return None
    except Exception as e:
        print(f"Error looking up user: {e}")
        print(f"Error type: {type(e)}")
        return None

def add_member_to_community(community_id, email, role="member"):
    """
    Add a user as a member to the Chronicles community.

    Args:
        community_id (str): UUID of the community to add member to
        email (str): Email address of the user to be added
        role (str, optional): Role to assign to the user. Defaults to "member".
                            Can be "owner", "manager", or "member"

    Returns:
        bool: True if user was added or is already a member, False if operation failed
    """
    try:
        print(f"\nLooking up user: {email}")
        user_id = get_user_id(email)
        if not user_id:
            print(f"❌ User not found: {email}")
            return False
            
        print(f"Found user ID: {user_id} for email: {email}")
        
        community_service = current_communities.service
        
        member_data = {
            "members": [{
                "type": "user",
                "id": user_id
            }],
            "role": role
        }
        
        print(f"Adding member with data: {member_data}")
        
        try:
            result = community_service.members.add(
                system_identity,
                community_id,
                member_data
            )
            print(f"✓ Added user {email} to community as {role}")
        except Exception as e:
            if 'AlreadyMemberError' in str(type(e)):
                print(f"✓ User {email} is already a member of the community")
                return True
            raise
            
        return True
        
    except Exception as e:
        print(f"Error adding member to community: {e}")
        print(f"Error type: {type(e)}")
        if hasattr(e, 'description'):
            print(f"Error description: {e.description}")
        return False

def create_test_manuscript_record(community_id):
    """
    Create and publish a test manuscript record in the Chronicles community.
    
    This function demonstrates the complete workflow for adding a record to a community:
    1. Create the initial draft record
    2. Create a community inclusion request
    3. Submit the request for review
    4. Accept the request (as an authorized user)
    5. Publish the record
    
    The community relationship is managed at the parent record level, which is
    automatically created during the process.
    
    Args:
        community_id (str): The UUID of the community to add the record to
        
    Returns:
        str: The ID of the created record if successful, None otherwise
    """
    record_service = current_service_registry.get("records")
    request_service = current_service_registry.get("requests")
    
    # Sample manuscript data with Arabic content
    manuscript_data = {
        "metadata": {
            "title": "مخطوطة تجريبية - Test Manuscript",
            "publication_date": "1850",
            "resource_type": {"id": "publication"},
            "creators": [
                {
                    "person_or_org": {
                        "name": "ابن خلدون",
                        "family_name": "خلدون",
                        "given_name": "ابن",
                        "type": "personal"
                    }
                }
            ],
            "languages": ["ara"],
            "description": "Test manuscript record for Chronicles community"
        },
        "access": {
            "record": "public",
            "files": "public",
            "status": "metadata-only"
        },
        "files": {
            "enabled": False
        }
    }
    
    try:
        # Step 1: Create the draft record
        print("\nCreating manuscript record...")
        draft = record_service.create(system_identity, manuscript_data)
        print(f"Draft created with ID: {draft.id}")
        
        # Step 2: Get the community-inclusion request type
        # This is a built-in request type that handles community membership
        request_type = request_service.request_type_registry._registered_types['community-inclusion']
        
        # Step 3: Create the community inclusion request
        print("\nCreating request...")
        request = request_service.create(
            identity=system_identity,
            data={
                "title": "Include manuscript in community",
                "description": "Request to include manuscript in the Chronicles community"
            },
            request_type=request_type,
            receiver={"community": community_id},  # The target community
            topic={"record": draft.id}            # The record to be included
        )
        print(f"Request created with ID: {request.id}")
        
        # Step 4: Submit the request for review
        print("\nSubmitting request...")
        submit_result = request_service.execute_action(system_identity, request.id, "submit")
        print(f"Request status after submit: {request_service.read(system_identity, request.id).data.get('status')}")
        
        # Step 5: Accept the request (this adds the record to the community)
        print("\nAccepting request...")
        accept_result = request_service.execute_action(system_identity, request.id, "accept")
        print(f"Request status after accept: {request_service.read(system_identity, request.id).data.get('status')}")
        
        # Step 6: Publish the record
        print("\nPublishing record...")
        record = record_service.publish(system_identity, draft.id)
        print(f"Record published with ID: {record.id}")
        
        # Optional: Try to reindex the record
        # This can help ensure the search index is up to date
        print("\nReindexing record...")
        try:
            record_service.indexer.index(record)
            print("Record reindexed")
        except Exception as e:
            print(f"Reindex error: {e}")
        
        # Wait for any async processing to complete
        import time
        print("\nWaiting for processing...")
        time.sleep(3)
        
        # Verify the final state
        record = record_service.read(system_identity, record.id)
        print("\nFinal record state:")
        print(f"Record ID: {record.id}")
        print(f"Record revision: {record.data.get('revision_id')}")
        print(f"Communities: {record.data.get('communities', {})}")
        print(f"Parent ID: {record.data.get('parent', {}).get('id')}")
        
        # Check the parent record's community information
        parent_id = record.data.get('parent', {}).get('id')
        if parent_id:
            print(f"\nParent record ID: {parent_id}")
            print(f"Parent data from child record:")
            parent_data = record.data.get('parent', {})
            print(f"Parent communities: {parent_data.get('communities', {})}")
            
            # Note: Direct parent record access might not be available
            # The parent data is already included in the child record
            # so we don't need to query it separately
        
        return record.id
        
    except Exception as e:
        print(f"\nError creating/publishing manuscript record:")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        if hasattr(e, 'description'):
            print(f"Error description: {e.description}")
        return None

def verify_manuscript_in_community(community_id, record_id):
    """
    Verify that a manuscript record is properly grouped in the Chronicles community.
    
    In InvenioRDM, community membership can be found in two places:
    1. Directly in the record's communities field
    2. In the parent record's communities field (more common)
    
    This function checks both locations to verify membership.
    
    Args:
        community_id (str): The UUID of the community to check
        record_id (str): The ID of the record to verify
        
    Returns:
        bool: True if record is in the community, False otherwise
    """
    record_service = current_service_registry.get("records")
    
    try:
        record = record_service.read(system_identity, record_id)
        print(f"\nVerifying record {record_id}:")
        print(f"Communities data: {record.data.get('communities', {})}")
        print(f"Parent data: {record.data.get('parent', {})}")
        
        # Check direct communities (less common)
        communities = record.data.get("communities", {})
        if communities.get("ids") and community_id in communities["ids"]:
            print(f"✓ Found community {community_id} in record's communities")
            return True
            
        # Check parent communities (more common)
        parent_data = record.data.get("parent", {})
        parent_communities = parent_data.get("communities", {})
        if parent_communities.get("ids") and community_id in parent_communities["ids"]:
            print(f"✓ Found community {community_id} in parent's communities")
            return True
            
        print(f"✗ Community {community_id} not found in record's or parent's communities")
        return False
        
    except Exception as e:
        print(f"Error verifying record: {e}")
        print(f"Error type: {type(e)}")
        return False

def main():
    """Execute the Chronicles community grouping test."""
    app = create_app()
    
    with app.app_context():
        print("\n=== Testing Chronicles Community Grouping ===\n")
        
        # Get existing community ID from config
        config = app.config.get('CHRONICLES_COMMUNITY')
        if not config:
            print("❌ CHRONICLES_COMMUNITY configuration not found")
            return 1
            
        community_slug = config.get('id')
        print(f"Using Chronicles community slug: {community_slug}")
        
        # Get the actual community ID
        try:
            community_service = current_communities.service
            community = community_service.read(system_identity, community_slug)
            community_id = community.id
            print(f"Found community: {community_id}")
        except Exception as e:
            print(f"❌ Error accessing community: {e}")
            return 1
        
        # Add members to the community
        print("\nAdding members to Chronicles community...")
        members_to_add = [
            ("admin@turath.com", "owner"),
        ]
        
        for email, role in members_to_add:
            if not add_member_to_community(community_id, email, role):
                print(f"❌ Failed to add member {email}")
                return 1
        
        # Create test manuscript
        print("\nCreating test manuscript record...")
        record_id = create_test_manuscript_record(community_id)
        if not record_id:
            print("❌ Failed to create test manuscript")
            return 1
        print(f"✓ Created manuscript record: {record_id}")
        
        # Verify grouping
        print("\nVerifying manuscript grouping...")
        if verify_manuscript_in_community(community_id, record_id):
            print("✓ Manuscript successfully grouped in Chronicles community")
        else:
            print("❌ Failed to verify manuscript in community")
            return 1
            
        print("\n✓ All tests passed successfully!")
        return 0

if __name__ == "__main__":
    exit(main())
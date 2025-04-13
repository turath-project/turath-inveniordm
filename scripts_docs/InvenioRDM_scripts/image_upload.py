"""Test script for uploading a single image with IIIF support."""

import click
from invenio_rdm_records.proxies import current_rdm_records_service
from flask import current_app
import os
import subprocess
from invenio_rdm_records.records.processors.tiles import TilesProcessor
from invenio_records_resources.services.uow import UnitOfWork, RecordCommitOp
from invenio_records_resources.services.files.processors.image import ImageMetadataExtractor
import shutil
from invenio_accounts.models import User
from invenio_access.utils import get_identity
from invenio_files_rest.models import Location

def do_upload_image(image_path, test_mode=False):
    """Upload a single test image and publish the record."""
    
    result = {
        "success": False,
        "record_id": None,
        "error": None
    }
    
    try:
        # Check location status
        location = Location.query.filter_by(default=True).first()
        if test_mode:
            print(f"\nUsing file location: {location.uri}")
            print(f"Location name: {location.name}")
            print(f"Location ID: {location.id}\n")
        else:
            click.echo(f"\nUsing file location: {location.uri}")
            click.echo(f"Location name: {location.name}")
            click.echo(f"Location ID: {location.id}\n")
        
        # Get admin user identity
        user = User.query.filter_by(email='admin@turath.com').first()
        if not user:
            msg = "Admin user not found! Please create the admin user first."
            if test_mode:
                result["error"] = msg
                return result
            else:
                click.echo(msg)
                return
        
        identity = get_identity(user)
        
        # Prepare metadata with required fields
        metadata = {
            "metadata": {
                "title": "Test Image for IIIF",
                "creators": [
                    {
                        "person_or_org": {
                            "family_name": "Test",
                            "given_name": "User",
                            "type": "personal"
                        }
                    }
                ],
                "resource_type": {"id": "image"},
                "publication_date": "2024-03-22",
                "dates": [
                    {
                        "date": "2024-03-22",
                        "type": {
                            "id": "available"
                        }
                    }
                ]
            },
            "access": {
                "record": "public",
                "files": "public"
            }
        }

        # Create a draft record
        draft = current_rdm_records_service.create(
            identity=identity,
            data=metadata
        )
        
        # Upload the file
        with open(image_path, "rb") as file:
            current_rdm_records_service.draft_files.init_files(
                identity=identity,
                id_=draft.id,
                data=[{"key": os.path.basename(image_path)}]
            )
            
            current_rdm_records_service.draft_files.set_file_content(
                identity=identity,
                id_=draft.id,
                file_key=os.path.basename(image_path),
                stream=file,
            )
            
            current_rdm_records_service.draft_files.commit_file(
                identity=identity,
                id_=draft.id,
                file_key=os.path.basename(image_path),
            )

        # After publishing, generate tiles
        def generate_tiles(record_id):
            """Generate IIIF tiles for the record."""
            with UnitOfWork() as uow:
                record = current_rdm_records_service.record_cls.pid.resolve(record_id)
                
                # Get the instance path for IIIF directory
                instance_path = current_app.instance_path
                iiif_dir = os.path.join(instance_path, 'data', 'iiif', '3', record_id)
                click.echo(f"\nCreating IIIF directory: {iiif_dir}")
                os.makedirs(iiif_dir, exist_ok=True)
                
                # Copy the original file to IIIF directory
                source_file = record.files[os.path.basename(image_path)].file.uri
                dest_file = os.path.join(iiif_dir, os.path.basename(image_path))
                click.echo(f"Copying file from {source_file} to {dest_file}")
                shutil.copy2(source_file, dest_file)
                
                # Generate tiles
                processor = TilesProcessor()
                processor(None, record, uow=uow)
                uow.register(RecordCommitOp(record))
                
                # Extract image metadata
                image_metadata_extractor = ImageMetadataExtractor()
                for file_record in record.files.values():
                    if image_metadata_extractor.can_process(file_record):
                        image_metadata_extractor.process(file_record)
                        file_record.commit()
                
                uow.commit()
                return record

        # Publish the record
        published_record = current_rdm_records_service.publish(
            identity=identity,
            id_=draft.id
        )
        click.echo(f"Record published with ID: {published_record.id}")
        click.echo(f"Access the record at: {current_app.config['SITE_UI_URL']}/records/{published_record.id}")

        # Generate tiles
        record_with_tiles = generate_tiles(published_record.id)
        
        # Debug checks
        def debug_file_locations(record_id, filename):
            """Debug helper to check file locations."""
            click.echo("\nDebug Information:")
            click.echo("-----------------")
            click.echo(f"Record ID: {record_id}")
            click.echo(f"Filename: {filename}")
            
            # Check IIIF storage path
            expected_path = f"/images/public/3/{record_id}/{filename}"
            click.echo(f"\nExpected IIIF path: {expected_path}")
            
            # Check if file exists in container
            cmd = f"docker-compose exec iipserver ls -la /images/public/3/{record_id}/"
            click.echo("\nChecking files in IIIF container:")
            subprocess.run(cmd, shell=True)
            
            # Check tile generation status
            click.echo("\nChecking tile generation status:")
            record = current_rdm_records_service.record_cls.pid.resolve(record_id)
            if record.media_files.enabled:
                tile_file = record.media_files.get(f"{filename}.ptif")
                if tile_file and tile_file.processor:
                    click.echo(f"Tile status: {tile_file.processor.get('status')}")
                else:
                    click.echo("No tile processing information found")
            else:
                click.echo("Media files not enabled for this record")

        debug_file_locations(published_record.id, os.path.basename(image_path))

        # For testing, let's return success and record ID
        if test_mode:
            # Normally you would set record_id to the actual ID from the created record
            result["success"] = True
            result["record_id"] = published_record.id
            return result
        else:
            # For CLI, just print success
            click.echo("Record created successfully!")
            return
            
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        if test_mode:
            result["error"] = error_msg
            return result
        else:
            click.echo(error_msg)
            return

@click.command()
@click.argument('image_path', type=click.Path(exists=True))
def upload_test_image(image_path):
    """Upload a single test image and publish the record."""
    return do_upload_image(image_path)

if __name__ == "__main__":
    upload_test_image() 
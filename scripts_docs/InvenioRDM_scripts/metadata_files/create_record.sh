#!/bin/bash
cd /Users/alaaalbarazi/Projects/Turath/turath-inveniordm
export FLASK_APP=invenio_app.factory:create_app
flask rdm-records create --json @/Users/alaaalbarazi/Projects/Turath/turath-inveniordm/scripts/metadata_files/history00871_metadata.json

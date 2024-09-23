# В вашем модуле views.py
from flask import Blueprint, jsonify
from invenio_records_resources.proxies import current_service

blueprint = Blueprint('iiif_manifest', __name__)

@blueprint.route('/iiif/manifest/<record_id>')
def manifest(record_id):
    # Получите запись по record_id
    record = current_service.read(id_=record_id, identity=g.identity)
    # Сформируйте манифест на основе данных записи
    manifest = {
        "@context": "http://iiif.io/api/presentation/2/context.json",
        "@id": f"https://your.domain/iiif/manifest/{record_id}",
        "@type": "sc:Manifest",
        "label": record["metadata"]["title"],
        "sequences": [
            {
                "@type": "sc:Sequence",
                "canvases": []
            }
        ]
    }

    # Добавьте канвасы на основе файлов записи
    for idx, file_metadata in enumerate(record["files"]["entries"].values(), start=1):
        file_url = file_metadata["links"]["self"]
        canvas = {
            "@id": f"https://your.domain/iiif/manifest/{record_id}/canvas/{idx}",
            "@type": "sc:Canvas",
            "label": file_metadata["key"],
            "width": 800,  # Замените на реальные размеры
            "height": 1000,
            "images": [
                {
                    "@type": "oa:Annotation",
                    "motivation": "sc:painting",
                    "resource": {
                        "@id": file_url,
                        "@type": "dctypes:Image",
                        "format": file_metadata["mimetype"],
                        "width": 800,
                        "height": 1000,
                    },
                    "on": f"https://your.domain/iiif/manifest/{record_id}/canvas/{idx}"
                }
            ]
        }
        manifest["sequences"][0]["canvases"].append(canvas)

    return jsonify(manifest)

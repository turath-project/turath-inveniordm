"""Facets configuration for Turath."""

from invenio_rdm_records.config import RDM_FACETS, RDM_SEARCH
from invenio_records_resources.services.records.facets import CFTermsFacet
from invenio_i18n import lazy_gettext as _

RDM_FACETS = {
    **RDM_FACETS,
    "script_type": {
        "facet": CFTermsFacet(
            field="turath:script_type.id",
            label=_("Script Type"),
        ),
        "ui": {
            "field": CFTermsFacet.field("turath:script_type.id"),
        },
    },
    "publisher": {
        "facet": CFTermsFacet(
            field="turath:publisher",
            label=_("Publisher"),
        ),
        "ui": {
            "field": CFTermsFacet.field("turath:publisher"),
        },
    },
}

RDM_SEARCH = {
    **RDM_SEARCH,
    "facets": RDM_SEARCH["facets"] + ["script_type", "publisher"]
}

# Also print the complete RDM_FACETS for debugging
print("\nComplete RDM_FACETS:", RDM_FACETS)
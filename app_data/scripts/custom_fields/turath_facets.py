"""Facets configuration for Turath."""

from invenio_rdm_records.config import RDM_FACETS, RDM_SEARCH
from invenio_records_resources.services.records.facets import CFTermsFacet
from invenio_i18n import lazy_gettext as _

RDM_FACETS = {
    **RDM_FACETS,
    # VocabularyCF fields
    "script_type": {
        "facet": CFTermsFacet(
            field="turath:script_type.id",
            label=_("Script Type"),
        ),
        "ui": {
            "field": CFTermsFacet.field("turath:script_type.id"),
        },
    },
    "creator": {
        "facet": CFTermsFacet(
            field="turath:creator.id",
            label=_("Creator"),
        ),
        "ui": {
            "field": CFTermsFacet.field("turath:creator.id"),
        },
    },
    "contributor": {
        "facet": CFTermsFacet(
            field="turath:contributor.id",
            label=_("Contributor"),
        ),
        "ui": {
            "field": CFTermsFacet.field("turath:contributor.id"),
        },
    },
    "language": {
        "facet": CFTermsFacet(
            field="turath:language.id",
            label=_("Language"),
        ),
        "ui": {
            "field": CFTermsFacet.field("turath:language.id"),
        },
    },
    "format": {
        "facet": CFTermsFacet(
            field="turath:format.id",
            label=_("Format"),
        ),
        "ui": {
            "field": CFTermsFacet.field("turath:format.id"),
        },
    },
    "resource_type": {
        "facet": CFTermsFacet(
            field="turath:resource_type.id",
            label=_("Resource Type"),
        ),
        "ui": {
            "field": CFTermsFacet.field("turath:resource_type.id"),
        },
    },
    
    # KeywordCF fields
    "publisher": {
        "facet": CFTermsFacet(
            field="turath:publisher",
            label=_("Publisher"),
        ),
        "ui": {
            "field": CFTermsFacet.field("turath:publisher"),
        },
    },
    "creator_arabic": {
        "facet": CFTermsFacet(
            field="turath:creator_arabic",
            label=_("Creator (Arabic)"),
        ),
        "ui": {
            "field": CFTermsFacet.field("turath:creator_arabic"),
        },
    },
    
    # TextCF fields
    "alternative_title": {
        "facet": CFTermsFacet(
            field="turath:alternative_title.keyword",
            label=_("Alternative Title"),
        ),
        "ui": {
            "field": CFTermsFacet.field("turath:alternative_title"),
        },
    },
    "identifier": {
        "facet": CFTermsFacet(
            field="turath:identifier.keyword",
            label=_("Identifier"),
        ),
        "ui": {
            "field": CFTermsFacet.field("turath:identifier"),
        },
    }
}

RDM_SEARCH = {
    **RDM_SEARCH,
    "facets": RDM_SEARCH["facets"] + [
        "script_type",
        "creator",
        "contributor",
        "language",
        "format",
        "resource_type",
        "publisher",
        "creator_arabic",
        "alternative_title",
        "identifier"
    ]
}

# Also print the complete RDM_FACETS for debugging
print("\nComplete RDM_FACETS:", RDM_FACETS)
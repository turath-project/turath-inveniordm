from invenio_i18n import lazy_gettext as _
from invenio_records_resources.services.custom_fields import (
    TextCF,
    KeywordCF,
    ISODateStringCF,
    EDTFDateStringCF,
    BooleanCF
)
from invenio_vocabularies.services.custom_fields import VocabularyCF
from marshmallow_utils.fields import SanitizedHTML, SanitizedUnicode
from marshmallow import validate
from invenio_records_resources.services.records.facets import CFTermsFacet
from invenio_rdm_records.config import RDM_FACETS, RDM_SEARCH

# Add at the top of the file with other imports
from datetime import datetime

def validate_w3cdtf_date(value):
    """
    Validate date string according to W3CDTF/ISO 8601 format (YYYY-MM-DD).
    Also accepts just YYYY or YYYY-MM.
    """
    if not value:
        return True  # Empty values are handled by required field validation
        
    try:
        # Handle different levels of precision
        if len(value) == 4:  # YYYY
            datetime.strptime(value, '%Y')
        elif len(value) == 7:  # YYYY-MM
            datetime.strptime(value, '%Y-%m')
        elif len(value) == 10:  # YYYY-MM-DD
            datetime.strptime(value, '%Y-%m-%d')
        else:
            return False
        return True
    except ValueError:
        return False
    
# Define namespace
RDM_NAMESPACES = {
    "turath": "https://turath.org/terms/"
}

# Define the Alternative Title field
RDM_CUSTOM_FIELDS = [
    
    # 1. Title
    TextCF(
        name="turath:title",
        field_cls=SanitizedUnicode,
        use_as_filter=True,
        field_args={
            # "required": True,  # Temporarily disabled for testing
            "error_messages": {
                "required": "Title is required"
            },
            "description": "Capitalize the first letter of the first word. Record punctuation as it appears in the resource. Do not use abbreviations."
        }
    ),

    # 2. Title-Alternative
    TextCF(
        name="turath:alternative_title",
        use_as_filter=True,
        field_args={
            "required": False,
            "description": "Required for Arabic script titles. Use ALA-LC for transliterations."
        },
        multiple=True
    ),
    VocabularyCF(
        name="turath:alternative_title_script",
        vocabulary_id="title_scripts",
        dump_options=True,
        multiple=False
    ),

    # 3. Creator
    VocabularyCF(
        name="turath:creator",
        vocabulary_id="creators",
        multiple=True,
        dump_options=False,
        field_args={
            # "required": True,  # Temporarily disabled for testing
            "description": "Personal names, group, or organizations"
        }
    ),
    KeywordCF(
        name="turath:creator_arabic",
        multiple=True,
        field_args={
            "description": "Creator name in Arabic script"
        }
    ),

    # 4. Contributor
    VocabularyCF(
        name="turath:contributor",
        vocabulary_id="contributors",
        multiple=True,
        dump_options=False,
        field_args={
            "description": "Secondary authors, editors, etc. Required for oral histories."
        }
    ),
    KeywordCF(
        name="turath:contributor_arabic",
        multiple=True,
        field_args={
            "description": "Contributor name in Arabic script"
        }
    ),
    VocabularyCF(
        name="turath:contributor_type",
        vocabulary_id="contributor_types",
        multiple=False,
        dump_options=True,
        field_args={
            "description": "Role of the contributor (e.g., editor, illustrator, transcriber)"
        }
    ),

    # 5. Publisher
    KeywordCF(
        name="turath:publisher",
        multiple=True,
        field_args={
            # "required": True,  # Temporarily disabled for testing
            "description": "Organization or corporate entity responsible for publication"
        }
    ),

    # 6-7. Date and Date-Issued
    TextCF(
        name="turath:date",
        field_cls=SanitizedUnicode,
        field_args={
            # "required": True,  # Temporarily disabled for testing
            "validate": validate_w3cdtf_date,
            "error_messages": {
                "invalid": "Date must be in YYYY-MM-DD format"
            }
        }
    ),
    EDTFDateStringCF(
        name="turath:date_issued",
        field_args={
            "required": False,
        }
    ),
    VocabularyCF(
        name="turath:date_type",
        vocabulary_id="date_types",
        multiple=False,
        dump_options=True,
        field_args={
            "description": "Type of date (created, modified, issued, etc.)"
        }
    ),

    # 8. Subject
    VocabularyCF(
        name="turath:subject",
        vocabulary_id="subjects",
        multiple=True,
        dump_options=False,
        field_args={
            "description": "Topics covered by the resource"
        }
    ),

    # 9. Description
    TextCF(
        name="turath:description",
        # field_cls=SanitizedHTML,
        multiple=True,
        field_args={
            "required": False, # fix later 
            "description": "Full description of the resource. Include abstract, table of contents, etc."
        }
    ),
    VocabularyCF(
        name="turath:description_type",
        vocabulary_id="description_types",
        dump_options=True,
        multiple=False,
        field_args={
            "description": "Type of description"
        }
    ),

    # 10. Type
    VocabularyCF(
        name="turath:resource_type",
        vocabulary_id="resourcetypes",
        dump_options=True,
        multiple=False,
        field_args={
            "description": "General nature or genre of the resource"
        }
    ),

    # 11. Format
    VocabularyCF(
        name="turath:format",
        vocabulary_id="formats",
        dump_options=True,
        multiple=True,
        field_args={
            # "required": True,  # Temporarily disabled for testing
            "description": "File format or physical medium"
        }
    ),
    TextCF(
        name="turath:format_extent",
        field_cls=SanitizedUnicode,
        field_args={
            "description": "Size or duration of the resource"
        }
    ),

    # 12. Identifier
    TextCF(
        name="turath:identifier",
        field_cls=SanitizedUnicode,
        multiple=True,
        field_args={
            # "required": True,  # Temporarily disabled for testing
            "description": "For digital objects: include filename with extension. Enter multiple identifiers in order of importance."
        }
    ),

    # 13. Source
    TextCF(
        name="turath:source",
        field_cls=SanitizedUnicode,
        multiple=True,
        field_args={
            "description": "Original source information (pre-digitization details)"
        }
    ),

    # 14. Language
    VocabularyCF(
        name="turath:language",
        vocabulary_id="languages",
        multiple=True,
        dump_options=False,
        field_args={
            # "required": True,  # Temporarily disabled for testing
            "description": "Languages used in the resource (ISO 639-2 codes)"
        }
    ),

    # 15. Coverage-Temporal
    TextCF(
        name="turath:coverage_temporal_start",
        field_cls=SanitizedUnicode,
        field_args={
            "validate": validate_w3cdtf_date,
            "error_messages": {
                "invalid": "Date must be in YYYY-MM-DD format"
            },
            "description": "Start date of the time period covered in the content"
        }
    ),
    TextCF(
        name="turath:coverage_temporal_end",
        field_cls=SanitizedUnicode,
        field_args={
            "validate": validate_w3cdtf_date,
            "error_messages": {
                "invalid": "Date must be in YYYY-MM-DD format"
            },
            "description": "End date of the time period covered in the content"
        }
    ),

    #16. Coverage-Spatial
    VocabularyCF(
        name="turath:coverage_spatial",
        vocabulary_id="places",
        multiple=True,
        dump_options=False,
        field_args={
            "description": "Geographic areas covered by the content"
        }
    ),
    TextCF(
        name="turath:geolocation_point",
        field_cls=SanitizedUnicode,
        field_args={
            "description": "Precise geographic coordinates"
        }
    ),

    # 17. Relation
    VocabularyCF(
        name="turath:relation_type",
        vocabulary_id="relationtypes",
        multiple=False,
        dump_options=True,
        field_args={
            # "required": True,  # Temporarily disabled for testing
            "description": "Type of relationship to other resources"
        }
    ),
    TextCF(
        name="turath:relation_identifier",
        field_cls=SanitizedUnicode,
        field_args={
            "description": "Identifier of the related resource"
        }
    ),
    TextCF(
        name="turath:bibliographic_citation",
        field_cls=SanitizedHTML,
        multiple=True,
        field_args={
            "description": "Bibliographic reference for the resource"
        }
    ),

    # 18. Rights
    VocabularyCF(
        name="turath:rights",
        vocabulary_id="licenses",
        multiple=False,
        dump_options=True,
        field_args={
            # "required": True,  # Temporarily disabled for testing
            "description": "Rights and access information"
        }
    ),
    TextCF(
        name="turath:rights_uri",
        field_cls=SanitizedUnicode,
        field_args={
            "description": "URL to rights statement"
        }
    ),
    TextCF(
        name="turath:rights_identifier",
        field_cls=SanitizedUnicode,
        field_args={
            "description": "Standardized rights identifier"
        }
    ),

    # 20. Script Type
    VocabularyCF(
        name="turath:script_type",
        vocabulary_id="script_types",
        dump_options=True,
        multiple=False
    ),
    VocabularyCF(
        name="turath:alternative_title_script",
        vocabulary_id="title_scripts",
        dump_options=True,
        multiple=False
    )
]

# Define UI Configuration
RDM_CUSTOM_FIELDS_UI = [
    # 1. Title Section
    {
        "section": "Title Information",
        "fields": [
            dict(
                field="turath:title",
                ui_widget="Input",
                props=dict(
                    label="Title",
                    placeholder="Enter the main title. Capitalize first word, keep original punctuation",
                    icon="header",
                    description="Primary title of the resource. Capitalize the first letter of the first word. Record punctuation as it appears in the resource. Do not use abbreviations.",
                    required=False
                )
            ),
            dict(
                field="turath:alternative_title",
                ui_widget="MultiInput",
                props=dict(
                    label="Alternative Title",
                    placeholder="Enter Arabic title or transliteration (ALA-LC)",
                    icon="header",
                    description="Required for non-Latin (Arabic) script titles",
                    help_text="Capitalize first letter. Record punctuation as it appears. No abbreviations."
                )
            ),
            dict(
                field="turath:alternative_title_script",
                ui_widget="Dropdown",
                props=dict(
                    label="Alternative Title Script",
                    placeholder="Select script",
                    icon="language",
                    vocabularyType="title_scripts",
                    search=False,
                    multiple=False,
                    clearable=True
                )
            )
        ]
    },

    # 2. Authorship Section
    {
        "section": "Authorship",
        "fields": [
            dict(
                field="turath:creator",
                ui_widget="AutocompleteDropdown",
                props=dict(
                    label="Creator",
                    placeholder="Last Name, First Name, Middle Name [YYYY-YYYY]",
                    icon="user",
                    description="Enter name in LCNAF format if available. For oral histories, enter interviewee.",
                    help_text="If name cannot be verified in LCNAF, enter it as it appears without inversion. Include birth/death dates for common names.",
                    multiple=True,
                    search=True,
                    required=False
                )
            ),
            dict(
                field="turath:creator_arabic",
                ui_widget="MultiInput",
                props=dict(
                    label="Creator (Arabic)",
                    placeholder="Last element of name, First Name",
                    icon="user",
                    description="Enter creator's name in Arabic script",
                    help_text="To consistently identify Last Name, use last element in name"
                )
            ),
            dict(
                field="turath:contributor",
                ui_widget="AutocompleteDropdown",
                props=dict(
                    label="Contributor",
                    placeholder="Last Name, First Name, Middle Name [role]",
                    icon="users",
                    description="Secondary contributors (LCNAF format). Required for oral histories (interviewer)",
                    help_text="If name cannot be verified in LCNAF, enter it as it appears. Do not abbreviate organization names.",
                    multiple=True,
                    search=True
                )
            ),
            dict(
                field="turath:contributor_arabic",
                ui_widget="MultiInput",
                props=dict(
                    label="Contributor (Arabic)",
                    placeholder="Last element of name, First Name",
                    icon="users",
                    description="Enter contributor's name in Arabic script",
                    help_text="To consistently identify Last Name, use last element in name"
                )
            ),
            dict(
                field="turath:contributor_type",
                ui_widget="Dropdown",
                props=dict(
                    label="Contributor Role",
                    placeholder="Select contributor role",
                    icon="user",
                    vocabularyType="contributor_types",
                    description="Role of the contributor",
                    search=False,
                    multiple=False,
                    clearable=True
                )
            )
        ]
    },

    # 3. Publication Information
    {
        "section": "Publication Information",
        "fields": [
            dict(
                field="turath:publisher",
                ui_widget="MultiInput",
                props=dict(
                    label="Publisher",
                    placeholder="Enter publishing organization or service",
                    icon="building",
                    description="Organization responsible for publication. May repeat Creator if same.",
                    required=False
                )
            ),
            dict(
                field="turath:date",
                ui_widget="Input",
                props=dict(
                    label="Date",
                    placeholder="YYYY-MM-DD",
                    icon="calendar",
                    description="Primary date associated with the resource. Not for temporal coverage.",
                    required=False
                )
            ),
            dict(
                field="turath:date_issued",
                ui_widget="Input",
                props=dict(
                    label="Date Issued",
                    placeholder="YYYY-MM-DD",
                    icon="calendar",
                    description="Publication or issuance date"
                )
            ),
            dict(
                field="turath:date_type",
                ui_widget="Dropdown",
                props=dict(
                    label="Date Type",
                    placeholder="Select date type",
                    icon="calendar",
                    vocabularyType="date_types",
                    description="Type of date",
                    search=False,
                    multiple=False,
                    clearable=True
                )
            )
        ]
    },

    # 4. Content Description
    {
        "section": "Content Description",
        "fields": [
            dict(
                field="turath:subject",
                ui_widget="AutocompleteDropdown",
                props=dict(
                    label="Subject",
                    placeholder="Select or enter subjects",
                    icon="tags",
                    description="Topics covered by the resource",
                    multiple=True,
                    search=True
                )
            ),
            dict(
                field="turath:description",
                ui_widget="RichInput",
                props=dict(
                    label="Description",
                    placeholder="Enter full description in complete sentences",
                    icon="align left",
                    description="Detailed description of the resource. Preferred in both English and Arabic.",
                    required=False# fix this 
                )
            ),
            dict(
                field="turath:description_type",
                ui_widget="Dropdown",
                props=dict(
                    label="Description Type",
                    placeholder="Select description type",
                    icon="file text",
                    vocabularyType="description_types",
                    description="e.g., Abstract, Table of Contents",
                    search=False,
                    multiple=False,
                    clearable=True
                )
            ),
            dict(
                field="turath:resource_type",
                ui_widget="Dropdown",
                props=dict(
                    label="Resource Type",
                    placeholder="Select resource type",
                    icon="file",
                    vocabularyType="resourcetypes",
                    description="General nature or genre (e.g., text, image, sound). Not physical format.",
                    search=False,
                    multiple=False,
                    clearable=True
                )
            )
        ]
    },

    # 5. Technical Information
    {
        "section": "Technical Information",
        "fields": [
            dict(
                field="turath:format",
                ui_widget="Dropdown",
                props=dict(
                    label="Format",
                    placeholder="Select format",
                    icon="file",
                    vocabularyType="formats",
                    description="File format or physical medium. Repeat for multiple formats.",
                    search=False,
                    multiple=True,
                    required=False,
                    clearable=True
                )
            ),
            dict(
                field="turath:format_extent",
                ui_widget="Input",
                props=dict(
                    label="Extent",
                    placeholder="e.g., '3 pages' or '10 MB' or '1:30:00'",
                    icon="resize horizontal",
                    description="Size or duration of the resource"
                )
            ),
            dict(
                field="turath:identifier",
                ui_widget="MultiInput",
                props=dict(
                    label="Identifier",
                    placeholder="filename.ext or DOI/URI/URL/ISBN",
                    icon="barcode",
                    description="For digital objects: enter filename with extension. Include identifiers in order of importance.",
                    help_text="Use separate entries for different identifier schemas (DOI, URI, URL, ISBN)",
                    required=False
                )
            )
        ]
    },

    # 6. Source and Language
    {
        "section": "Source and Language",
        "fields": [
            dict(
                field="turath:source",
                ui_widget="Input",
                props=dict(
                    label="Source",
                    placeholder="Enter pre-digitization details",
                    icon="book",
                    description="For digital objects: include genre, collection, box, folder information. Not for born-digital objects.",
                    help_text="For citational information use bibliographicCitation. For relationships use Relation element."
                )
            ),
            dict(
                field="turath:language",
                ui_widget="AutocompleteDropdown",
                props=dict(
                    label="Language",
                    placeholder="Select languages (e.g., ara, eng, tur, ota)",
                    icon="language",
                    description="Use ISO 639-2 codes. Separate multiple languages with semicolon and space.",
                    help_text="For textual descriptions of the language, use Description field.",
                    multiple=True,
                    search=True,
                    required=False
                )
            )
        ]
    },

    # 7. Coverage
    {
        "section": "Coverage",
        "fields": [
            dict(
                field="turath:coverage_spatial",
                ui_widget="AutocompleteDropdown",
                props=dict(
                    label="Spatial Coverage",
                    placeholder="Select or enter places",
                    icon="globe",
                    vocabularyType="places",
                    description="Geographic areas covered by the content. Not for publication place.",
                    multiple=True,
                    search=True
                )
            ),
            dict(
                field="turath:coverage_temporal_start",
                ui_widget="Input",
                props=dict(
                    label="Temporal Coverage (Start)",
                    placeholder="YYYY-MM-DD",
                    icon="calendar",
                    description="Start date of the time period covered in the content. Not for publication dates."
                )
            ),
            dict(
                field="turath:coverage_temporal_end",
                ui_widget="Input",
                props=dict(
                    label="Temporal Coverage (End)",
                    placeholder="YYYY-MM-DD",
                    icon="calendar",
                    description="End date of the time period covered in the content. Not for publication dates."
                )
            )
        ]
    },

    # 8. Relations
    {
        "section": "Relations",
        "fields": [
            dict(
                field="turath:relation_type",
                ui_widget="Dropdown",
                props=dict(
                    label="Relation Type",
                    placeholder="Select relation type",
                    icon="sitemap",
                    vocabularyType="relationtypes",
                    search=False,
                    multiple=False,
                    clearable=True
                )
            ),
            dict(
                field="turath:relation_identifier",
                ui_widget="Input",
                props=dict(
                    label="Related Resource Identifier",
                    placeholder="Enter identifier of related resource",
                    icon="linkify",
                    description="Identifier of the related resource"
                )
            ),
            dict(
                field="turath:bibliographic_citation",
                ui_widget="RichInput",
                props=dict(
                    label="Bibliographic Citation",
                    placeholder="Enter citation",
                    icon="quote right",
                    description="How to cite this resource"
                )
            )
        ]
    },
    # 9. Rights
    {
        "section": "Rights",
        "fields": [
            dict(
                field="turath:rights",
                ui_widget="Dropdown",
                props=dict(
                    label="License",
                    placeholder="Select license",
                    icon="copyright",
                    description="License or rights statement",
                    vocabularyType="licenses",
                    search=False,
                    multiple=False,
                    clearable=True
                )
            ),
            dict(
                field="turath:rights_uri",
                ui_widget="Input",
                props=dict(
                    label="License URL",
                    placeholder="https://creativecommons.org/licenses/...",
                    icon="linkify",
                    description="URL of the license"
                )
            ),
            dict(
                field="turath:rights_identifier",
                ui_widget="Input",
                props=dict(
                    label="License Identifier",
                    placeholder="e.g., CC-BY-4.0",
                    icon="id card",
                    description="Standardized license identifier"
                )
            )
        ]
    },

    # 10. Script Type
    {
        "section": "Script Type",
        "fields": [
            dict(
                field="turath:script_type",
                ui_widget="Dropdown",
                props=dict(
                    label="Script Type",
                    placeholder="Select script type",
                    icon="font",
                    vocabularyType="script_types",
                    search=False,
                    multiple=False,
                    clearable=True
                )
            )
        ]
    }
]
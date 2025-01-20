"""
Metadata facts and mapping rules for Turath.
Contains Dublin Core to DataCite mapping information and metadata rules.
"""

RDM_FACTS = {
    "title": {
        "datacite": "Title",
        "dublin_core": "dcterms:title",
        "obligation": "required",
        "repeatable": False,
        "encoding_scheme": "Plain text",
        "best_practices": [
            "Capitalize first letter of first word",
            "Record punctuation as it appears",
            "Do not use abbreviations"
        ]
    },
    "alternative_title": {
        "datacite": "Title/titleType",
        "dublin_core": "dcterms:alternative",
        "obligation": "required_if_applicable",
        "repeatable": True,
        "encoding_scheme": ["Plain text", "ALA-LC Romanization Table"],
        "best_practices": [
            "Required for Arabic script titles",
            "Optional for transliterations",
            "Follow ALA-LC rules for Arabic"
        ]
    },
    "creator": {
        "datacite": "Creator",
        "dublin_core": "dcterms:creator",
        "obligation": "required",
        "repeatable": True,
        "controlled_vocab": "LCNAF",
        "best_practices": [
            "Enter as: Last Name, First Name, Middle Name",
            "Include birth dates for common names",
            "For oral histories, use interviewee",
            "For Arabic names, use last element as Last Name"
        ]
    },
    "contributor": {
        "datacite": {
            "property": "Contributor",
            "subproperties": ["contributorName", "contributorType"]
        },
        "dublin_core": "dcterms:contributor",
        "obligation": "preferred",
        "repeatable": True,
        "controlled_vocab": "LCNAF",
        "contributor_types": [
            "ContactPerson",
            "DataCollector",
            "DataCurator",
            "DataManager",
            "Distributor",
            "Editor",
            "Producer",
            "RightsHolder",
            "Sponsor",
            "Other"
        ]
    },
    "date": {
        "datacite": {
            "property": "Date",
            "subproperties": ["dateType", "dateInformation"]
        },
        "dublin_core": ["dcterms:date", "dcterms:created", "dcterms:modified", "dcterms:issued"],
        "obligation": "required",
        "repeatable": True,
        "encoding_scheme": ["W3CDTF/ISO 8601", "DCMI Period", "RKMS-ISO8601"],
        "date_types": ["Collected", "Created", "Issued", "Updated", "Other"]
    },
    "subject": {
        "datacite": "Subject",
        "dublin_core": "dcterms:subject",
        "obligation": "required",
        "repeatable": True,
        "controlled_vocab": ["LCSH", "LCNAF", "AAT"],
        "best_practices": [
            "Use controlled vocabulary when possible",
            "Separate terms with semicolon and space"
        ]
    },
    "description": {
        "datacite": {
            "property": "Description",
            "subproperties": ["descriptionType"]
        },
        "dublin_core": ["dcterms:description", "dcterms:abstract", "dcterms:tableOfContents"],
        "obligation": "required",
        "repeatable": True,
        "description_types": [
            "Abstract",
            "Methods",
            "TableOfContents",
            "TechnicalInfo",
            "Other"
        ]
    },
    "rights": {
        "datacite": {
            "property": "Rights",
            "subproperties": ["rightsURI", "rightsIdentifier"]
        },
        "dublin_core": ["dcterms:rights", "dcterms:accessRights", "dcterms:rightsHolder"],
        "obligation": "required_if_applicable",
        "repeatable": True,
        "best_practices": [
            "Include simple rights statement",
            "Use URL for additional information",
            "Specify access rights and copyright holder"
        ]
    },
    "relation": {
        "datacite": ["RelatedItem", "RelatedIdentifier"],
        "dublin_core": [
            "dcterms:relation",
            "dcterms:requires",
            "dcterms:isPartOf",
            "dcterms:isVersionOf"
        ],
        "obligation": "required",
        "repeatable": True,
        "relation_types": [
            "Requires",
            "IsPartOf",
            "IsVersionOf",
            "IsPublishedIn"
        ],
        "best_practices": [
            "Requires and IsPartOf are required",
            "Use for software dependencies",
            "Use for collection relationships"
        ]
    }
} 
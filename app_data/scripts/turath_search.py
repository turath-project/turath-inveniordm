# """Search configurations for Turath."""

# from invenio_search.engine import dsl

# RDM_SEARCH = {
#     "mappings": {
#         "properties": {
#             #-----------------------------------------------
#             # 1. Title Fields
#             #-----------------------------------------------
#             "turath:title": {
#                 "type": "text",
#                 "boost": 2.0,  # Higher relevance for title searches
#                 "fields": {
#                     "keyword": {"type": "keyword"},
#                     "arabic": {"type": "text", "analyzer": "arabic"}
#                 }
#             },

#             #-----------------------------------------------
#             # 2. Alternative Title Fields
#             #-----------------------------------------------
#             "turath:alternative_title": {
#                 "type": "text",
#                 "fields": {
#                     "keyword": {"type": "keyword"},
#                     "arabic": {"type": "text", "analyzer": "arabic"}
#                 }
#             },
#             "turath:alternative_title_script": {
#                 "type": "keyword"  # Controlled vocabulary
#             },

#             #-----------------------------------------------
#             # 3. Creator Fields
#             #-----------------------------------------------
#             "turath:creator": {
#                 "type": "text",
#                 "fields": {
#                     "keyword": {"type": "keyword"},
#                     "id": {"type": "keyword"}  # For vocabulary lookup
#                 }
#             },
#             "turath:creator_arabic": {
#                 "type": "text",
#                 "analyzer": "arabic",
#                 "fields": {
#                     "keyword": {"type": "keyword"}
#                 }
#             },

#             #-----------------------------------------------
#             # 4. Contributor Fields
#             #-----------------------------------------------
#             "turath:contributor": {
#                 "type": "text",
#                 "fields": {
#                     "keyword": {"type": "keyword"},
#                     "id": {"type": "keyword"}
#                 }
#             },
#             "turath:contributor_arabic": {
#                 "type": "text",
#                 "analyzer": "arabic",
#                 "fields": {
#                     "keyword": {"type": "keyword"}
#                 }
#             },
#             "turath:contributor_type": {
#                 "type": "keyword"  # Controlled vocabulary
#             },

#             #-----------------------------------------------
#             # 5. Publisher Field
#             #-----------------------------------------------
#             "turath:publisher": {
#                 "type": "text",
#                 "fields": {
#                     "keyword": {"type": "keyword"},
#                     "arabic": {"type": "text", "analyzer": "arabic"}
#                 }
#             },

#             #-----------------------------------------------
#             # 6-7. Date Fields
#             #-----------------------------------------------
#             "turath:date": {
#                 "type": "date",
#                 "format": "yyyy-MM-dd||yyyy-MM||yyyy"
#             },
#             "turath:date_issued": {
#                 "type": "date",
#                 "format": "yyyy-MM-dd||yyyy-MM||yyyy"
#             },
#             "turath:date_type": {
#                 "type": "keyword"  # Controlled vocabulary
#             },

#             #-----------------------------------------------
#             # 8. Subject Field
#             #-----------------------------------------------
#             "turath:subject": {
#                 "type": "text",
#                 "fields": {
#                     "keyword": {"type": "keyword"},
#                     "id": {"type": "keyword"}
#                 }
#             },

#             #-----------------------------------------------
#             # 9. Description Fields
#             #-----------------------------------------------
#             "turath:description": {
#                 "type": "text",
#                 "fields": {
#                     "keyword": {"type": "keyword"},
#                     "arabic": {"type": "text", "analyzer": "arabic"},
#                     "html": {"type": "text"}  # For HTML content
#                 }
#             },
#             "turath:description_type": {
#                 "type": "keyword"  # Controlled vocabulary
#             },

#             #-----------------------------------------------
#             # 10. Resource Type Field
#             #-----------------------------------------------
#             "turath:resource_type": {
#                 "type": "keyword"  # Controlled vocabulary
#             },

#             #-----------------------------------------------
#             # 11. Format Fields
#             #-----------------------------------------------
#             "turath:format": {
#                 "type": "keyword"  # Controlled vocabulary
#             },
#             "turath:format_extent": {
#                 "type": "text",
#                 "fields": {
#                     "keyword": {"type": "keyword"}
#                 }
#             },

#             #-----------------------------------------------
#             # 12. Identifier Field
#             #-----------------------------------------------
#             "turath:identifier": {
#                 "type": "text",
#                 "fields": {
#                     "keyword": {"type": "keyword"}
#                 }
#             },

#             #-----------------------------------------------
#             # 13. Source Field
#             #-----------------------------------------------
#             "turath:source": {
#                 "type": "text",
#                 "fields": {
#                     "keyword": {"type": "keyword"}
#                 }
#             },

#             #-----------------------------------------------
#             # 14. Language Field
#             #-----------------------------------------------
#             "turath:language": {
#                 "type": "keyword"  # Controlled vocabulary
#             },

#             #-----------------------------------------------
#             # 15. Coverage-Temporal Fields
#             #-----------------------------------------------
#             "turath:coverage_temporal_start": {
#                 "type": "date",
#                 "format": "yyyy-MM-dd||yyyy-MM||yyyy"
#             },
#             "turath:coverage_temporal_end": {
#                 "type": "date",
#                 "format": "yyyy-MM-dd||yyyy-MM||yyyy"
#             },

#             #-----------------------------------------------
#             # 16. Coverage-Spatial Fields
#             #-----------------------------------------------
#             "turath:coverage_spatial": {
#                 "type": "text",
#                 "fields": {
#                     "keyword": {"type": "keyword"},
#                     "id": {"type": "keyword"}
#                 }
#             },
#             "turath:geolocation_point": {
#                 "type": "geo_point"  # For geographic coordinates
#             },

#             #-----------------------------------------------
#             # 17. Relation Fields
#             #-----------------------------------------------
#             "turath:relation_type": {
#                 "type": "keyword"  # Controlled vocabulary
#             },
#             "turath:relation_identifier": {
#                 "type": "text",
#                 "fields": {
#                     "keyword": {"type": "keyword"}
#                 }
#             },
#             "turath:bibliographic_citation": {
#                 "type": "text",
#                 "fields": {
#                     "keyword": {"type": "keyword"},
#                     "arabic": {"type": "text", "analyzer": "arabic"},
#                     "html": {"type": "text"}  # For HTML content
#                 }
#             },

#             #-----------------------------------------------
#             # 18. Rights Fields
#             #-----------------------------------------------
#             "turath:rights": {
#                 "type": "keyword"  # Controlled vocabulary
#             },
#             "turath:rights_uri": {
#                 "type": "keyword"
#             },
#             "turath:rights_identifier": {
#                 "type": "keyword"
#             },

#             #-----------------------------------------------
#             # 19. Script Type Field
#             #-----------------------------------------------
#             "turath:script_type": {
#                 "type": "keyword"  # Controlled vocabulary
#             }
#         }
#     },
#     "settings": {
#         "analysis": {
#             "analyzer": {
#                 "arabic": {
#                     "type": "custom",
#                     "tokenizer": "standard",
#                     "filter": [
#                         "lowercase",
#                         "arabic_normalization",
#                         "arabic_stemmer"
#                     ]
#                 }
#             }
#         }
#     },
#     # Use the facet names we defined in RDM_FACETS
#     "facets": [
#         "resource_type",
#         "language"
#     ],
#     "sort": [
#         "bestmatch",
#         "newest",
#         "oldest"
#     ]
# }

# RDM_SORT_OPTIONS = {
#     "bestmatch": dict(
#         title="Best match",
#         fields=["_score"],
#     ),
#     "newest": dict(
#         title="Newest",
#         fields=["-created"],
#     ),
#     "oldest": dict(
#         title="Oldest",
#         fields=["created"],
#     ),
# } 
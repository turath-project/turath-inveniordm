# Mirador Previewer Configuration
# -----------------------
# Mirador Previewer is registered automatically via entry points

# Remove file count limit per record
# # Remove file count limit per record
# FILES_REST_DEFAULT_MAX_FILE_COUNT = None

# # Increase UI deposit form file quota
# APP_RDM_DEPOSIT_FORM_QUOTA = {
#     "maxFiles": 1000,
#     "maxStorage": 30*10**9,  # 30GB
# }

# # More detailed logs for file operations
# APP_DEFAULT_SECURE_HEADERS = {
#     'force_https': True,
#     'strict_transport_security': True,
#     'strict_transport_security_preload': False,
#     'strict_transport_security_max_age': 31556926,  # One year in seconds
#     'strict_transport_security_include_subdomains': True,
#     'content_security_policy': {
#         'default-src': ["'self'"],
#     },
#     'content_security_policy_report_uri': None,
#     'content_security_policy_report_only': False,
#     'session_cookie_secure': True,
#     'session_cookie_http_only': True,
# }
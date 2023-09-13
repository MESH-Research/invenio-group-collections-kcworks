from jsonschema import FormatChecker
from jsonschema.validators import Draft4Validator
checker = FormatChecker()
f = checker.checks('isLowercase')(lambda x: x == x.lower())

validator = Draft4Validator({"format": "isLowercase"},
                            format_checker=checker)

groups_metadata_schema = {
    "type": "object",
    "properties": {
        "commons_id": {"type": "string",
                       "format": "isLowercase"},
        "group_name": {"type": "string"},
        "group_url": {"type": "string"},
        "privacy": {"type": "string"},
        "description": {"type": "string"},
        "profile_image": {"type": "string"},
        "who_can_upload": {"type": "string"},
        "who_can_accept": {"type": "string"},
        "invenio_roles": {
            "type": "object",
            "properties": {
                "admin": {"type": "string"},
                "moderator": {"type": "string"},
                "member": {"type": "string"},
            },
            "required": ["admin", "moderator", "member"],
        },
    },
    "required": ["commons_id", "group_name", "privacy", "who_can_upload",
                 "who_can_accept", "invenio_roles"],
}
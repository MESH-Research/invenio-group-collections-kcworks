from jsonschema import FormatChecker
from jsonschema.validators import Draft4Validator
checker = FormatChecker()
f = checker.checks('isLowercase')(lambda x: x == x.lower())

validator = Draft4Validator({"format": "isLowercase"},
                            format_checker=checker)

# FIXME: how to serve this from "local://groups-metadata-v1.0.0.json"?
groups_metadata_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "id": "local://groups-metadata-v1.0.0.json",
    # "additionalProperties": False,
    "title": "Invenio Groups Metadata Schema v1.0.0",
    "type": "object",
    "properties": {
        "access": {
            "type": "object",
            "properties": {
                "group_privacy": {
                    "type": "string",
                    "enum": ["public", "private", "hidden"]
                },
                "community_privacy": {
                    "type": "string",
                    "enum": ["public", "private", "hidden"]
                },
                "can_upload": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["members", "moderators", "administrators"]
                    }
                },
                "can_accept": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["members", "moderators", "administrators"]
                    }
                },
            },
            "required": ["group_privacy", "community_privacy", "can_upload",
                         "can_accept"]
        },
        "metadata": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string",
                             "format": "isLowercase"},
                "group_name": {"type": "string"},
                "group_url": {"type": "string"},
                "group_description": {"type": "string"},
                "profile_image": {"type": "string"},
                "has_community": {"type": "boolean"}
            },
            "required": ["group_id", "group_name", "has_community"]
        },
        "invenio_roles": {
            "type": "object",
            "properties": {
                "administrator": {"type": "string"},
                "moderator": {"type": "string"},
                "member": {"type": "string"}
            },
            "required": ["administrator", "moderator", "member"]
        },
    },
    "required": ["access", "metadata", "invenio_roles"]
}
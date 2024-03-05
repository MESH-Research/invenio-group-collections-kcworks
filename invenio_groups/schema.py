# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Marshmallow schema for groups metadata records."""

from invenio_i18n import lazy_gettext as _
from invenio_records_resources.services.records.schema import BaseRecordSchema
from marshmallow import EXCLUDE, fields, Schema, validate
from marshmallow.fields import Boolean, Url
from marshmallow_utils.fields import (
    NestedAttribute,
    SanitizedHTML,
    SanitizedUnicode,
)


def _not_blank(**kwargs):
    """Returns a non-blank validation rule."""
    max_ = kwargs.get("max", "")
    return validate.Length(
        error=_(
            "Field cannot be blank or longer than {max_} characters.".format(
                max_=max_
            )
        ),
        min=1,
        **kwargs,
    )


def no_longer_than(max, **kwargs):
    """Returns a character limit validation rule."""
    return validate.Length(
        error=_(
            "Field cannot be longer than {max} characters.".format(max=max)
        ),
        max=max,
        **kwargs,
    )


class GroupsMetadataAccessSchema(Schema):
    """ """

    group_privacy = fields.Str(
        required=True, validate=validate.OneOf(["public", "private", "hidden"])
    )
    community_privacy = fields.Str(
        required=True,
        validate=validate.OneOf(["public", "private", "hidden", "none"]),
    )
    can_upload = fields.List(
        fields.Str(
            required=True,
            validate=validate.OneOf(
                ["members", "moderators", "administrators", "none"]
            ),
        ),
        required=True,
    )
    can_accept = fields.List(
        fields.Str(
            required=True,
            validate=validate.OneOf(
                ["members", "moderators", "administrators", "none"]
            ),
        ),
        required=True,
    )


class GroupsMetadataMetadataSchema(Schema):
    """ """

    group_id = SanitizedUnicode(required=True, validate=_not_blank(max=250))
    group_name = SanitizedUnicode(required=True, validate=_not_blank(max=2000))
    group_description = SanitizedHTML(
        required=False, validate=no_longer_than(max=2000)
    )
    group_url = Url(required=False, validate=_not_blank())
    profile_image = SanitizedUnicode(
        required=False, validate=no_longer_than(max=250)
    )
    has_community = Boolean(required=True)


class GroupsMetadataInvenioRolesSchema(Schema):
    """ """

    administrator = SanitizedUnicode(
        required=True, validate=_not_blank(max=250)
    )
    moderator = SanitizedUnicode(required=True, validate=_not_blank(max=250))
    member = SanitizedUnicode(required=True, validate=_not_blank(max=250))


class GroupsMetadataSchema(BaseRecordSchema):
    """Marshmallow schema for groups metadata records.

    Following fields are defined in BaseRecordSchema:
    id = fields.String(dump_only=True)
    created = fields.DateTime(dump_only=True)
    updated = fields.DateTime(dump_only=True)
    links = fields.Method('get_links')
    revision_id = fields.Integer(dump_only=True)
    """

    class Meta:
        """Meta class to accept unknown fields."""

        unknown = EXCLUDE

    id = fields.String(dump_only=True)

    metadata = NestedAttribute(GroupsMetadataMetadataSchema, required=True)
    access = NestedAttribute(GroupsMetadataAccessSchema, required=True)
    invenio_roles = NestedAttribute(
        GroupsMetadataInvenioRolesSchema, required=True
    )

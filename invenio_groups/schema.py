# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Marshmallow schema for groups metadata records."""

from invenio_records_resources.services.records.schema import (
    BaseRecordSchema
)

class GroupsMetadataSchema(BaseRecordSchema):
    """Marshmallow schema for groups metadata records."""

    class Meta:
        """Meta class to accept unknown fields."""

        unknown = EXCLUDE
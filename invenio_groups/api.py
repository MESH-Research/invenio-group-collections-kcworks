# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""DB model interaction api for invenio-groups."""


from .models import GroupsMetadata
from invenio_groups.validators import groups_metadata_schema
from invenio_records.api import Record
from invenio_records.systemfields import (
    ConstantField, ModelField, SystemFieldsMixin
)

class GroupsMetadataAPI(Record, SystemFieldsMixin):
    """API class for interacting with group metadata records.
    """

    id = ModelField()
    model_cls = GroupsMetadata
    # format_checker = None
    # validator = None
    # dumper = None
    # loader = None

    schema = ConstantField("$schema", groups_metadata_schema)
    # schema = ConstantField("$schema", "local://groups-metadata-v1.0.0.json")
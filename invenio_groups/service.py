# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

from invenio_records_resources.services.records.service import RecordService


class GroupsMetadataService(RecordService):
    """Service for managing group metadata records."""

    def __init__(self, config={}, **kwargs):
        """Constructor."""
        super().__init__(config=config, **kwargs)


class GroupCollectionsService(RecordService):
    """Service for managing group collections."""

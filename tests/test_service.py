# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Unit tests for the invenio-groups service."""

import pytest
from invenio_groups.service import GroupsMetadataService
from invenio_groups.proxies import current_groups


def test_service(testapp, db):
    """Test service creation."""
    with testapp.app_context():
        ext = current_groups
        service = ext.service
        assert service
        assert isinstance(service, GroupsMetadataService)
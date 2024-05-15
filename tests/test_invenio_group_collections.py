# -*- coding: utf-8 -*-
#
# This file is part of the invenio-group-collections package.
# Copyright (C) 2024, MESH Research.
#
# invenio-group-collections is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Tests for invenio-group-collections."""

from invenio_group_collections import __version__


def test_version():
    """Test version import."""
    assert __version__

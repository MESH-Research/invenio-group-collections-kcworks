# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 MESH Research
#
# invenio-groups is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Tests for invenio-groups."""

import pkg_resources

from invenio_groups import __version__


def test_version():
    """Test version import."""
    assert __version__


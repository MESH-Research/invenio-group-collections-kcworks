#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2026, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""API-suite conftest for monorepo symlink discovery.

When these tests are collected via `tests/api/group_collections` → this
directory, the monorepo root `create_app` (UI+API) would otherwise win.
Force `create_api` here, matching package-local runs and
`tests/api/remote_user_data/conftest.py`.
"""

import pytest
from invenio_app.factory import create_api as _create_app


@pytest.fixture(scope="module")
def create_app(instance_path, entry_points):
    """API-only app factory for this suite.

    Returns:
        The `create_api` factory from `invenio_app.factory`.
    """
    return _create_app

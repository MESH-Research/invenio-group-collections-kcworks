# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Unit tests for the invenio-groups alembic migrations.
"""

import pytest
from invenio_db.utils import drop_alembic_version_table

def test_alembic(testapp, db):
    """Test alembic migrations.
    """
    ext = testapp.extensions['invenio-groups']

    if db.engine.name == 'sqlite':
        pytest.skip("SQLite does not support ALTER TABLE operations.")

    assert not ext.alembic.compare_metadata()
    db.drop_all()
    drop_alembic_version_table()
    ext.alembic.upgrade()

    assert not ext.alembic.compare_metadata()
    ext.alembic.stamp()
    ext.alembic.downgrade()
    ext.alembic.upgrade()

    assert not ext.alembic.compare_metadata()
    drop_alembic_version_table()
# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Unit tests for invenio-groups models.
"""

import pytest
from invenio_groups.models import Group

def test_groups_metadata_model(testapp, db):
    """invenio-groups metadata model test."""
    with testapp.app_context():
        assert "groups_metadata" in db.metadata.tables

        assert Group.query.count() == 0
        mygroup = Group.create(name='mygroup')
        db.session.commit()
        mygroup_id = mygroup.id
        print('mygroup_id: ', mygroup_id)
        print('mygroup: ', mygroup)

        assert Group.query.count() == 1
        db.session.commit()




        # :id:
        # :created:
        # :updated:
        # :json:
        # :version_id:

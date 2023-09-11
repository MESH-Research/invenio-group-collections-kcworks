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
from sqlalchemy import select

def test_groups_metadata_model(testapp, db):
    """invenio-groups metadata model test."""
    with testapp.app_context():
        # confirm that the table exists
        assert "groups_metadata" in db.metadata.tables

        # test record creation
        assert Group.query.count() == 0
        schema = {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                },
                "required": ["name"],
            }
        data = {"name": "Test Group", "$schema": schema}

        mygroup = Group(data=data)
        db.session.add(mygroup)
        db.session.commit()
        mygroup_id = mygroup.id

        assert Group.query.count() == 1
        assert len(db.session.execute(select(Group)).all()) == 1
        db.session.commit()

        # test record retrieval
        stmt = select(Group).where(Group.id == mygroup_id)
        retrieved_group = db.session.scalars(stmt).one()
        print('retrieved_group: ', retrieved_group)
        assert retrieved_group.id == mygroup_id
        assert retrieved_group.data == {"name": "Test Group", "$schema": schema}
        assert retrieved_group.version_id == 1

        # test record update
        retrieved_group.data = {"name": "Test Group revised", "$schema": schema}
        db.session.commit()
        retrieved_group2 = db.session.get(Group, mygroup_id)
        assert retrieved_group2.data == {"name": "Test Group revised", "$schema": schema}

        # test record deletion
        group_to_delete = db.session.get(Group, mygroup_id)
        db.session.delete(group_to_delete)
        db.session.commit()

        assert Group.query.count() == 0
        assert db.session.execute(select(Group)).all() == []
        # :id:
        # :created:
        # :updated:
        # :json:
        # :version_id:

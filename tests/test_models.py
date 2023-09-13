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
from invenio_groups.models import GroupsMetadata
from invenio_groups.api import GroupsMetadataAPI
from jsonschema.exceptions import ValidationError
import sqlalchemy
from sqlalchemy import select
from uuid import UUID

def test_groups_metadata_model(testapp, db):
    """invenio-groups metadata model test."""
    with testapp.app_context():
        # confirm that the table exists
        assert "groups_metadata" in db.metadata.tables

        # test record creation
        assert GroupsMetadata.query.count() == 0
        data = {"name": "Test Group"}

        mygroup = GroupsMetadata(data=data)
        db.session.add(mygroup)
        db.session.commit()
        mygroup_id = mygroup.id

        assert GroupsMetadata.query.count() == 1
        assert len(db.session.execute(select(GroupsMetadata)).all()) == 1
        db.session.commit()

        # test record retrieval
        stmt = select(GroupsMetadata).where(GroupsMetadata.id == mygroup_id)
        retrieved_group = db.session.scalars(stmt).one()
        # print('retrieved_group: ', retrieved_group)
        assert retrieved_group.id == mygroup_id
        assert retrieved_group.data == {"name": "Test Group"}
        assert retrieved_group.version_id == 1
        assert retrieved_group.is_deleted == False

        assert type(retrieved_group.decode(retrieved_group.json)) == dict
        assert type(retrieved_group.json) == dict

        assert retrieved_group.encoder == None

        # test record update
        retrieved_group.data = {"name": "Test Group revised"}
        db.session.commit()
        retrieved_group2 = db.session.get(GroupsMetadata, mygroup_id)
        assert retrieved_group2.data == {"name": "Test Group revised"}

        # test record deletion
        group_to_delete = db.session.get(GroupsMetadata, mygroup_id)
        db.session.delete(group_to_delete)
        db.session.commit()

        assert GroupsMetadata.query.count() == 0
        assert db.session.execute(select(GroupsMetadata)).all() == []


def test_groups_metadata_api(testapp, db):
    """invenio-groups metadata api test."""
    with testapp.app_context():
        # test record creation and commit

        # first test schema validation
        with pytest.raises(ValidationError) as exc_validate:
            my_group = GroupsMetadataAPI.create(
                {"group_name": "Test Group"}
            )
        assert "'commons_id' is a required property" in str(exc_validate.value)

        # then valid record creation
        my_group = GroupsMetadataAPI.create({
            "group_name": "Test Group",
            "commons_id": "testgroup",
            "group_description": "test group description",
            "group_privacy": "public",
            "who_can_upload": ["members", "moderators", "administrators"],
            "who_can_accept": ["administrators"],
            "invenio_roles": {
                "administrator": "testgroup-admin",
                "moderator": "testgroup-mod",
                "member": "testgroup-member"
            },
            "has_community": True
        })
        from pprint import pprint
        pprint({k:v for k, v in my_group.items()})
        assert my_group.revision_id == 0
        assert type(my_group.id) == UUID
        db.session.commit()
        print('my_group')
        print(my_group)
        print(my_group.id)
        print(my_group.created)
        print(my_group.dumps())

        assert my_group.dumps() =={'$schema':
            {'$schema': 'http://json-schema.org/draft-04/schema#',
             'id': 'local://groups-metadata-v1.0.0.json',
             'properties': {'commons_group_id': {'format': 'isLowercase',
                                                 'type': 'string'},
                            'community_privacy': {'type': 'string'},
                            'group_description': {'type': 'string'},
                            'group_name': {'type': 'string'},
                            'group_privacy': {'type': 'string'},
                            'group_url': {'type': 'string'},
                            'has_community': {'type': 'boolean'},
                            'invenio_roles': {'properties': {'administrator': {'type': 'string'},
                                                             'member': {'type': 'string'},
                                                             'moderator': {'type': 'string'}},
                                              'required': ['administrator',
                                                           'moderator',
                                                           'member'],
                                              'type': 'object'},
                            'profile_image': {'type': 'string'},
                            'who_can_accept': {'items': {'enum': ['members',
                                                                  'moderators',
                                                                  'administrators'],
                                                         'type': 'string'},
                                               'type': 'array'},
                            'who_can_upload': {'items': {'enum': ['members',
                                                                  'moderators',
                                                                  'administrators'],
                                                         'type': 'string'},
                                               'type': 'array'}},
             'required': ['commons_id',
                          'group_name',
                          'group_description',
                          'group_privacy',
                          'who_can_upload',
                          'who_can_accept',
                          'invenio_roles',
                          'has_community'],
             'title': 'Invenio Groups Metadata Schema v1.0.0',
             'type': 'object'},
            'commons_id': 'testgroup',
            'group_description': 'test group description',
            'group_name': 'Test Group',
            'group_privacy': 'public',
            'has_community': True,
            'invenio_roles': {'administrator': 'testgroup-admin',
                              'member': 'testgroup-member',
                              'moderator': 'testgroup-mod'},
            'who_can_accept': ['administrators'],
            'who_can_upload': ['members', 'moderators', 'administrators']
        }
        assert my_group['group_name'] == "Test Group"

        # test record revision
        my_group['group_name'] = "Test Group revised"
        my_group_updated = my_group.commit()
        db.session.commit()
        assert my_group_updated['group_name'] == "Test Group revised"

        my_group_fetched = GroupsMetadataAPI.get_record(my_group.id)
        assert type(my_group_fetched) == GroupsMetadataAPI

        # soft delete and test that still exists in db
        my_group.delete()
        db.session.commit()
        with pytest.raises(sqlalchemy.exc.NoResultFound) as exc:
            my_group_fetched = GroupsMetadataAPI.get_record(my_group.id)
        assert str(exc.value) == "No row was found when one was required"
        my_groups_fetched = GroupsMetadataAPI.get_records([my_group.id])
        assert len(my_groups_fetched) == 0
        assert len(db.session.get(GroupsMetadata, my_group.id)) == 1
        my_group_soft_deleted = GroupsMetadataAPI.get_record(my_group.id,
                                                             with_deleted=True)
        assert len(my_group_soft_deleted) == 1
        assert my_group_soft_deleted[0].is_deleted == True

        # undelete and test that accessible again
        my_group_soft_deleted[0].undelete()

        assert my_group.json == {"name": "Test Group"}
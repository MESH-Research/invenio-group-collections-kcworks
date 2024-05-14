# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Unit tests for invenio-groups models."""

import py
import pytest
from invenio_groups.models import GroupsMetadata
from invenio_groups.api import GroupsMetadataAPI
from jsonschema.exceptions import ValidationError
import sqlalchemy
from sqlalchemy import select
from uuid import UUID


@pytest.mark.skip(reason="Not implemented")
def test_groups_metadata_model(app, db):
    """invenio-groups metadata model test."""
    with app.app_context():
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
        assert retrieved_group.is_deleted is False

        assert isinstance(retrieved_group.decode(retrieved_group.json), dict)
        assert isinstance(retrieved_group.json, dict)

        assert retrieved_group.encoder is None

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


@pytest.mark.skip(reason="Not implemented")
def test_groups_metadata_api(app, db):
    """invenio-groups metadata api test."""
    with app.app_context():
        # test record creation and commit

        # first test schema validation
        with pytest.raises(ValidationError) as exc_validate:
            my_group = GroupsMetadataAPI.create({"group_name": "Test Group"})
        assert "'access' is a required property" in str(exc_validate.value)

        # then valid record creation
        my_group = GroupsMetadataAPI.create(
            {
                "metadata": {
                    "group_name": "Test Group",
                    "group_id": "testgroup",
                    "group_description": "test group description",
                    "has_community": True,
                },
                "access": {
                    "group_privacy": "public",
                    "community_privacy": "public",
                    "can_upload": ["members", "moderators", "administrators"],
                    "can_accept": ["administrators"],
                },
                "invenio_roles": {
                    "administrator": "testgroup-admin",
                    "moderator": "testgroup-mod",
                    "member": "testgroup-member",
                },
            }
        )
        from pprint import pprint

        pprint({k: v for k, v in my_group.items()})
        assert my_group.revision_id == 0
        assert isinstance(my_group.id, UUID)
        db.session.commit()
        print("my_group")
        print(my_group)
        print(my_group.id)
        print(my_group.created)
        print(my_group.updated)
        print(my_group.revision_id)
        print(my_group.is_deleted)

        json_dump = my_group.dumps()
        print(json_dump)
        assert json_dump["id"] == json_dump["uuid"] == str(my_group.id)
        assert json_dump["version_id"] == my_group.revision_id + 1
        json_vals = {
            k: v
            for k, v in json_dump.items()
            if k not in ["id", "uuid", "created", "updated", "indexed_at"]
        }
        assert json_vals == {
            "$schema": {
                "$schema": "http://json-schema.org/draft-04/schema#",
                "id": "local://groups-metadata-v1.0.0.json",
                # "additionalProperties": False,
                "title": "Invenio Groups Metadata Schema v1.0.0",
                "type": "object",
                "properties": {
                    "access": {
                        "type": "object",
                        "properties": {
                            "group_privacy": {
                                "type": "string",
                                "enum": ["public", "private", "hidden"],
                            },
                            "community_privacy": {
                                "type": "string",
                                "enum": ["public", "private", "hidden"],
                            },
                            "can_upload": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": [
                                        "members",
                                        "moderators",
                                        "administrators",
                                    ],
                                },
                            },
                            "can_accept": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": [
                                        "members",
                                        "moderators",
                                        "administrators",
                                    ],
                                },
                            },
                        },
                        "required": [
                            "group_privacy",
                            "community_privacy",
                            "can_upload",
                            "can_accept",
                        ],
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "group_id": {
                                "type": "string",
                                "format": "isLowercase",
                            },
                            "group_name": {"type": "string"},
                            "group_url": {"type": "string"},
                            "group_description": {"type": "string"},
                            "profile_image": {"type": "string"},
                            "has_community": {"type": "boolean"},
                        },
                        "required": [
                            "group_id",
                            "group_name",
                            "has_community",
                        ],
                    },
                    "invenio_roles": {
                        "type": "object",
                        "properties": {
                            "administrator": {"type": "string"},
                            "moderator": {"type": "string"},
                            "member": {"type": "string"},
                        },
                        "required": ["administrator", "moderator", "member"],
                    },
                },
                "required": ["access", "metadata", "invenio_roles"],
            },
            "access": {
                "group_privacy": "public",
                "community_privacy": "public",
                "can_accept": ["administrators"],
                "can_upload": ["members", "moderators", "administrators"],
            },
            "metadata": {
                "group_id": "testgroup",
                "group_description": "test group description",
                "group_name": "Test Group",
                "has_community": True,
            },
            "invenio_roles": {
                "administrator": "testgroup-admin",
                "member": "testgroup-member",
                "moderator": "testgroup-mod",
            },
            "version_id": 1,
        }
        assert my_group["metadata"]["group_name"] == "Test Group"
        assert {k: v for k, v in my_group.items()} == {
            k: v
            for k, v in json_dump.items()
            if k
            not in [
                "created",
                "id",
                "updated",
                "uuid",
                "version_id",
                "indexed_at",
            ]
        }  # because using default dumper that's deepcopy

        # test record revision
        my_group["metadata"]["group_name"] = "Test Group revised"
        my_group_updated = my_group.commit()
        db.session.commit()
        assert (
            my_group_updated["metadata"]["group_name"] == "Test Group revised"
        )

        my_group_fetched = GroupsMetadataAPI.get_record(my_group.id)
        assert isinstance(my_group_fetched, GroupsMetadataAPI)
        assert my_group_fetched.revision_id == 1

        # soft delete and test that still exists in db
        my_group.delete()
        db.session.commit()
        with pytest.raises(sqlalchemy.exc.NoResultFound) as exc:
            my_group_fetched = GroupsMetadataAPI.get_record(my_group.id)
        assert str(exc.value) == "No row was found when one was required"
        my_groups_fetched = GroupsMetadataAPI.get_records([my_group.id])
        assert len(my_groups_fetched) == 0  # not accessible from api anymore
        assert (
            type(db.session.get(GroupsMetadata, my_group.id)) == GroupsMetadata
        )  # still exists in db
        my_group_soft_deleted = GroupsMetadataAPI.get_record(
            my_group.id, with_deleted=True
        )
        assert isinstance(my_group_soft_deleted, GroupsMetadataAPI)
        assert my_group_soft_deleted.is_deleted is True

        # undelete and test that accessible again
        my_group_soft_deleted.undelete()
        my_group_soft_deleted.commit()
        db.session.commit()
        my_group_fetched = GroupsMetadataAPI.get_record(my_group.id)
        assert isinstance(my_group_fetched, GroupsMetadataAPI)

        # hard delete and test that no longer exists in db
        my_group_fetched.delete(force=True)
        db.session.commit()
        with pytest.raises(sqlalchemy.exc.NoResultFound) as after_delete_exc:
            fetched_after_delete = GroupsMetadataAPI.get_record(  # noqa
                my_group.id
            )
        assert (
            str(after_delete_exc.value)
            == "No row was found when one was required"
        )
        assert (
            db.session.get(GroupsMetadata, my_group.id) is None
        )  # no longer exists in db

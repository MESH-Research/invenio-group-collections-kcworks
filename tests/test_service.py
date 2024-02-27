# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Unit tests for the invenio-groups service."""

from invenio_groups.api import GroupsMetadataAPI
from invenio_groups.service import GroupsMetadataService
from invenio_groups.proxies import current_groups
import marshmallow

# from pprint import pprint
import pytest


def test_service(testapp, db, superuser_identity):
    """Test service creation."""
    with testapp.app_context():
        ext = current_groups
        service = ext.service
        assert service
        assert isinstance(service, GroupsMetadataService)

        # test record creation
        # first test validation with invalid data
        with pytest.raises(marshmallow.exceptions.ValidationError) as exc:
            my_item = service.create(
                superuser_identity, {"name": "Test Group"}
            )
        assert exc.value.messages == {
            "metadata": ["Missing data for required field."],
            "invenio_roles": ["Missing data for required field."],
            "access": ["Missing data for required field."],
        }
        # then test validation with valid data
        valid_data = {
            "access": {
                "group_privacy": "public",
                "community_privacy": "public",
                "can_upload": ["members", "moderators", "administrators"],
                "can_accept": ["administrators"],
            },
            "metadata": {
                "group_name": "Test Group",
                "group_id": "testgroup",
                "group_description": "test group description",
                "has_community": True,
            },
            "invenio_roles": {
                "administrator": "testgroup-admin",
                "moderator": "testgroup-mod",
                "member": "testgroup-member",
            },
        }
        print("valid_data", valid_data)
        my_item = service.create(identity=superuser_identity, data=valid_data)
        my_item_vals = {
            k: v
            for k, v in my_item.to_dict().items()
            if k not in ["id", "created", "updated", "links"]
        }
        assert my_item_vals == {**valid_data, "revision_id": 1}
        # check that it's accessible via the API retrieval
        my_item_id = my_item.id
        api_result = GroupsMetadataAPI.get_record(my_item_id)
        print(api_result)
        assert api_result == valid_data

        # test record retrieval
        read_result = service.read(superuser_identity, my_item_id)
        print("read_result")
        print(dir(read_result))
        print(read_result.id)
        print(read_result.to_dict())
        assert read_result.id == my_item_id
        assert read_result.data == my_item_vals

        # test record search
        search_result = service.search(
            superuser_identity, q="metadata.group_id=testgroup"
        )
        search_result = service.search(superuser_identity, q=f"*")
        print(search_result)
        print(search_result.total)
        print(search_result.hits)
        print(search_result.to_dict())
        assert search_result.total == 1

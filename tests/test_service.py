# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Unit tests for the invenio-groups services."""

from invenio_access.permissions import system_identity
from invenio_accounts import current_accounts
from invenio_cache import current_cache
from invenio_communities.communities.records.api import Community
from invenio_communities.proxies import current_communities
from invenio_groups.api import GroupsMetadataAPI
from invenio_groups.errors import (
    CommonsGroupNotFoundError,
    CollectionAlreadyExistsError,
)
from invenio_groups.service import (
    GroupsMetadataService,
    GroupCollectionsService,
)
from invenio_groups.proxies import (
    current_groups,
    current_group_collections_service as current_collections,
)
import marshmallow

# from pprint import pprint
import pytest
from invenio_groups.utils import logger


def test_collections_service_init(app):
    """Test service initialization."""
    with app.app_context():
        ext = current_groups
        collections_service = ext.collections_service
        assert collections_service
        assert isinstance(collections_service, GroupCollectionsService)


def test_collections_service_create(
    app,
    db,
    requests_mock,
    search_clear,
    sample_community1,
    location,
    custom_fields,
    admin,
):
    """Test service creation."""
    instance_name = "knowledgeCommons"
    group_remote_id = sample_community1["api_response"]["id"]
    api_response = sample_community1["api_response"]
    expected_record = sample_community1["expected_record"]

    with app.app_context():
        update_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            "knowledgeCommons"
        ][
            "url"
        ]  # noq"
        requests_mock.get(
            update_url.replace("{id}", group_remote_id),
            json=api_response,
        )
        requests_mock.get(
            "https://hcommons-dev.org/app/plugins/buddypress/bp-core/images/mystery-group.png",
            status_code=404,
        )

        assert admin.user

        # test record creation
        actual = current_collections.create(
            system_identity,
            group_remote_id,
            instance_name,
        )
        actual_vals = {
            k: v
            for k, v in actual.to_dict().items()
            if k not in ["id", "created", "updated", "links"]
        }
        assert actual_vals == {**expected_record, "revision_id": 2}

        actual_slug = actual.data["slug"]
        community_list = current_communities.service.search(
            identity=system_identity, q=f"slug:{actual_slug}"
        ).to_dict()
        assert len(community_list["hits"]["hits"]) == 1

        read_vals = {
            k: v
            for k, v in community_list["hits"]["hits"][0].items()
            if k not in ["id", "created", "updated", "links"]
        }
        assert read_vals == {**expected_record, "revision_id": 2}


def test_collections_service_create_not_found(
    app, db, requests_mock, not_found_response_body, search_clear, location
):
    """Test service creation when requested group cannot be found."""
    with app.app_context():
        update_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            "knowledgeCommons"
        ][
            "url"
        ]  # noqa
        requests_mock.get(
            update_url.replace("{id}", "1004290111"),
            status_code=200,
            headers={
                "Content-Type": "application/json",
            },
            json=not_found_response_body,
        )

        with pytest.raises(CommonsGroupNotFoundError):
            current_collections.create(
                system_identity, "1004290111", "knowledgeCommons"
            )


def test_collections_service_create_already_deleted(
    app,
    db,
    requests_mock,
    sample_community1,
    search_clear,
    location,
    custom_fields,
    admin,
):
    """Test service creation when a group for the requested community
    already exists but was deleted.
    """
    logger.debug("test_collections_service_create_already_deleted***********")
    with app.app_context():
        update_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            "knowledgeCommons"
        ][
            "url"
        ]  # noqa
        requests_mock.get(
            update_url.replace("{id}", "1004290"),
            status_code=200,
            json=sample_community1["api_response"],
        )
        requests_mock.get(
            "https://hcommons-dev.org/app/plugins/buddypress/bp-core/images/mystery-group.png",
            status_code=404,
        )

        admin = admin.user
        logger.debug("admin.id")
        logger.debug(admin.id)
        logger.debug(current_accounts.datastore.get_user(1))

        existing = current_communities.service.create(
            system_identity, data=sample_community1["creation_metadata"]
        )
        Community.index.refresh()

        current_communities.service.delete(system_identity, existing.id)

        Community.index.refresh()

        actual = current_collections.create(
            system_identity,
            "1004290",
            "knowledgeCommons",
        )
        actual_data = {
            k: v
            for k, v in actual.to_dict().items()
            if k not in ["id", "created", "updated", "links", "revision_id"]
        }

        # slug is incremented because of soft-deleted community
        expected = {
            **sample_community1["expected_record"],
            "slug": "the-inklings-1",
        }
        assert actual_data == expected


def test_collections_service_create_already_exists(
    app,
    db,
    requests_mock,
    sample_community1,
    search_clear,
    location,
    custom_fields,
    admin,
):
    """Test service creation when a group for the requested community
    already exists.
    """
    logger.debug("test_collections_service_create_already_exists***********")
    with app.app_context():
        logger.debug("admin.id")
        logger.debug(admin.user.id)

        update_url = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            "knowledgeCommons"
        ][
            "url"
        ]  # noqa
        requests_mock.get(
            update_url.replace("{id}", "1004290"),
            status_code=200,
            json=sample_community1["api_response"],
        )
        current_communities.service.create(
            system_identity, data=sample_community1["creation_metadata"]
        )
        Community.index.refresh()

        with pytest.raises(CollectionAlreadyExistsError):
            current_collections.create(
                system_identity,
                "1004290",
                "knowledgeCommons",
            )


@pytest.mark.skip(reason="Not implemented")
def test_metadata_service_create(app, db, superuser_identity, search_clear):
    """Test service creation."""
    with app.app_context():
        current_cache.clear()
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
        # print("api_result")
        # print(api_result)
        assert {
            k: v for k, v in api_result.items() if k != "$schema"
        } == valid_data

        # test record retrieval
        read_result = service.read(superuser_identity, my_item_id)
        # FIXME: schema isn't dumping the data correctly
        print("read_result")
        print(read_result.to_dict())
        assert read_result.id == my_item_id
        assert {
            k: v
            for k, v in read_result.data.items()
            if k not in ["created", "updated", "id", "links"]
        } == my_item_vals

        # test record search
        search_result = service.search(
            superuser_identity, q="metadata.group_id:testgroup"
        )
        # search_result = service.search(superuser_identity, q="")
        print(search_result)
        print(search_result.total)
        print(search_result.hits)
        # print(search_result.to_dict())
        assert search_result.total == 1
        assert search_result.to_dict()["hits"]["hits"][0]["id"] == my_item_id
        assert search_result.to_dict()["hits"]["total"] == 1
        assert search_result.to_dict()["sortBy"] == "newest"
        assert search_result.to_dict()["links"] == {
            "self": "https://127.0.0.1:5000/api/groups?"
            "page=1&q=&size=25&sort=newest"
        }

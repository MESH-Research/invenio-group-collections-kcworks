# -*- coding: utf-8 -*-
#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Unit tests for the invenio-group-collections-kcworks service."""

from invenio_access.permissions import system_identity
from invenio_accounts import current_accounts
from invenio_communities.communities.records.api import Community
from invenio_communities.proxies import current_communities
from invenio_group_collections_kcworks.errors import (
    CommonsGroupNotFoundError,
    CollectionAlreadyExistsError,
)
from invenio_group_collections_kcworks.service import (
    GroupCollectionsService,
)
from invenio_group_collections_kcworks.proxies import (
    current_group_collections,
    current_group_collections_service as current_collections,
)

# from pprint import pprint
import pytest


def test_collections_service_init(app):
    """Test service initialization."""
    with app.app_context():
        ext = current_group_collections
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
            "https://hcommons-dev.org/app/plugins/buddypress/bp-core/images/mystery-group.png",  # noqa
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
    app.logger.debug(
        "test_collections_service_create_already_deleted***********"
    )
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
            "https://hcommons-dev.org/app/plugins/buddypress/bp-core/images/mystery-group.png",  # noqa
            status_code=404,
        )

        admin = admin.user
        app.logger.debug("admin.id")
        app.logger.debug(admin.id)
        app.logger.debug(current_accounts.datastore.get_user(1))

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
    app.logger.debug(
        "test_collections_service_create_already_exists***********"
    )
    with app.app_context():
        app.logger.debug("admin.id")
        app.logger.debug(admin.user.id)

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

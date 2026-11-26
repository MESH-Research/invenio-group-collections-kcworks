#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2026, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Durable svc-group-collections account has write capability."""

from invenio_group_collections_kcworks.proxies import (
    current_group_collections_service,
)

from tests.fixtures.users import get_durable_service_user


def test_group_collections_service_account_has_write_capability(app, admin_roles):
    """Seeded svc-group-collections may create/update/delete group collections."""
    _user, identity = get_durable_service_user("svc-group-collections")
    service = current_group_collections_service
    for action in (
        "create_group_collection",
        "update_group_collection",
        "delete_group_collection",
    ):
        service.require_permission(identity, action)

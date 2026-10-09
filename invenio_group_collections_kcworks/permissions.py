#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024-2026, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Permission policy and access action for group collections."""

from invenio_access import action_factory
from invenio_administration.generators import Administration
from invenio_communities.generators import CommunityMembers, IfRestricted
from invenio_records_permissions.generators import (
    AdminAction,
    AnyUser,
    SystemProcess,
)
from invenio_records_permissions.policies import BasePermissionPolicy

group_collections_write_action = action_factory("group-collections-write")


class GroupCollectionsPermissionPolicy(BasePermissionPolicy):
    """Permission policy for group collections.

    Mirrors communities: search is open; read respects `access.visibility`.
    Mutations require the `group-collections-write` capability (or
    administration / system process).
    """

    can_search_group_collections = [AnyUser(), SystemProcess()]

    can_read_group_collection = [
        IfRestricted("visibility", then_=[CommunityMembers()], else_=[AnyUser()]),
        SystemProcess(),
    ]

    can_create_group_collection = [
        AdminAction(group_collections_write_action),
        Administration(),
        SystemProcess(),
    ]
    can_update_group_collection = [
        AdminAction(group_collections_write_action),
        Administration(),
        SystemProcess(),
    ]
    can_delete_group_collection = [
        AdminAction(group_collections_write_action),
        Administration(),
        SystemProcess(),
    ]

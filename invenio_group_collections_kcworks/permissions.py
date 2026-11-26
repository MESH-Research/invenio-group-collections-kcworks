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
from invenio_communities.generators import (
    CommunityMembers,
    CommunityOwners,
    IfRestricted,
)
from invenio_records_permissions.generators import (
    AdminAction,
    AnyUser,
    SystemProcess,
)
from invenio_records_permissions.policies import BasePermissionPolicy

from .generators import And, KCGroupAdmin

group_collections_write_action = action_factory("group-collections-write")

# Non-admin path: community owner ∧ KC group admin (no capability required).
# Policy lists are OR, so junction via `And`.
_owner_with_kc_admin = And(
    CommunityOwners(),
    KCGroupAdmin(),
)


class GroupCollectionsPermissionPolicy(BasePermissionPolicy):
    """Permission policy for group collections.

    Mirrors communities: search is open; read respects `access.visibility`.
    Create allows the write capability, administration / system process, or a
    KC group admin for the target group (no community owner yet).
    Update/delete/associate/transfer allow the write capability, administration
    / system process, or `_owner_with_kc_admin`.
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
        KCGroupAdmin(),
    ]
    can_update_group_collection = [
        AdminAction(group_collections_write_action),
        Administration(),
        SystemProcess(),
        _owner_with_kc_admin,
    ]
    can_delete_group_collection = [
        AdminAction(group_collections_write_action),
        Administration(),
        SystemProcess(),
        _owner_with_kc_admin,
    ]

    can_associate_group_collection = [
        AdminAction(group_collections_write_action),
        Administration(),
        SystemProcess(),
        _owner_with_kc_admin,
    ]
    can_transfer_group_collection = [
        AdminAction(group_collections_write_action),
        Administration(),
        SystemProcess(),
        _owner_with_kc_admin,
    ]

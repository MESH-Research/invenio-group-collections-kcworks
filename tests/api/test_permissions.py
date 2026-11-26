#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2026, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Capability checks for group collections mutations."""

from types import SimpleNamespace

import pytest
from flask_principal import Identity
from invenio_access.models import ActionRoles
from invenio_access.permissions import (
    any_user,
    authenticated_user,
    system_identity,
)
from invenio_access.utils import get_identity
from invenio_accounts.proxies import current_accounts
from invenio_db import db
from invenio_group_collections_kcworks.permissions import (
    group_collections_write_action,
)
from invenio_group_collections_kcworks.proxies import (
    current_group_collections_service,
)
from invenio_records_resources.services.errors import PermissionDeniedError


def _community_record(*, id_: str, visibility: str) -> SimpleNamespace:
    """Minimal record shape for `IfRestricted` / `CommunityMembers`.

    Returns:
        A simple namespace with `id` and `access.visibility`.
    """
    return SimpleNamespace(
        id=id_,
        access=SimpleNamespace(visibility=visibility),
    )


def _identity_for_user(app, user) -> Identity:
    """Build an identity with roles and system needs via Invenio's test helper.

    Returns:
        The user's identity with `any_user` and `authenticated_user` needs.
    """
    identity = get_identity(user)
    identity.provides.add(any_user)
    identity.provides.add(authenticated_user)
    return identity


def _ensure_write_action_role():
    """Bind group-collections-write action to a matching role.

    Returns:
        The `group-collections-write` role row.
    """
    role = current_accounts.datastore.find_or_create_role(
        name="group-collections-write"
    )
    current_accounts.datastore.commit()
    for existing in ActionRoles.query_by_action(group_collections_write_action).all():
        if existing.role_id == role.id:
            return role
    db.session.add(
        ActionRoles.create(action=group_collections_write_action, role=role)
    )
    db.session.commit()
    return role


@pytest.fixture
def group_collections_writer(UserFixture, app, db):
    """Non-admin user with group-collections-write only.

    Returns:
        The created user fixture with the write capability role.
    """
    role = _ensure_write_action_role()
    u = UserFixture(
        email="svc-group-collections@example.org",
        password="password",
    )
    u.create(app, db)
    current_accounts.datastore.add_role_to_user(u.user, role)
    current_accounts.datastore.commit()
    return u


def test_group_collections_write_capability_allows_mutations(
    app, group_collections_writer
):
    """Capability role satisfies create/delete group-collection actions."""
    identity = _identity_for_user(app, group_collections_writer.user)
    current_group_collections_service.require_permission(
        identity, "create_group_collection"
    )
    current_group_collections_service.require_permission(
        identity, "delete_group_collection"
    )


def test_plain_authenticated_user_denied_group_collections_write(
    UserFixture, app, db
):
    """Ordinary authenticated users cannot mutate group collections."""
    _ensure_write_action_role()
    u = UserFixture(
        email="plain-user@example.org",
        password="password",
    )
    u.create(app, db)
    identity = _identity_for_user(app, u.user)
    with pytest.raises(PermissionDeniedError):
        current_group_collections_service.require_permission(
            identity, "create_group_collection"
        )
    with pytest.raises(PermissionDeniedError):
        current_group_collections_service.require_permission(
            identity, "delete_group_collection"
        )


def test_system_identity_can_mutate_group_collections(app):
    """Internal jobs retain create/delete via SystemProcess."""
    current_group_collections_service.require_permission(
        system_identity, "create_group_collection"
    )
    current_group_collections_service.require_permission(
        system_identity, "delete_group_collection"
    )


def test_admin_still_allowed_via_administration(app, admin, admin_role_need):
    """Administration override still permits mutations."""
    identity = _identity_for_user(app, admin.user)
    current_group_collections_service.require_permission(
        identity, "create_group_collection"
    )


def test_any_user_can_search_group_collections(app, UserFixture, db):
    """Search is open (visibility is enforced per-hit via communities search)."""
    u = UserFixture(
        email="reader@example.org",
        password="password",
    )
    u.create(app, db)
    identity = _identity_for_user(app, u.user)
    current_group_collections_service.require_permission(
        identity, "search_group_collections"
    )


def test_read_group_collection_public_allows_any_user(app, UserFixture, db):
    """Public visibility uses AnyUser on read_group_collection."""
    u = UserFixture(
        email="public-reader@example.org",
        password="password",
    )
    u.create(app, db)
    identity = _identity_for_user(app, u.user)
    current_group_collections_service.require_permission(
        identity,
        "read_group_collection",
        record=_community_record(id_="pub-1", visibility="public"),
    )


def test_read_group_collection_restricted_denies_non_member(app, UserFixture, db):
    """Restricted visibility requires community membership."""
    u = UserFixture(
        email="non-member@example.org",
        password="password",
    )
    u.create(app, db)
    identity = _identity_for_user(app, u.user)
    with pytest.raises(PermissionDeniedError):
        current_group_collections_service.require_permission(
            identity,
            "read_group_collection",
            record=_community_record(id_="res-1", visibility="restricted"),
        )


def test_associate_allowed_for_write_capability_without_owner_or_kc_admin(
    app, group_collections_writer
):
    """Write capability alone satisfies associate_group_collection."""
    identity = _identity_for_user(app, group_collections_writer.user)
    current_group_collections_service.require_permission(
        identity,
        "associate_group_collection",
        record=_community_record(id_="c-assoc-1", visibility="public"),
        commons_instance="knowledgeCommons",
        commons_group_id="9001",
    )


def test_transfer_allowed_for_write_capability_without_owner_or_kc_admin(
    app, group_collections_writer
):
    """Write capability alone satisfies transfer_group_collection."""
    identity = _identity_for_user(app, group_collections_writer.user)
    current_group_collections_service.require_permission(
        identity,
        "transfer_group_collection",
        record=_community_record(id_="c-xfer-cap", visibility="public"),
        commons_groups=[
            ("knowledgeCommons", "9010"),
            ("knowledgeCommons", "9011"),
        ],
    )


def test_associate_allowed_for_system_identity(app):
    """System process may associate without ownership checks."""
    current_group_collections_service.require_permission(
        system_identity,
        "associate_group_collection",
        record=_community_record(id_="c-assoc-sys", visibility="public"),
        commons_instance="knowledgeCommons",
        commons_group_id="9002",
    )


def test_transfer_allowed_for_administration(app, admin, admin_role_need):
    """Administration may transfer without KC group admin RoleNeeds."""
    identity = _identity_for_user(app, admin.user)
    current_group_collections_service.require_permission(
        identity,
        "transfer_group_collection",
        record=_community_record(id_="c-xfer-admin", visibility="public"),
        commons_groups=[
            ("knowledgeCommons", "9003"),
            ("knowledgeCommons", "9004"),
        ],
    )


def test_transfer_denied_when_missing_one_kc_admin_role(
    app,
    db,
    UserFixture,
    minimal_community_factory,
    search_clear,
):
    """Owner without write capability + only one KC admin role cannot transfer."""
    u = UserFixture(
        email="owner-partial-xfer@example.org",
        password="password",
    )
    u.create(app, db)
    owner = u.user
    community = minimal_community_factory(
        owner=owner.id, slug="perm-transfer-partial"
    )
    old_group_id = "9005"
    new_group_id = "9006"
    role_name = f"knowledgeCommons---{old_group_id}|administrator"
    role = current_accounts.datastore.find_or_create_role(name=role_name)
    current_accounts.datastore.commit()
    owner = db.session.merge(owner)
    role = db.session.merge(role)
    current_accounts.datastore.add_role_to_user(owner, role)
    current_accounts.datastore.commit()

    identity = _identity_for_user(app, owner)
    with pytest.raises(PermissionDeniedError):
        current_group_collections_service.require_permission(
            identity,
            "transfer_group_collection",
            record=community._record,
            commons_groups=[
                ("knowledgeCommons", old_group_id),
                ("knowledgeCommons", new_group_id),
            ],
        )


def test_associate_allowed_for_owner_with_kc_admin(
    app,
    db,
    UserFixture,
    minimal_community_factory,
    search_clear,
):
    """Owner + KC admin RoleNeed may associate (capability not required)."""
    u = UserFixture(
        email="owner-kc-admin-assoc@example.org",
        password="password",
    )
    u.create(app, db)
    owner = u.user
    community = minimal_community_factory(
        owner=owner.id, slug="perm-associate-ok"
    )
    group_id = "9007"
    role_name = f"knowledgeCommons---{group_id}|administrator"
    role = current_accounts.datastore.find_or_create_role(name=role_name)
    current_accounts.datastore.commit()
    owner = db.session.merge(owner)
    role = db.session.merge(role)
    current_accounts.datastore.add_role_to_user(owner, role)
    current_accounts.datastore.commit()

    identity = _identity_for_user(app, owner)
    current_group_collections_service.require_permission(
        identity,
        "associate_group_collection",
        record=community._record,
        commons_instance="knowledgeCommons",
        commons_group_id=group_id,
    )

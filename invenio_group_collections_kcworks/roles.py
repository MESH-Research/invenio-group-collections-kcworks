# Part of Invenio-Group-Collections-KCWorks
# Copyright (C) 2026 MESH Research
#
# Invenio-Group-Collections-KCWorks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Service-capability roles and accounts for group-collection mutations.

One capability isolates privileged group-collection write surfaces that are not
already gated by ordinary community-role policy:

- `group-collections-write` → `svc-group-collections`

`ensure_service_capabilities()` creates that role (bound to its access action)
and the service account (active for API auth, no local password, confirmed),
and assigns the role. Idempotent. Called automatically from this package's
`finalize_app` / `api_finalize_app` hooks.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from flask_principal import Need
from invenio_access.models import ActionRoles
from invenio_accounts.proxies import current_accounts
from invenio_db import db
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from invenio_group_collections_kcworks.permissions import (
    group_collections_write_action,
)

SERVICE_ROLE_CHECK_RETRIES = 5


def _accounts_tables_ready() -> bool:
    """Return True when the accounts schema is present.

    Finalize hooks can run during test bootstrap before session `create_all`.
    Production always has migrated tables by the time the app finalizes.
    """
    try:
        return inspect(db.engine).has_table("accounts_role")
    except Exception:
        return False


@dataclass(frozen=True, slots=True)
class ServiceCapability:
    """One capability role bound to an `invenio_access` action."""

    role_name: str
    action: Need
    description: str


@dataclass(frozen=True, slots=True)
class ServiceAccountSpec:
    """One dedicated service user and the capability roles it must hold."""

    username: str
    email: str
    role_names: tuple[str, ...]
    description: str


SERVICE_CAPABILITIES: tuple[ServiceCapability, ...] = (
    ServiceCapability(
        role_name="group-collections-write",
        action=group_collections_write_action,
        description="Create/update/delete group collections via the API",
    ),
)


SERVICE_ACCOUNTS: tuple[ServiceAccountSpec, ...] = (
    ServiceAccountSpec(
        username="svc-group-collections",
        email="svc-group-collections@service.kcworks.local",
        role_names=("group-collections-write",),
        description="Group-collection create/update/delete via OAuth",
    ),
)


def ensure_service_capability_roles() -> list[str]:
    """Create capability roles and bind each to its access action.

    Idempotent. Looks up each role first; creates and commits only when the
    role or its action binding is missing. Retries on concurrent create/bind
    races from peer app instances.

    Returns:
        Role names that were ensured (created or already present).
    """
    datastore = current_accounts.datastore
    ensured: list[str] = []

    def _try_actionrole_write(role, capability):
        already_bound = any(
            row.role_id == role.id
            for row in ActionRoles.query_by_action(capability.action).all()
        )
        if not already_bound:
            db.session.add(
                ActionRoles.create(action=capability.action, role_id=role.id)
            )
            try:
                db.session.commit()
                return True
            except (IntegrityError, StaleDataError):
                db.session.rollback()
                return False
        return True

    def _try_role_check(capability):
        role = datastore.find_role(capability.role_name)
        if role is None:
            role = datastore.create_role(name=capability.role_name)
            try:
                datastore.commit()
            except (IntegrityError, StaleDataError):
                db.session.rollback()
                return None
        return role

    for capability in SERVICE_CAPABILITIES:
        # Peer app instances race to create the role and/or action link
        role = None
        for i in range(SERVICE_ROLE_CHECK_RETRIES):
            role = _try_role_check(capability)
            if role:
                break
        if not role:
            raise RuntimeError(
                "invenio_group_collections_kcworks.ext could not ensure role "
                f"exists for role {capability.role_name}"
            )

        action_bound = False
        for i in range(SERVICE_ROLE_CHECK_RETRIES):
            action_bound = _try_actionrole_write(role, capability)
            if action_bound:
                break
        if not action_bound:
            raise RuntimeError(
                "invenio_group_collections_kcworks.ext could not ensure action role "
                f"exists for role {role.id}, action {capability.action}"
            )
        ensured.append(capability.role_name)

    return ensured


def _find_service_user(username: str, email: str) -> Any | None:
    """Locate a service user by username, then email.

    Returns:
        The user if found, otherwise `None`.
    """
    datastore = current_accounts.datastore
    user = datastore.find_user(username=username)
    if user is not None:
        return user
    return datastore.find_user(email=email)


def ensure_service_accounts() -> list[dict[str, Any]]:
    """Create service accounts if missing and assign their capability roles.

    Users are active (required for static-token / OAuth API auth), confirmed,
    and created without a password so they cannot use local login. Idempotent.
    Retries on concurrent create/assign races from peer app instances.

    Returns:
        One dict per account with `username`, `user_id`, `created`, and
        `roles_added`.

    Raises:
        RuntimeError: If a required capability role is missing, or if the
            user / role assignments cannot be ensured after retries.
    """
    datastore = current_accounts.datastore
    results: list[dict[str, Any]] = []

    def _try_user_check(spec: ServiceAccountSpec) -> tuple[Any, bool] | None:
        user = _find_service_user(spec.username, spec.email)
        if user is not None:
            return user, False
        user = datastore.create_user(
            email=spec.email,
            username=spec.username,
            password=None,
            active=True,
            confirmed_at=datetime.now(UTC),
            user_profile={"full_name": spec.description},
        )
        try:
            datastore.commit()
            return user, True
        except (IntegrityError, StaleDataError):
            db.session.rollback()
            return None

    def _try_role_assign(user: Any, spec: ServiceAccountSpec) -> list[str] | None:
        roles_added: list[str] = []
        existing_role_names = {role.name for role in (user.roles or [])}
        for role_name in spec.role_names:
            if role_name in existing_role_names:
                continue
            role = datastore.find_role(role_name)
            if role is None:
                raise RuntimeError(
                    f"Capability role {role_name!r} missing; run "
                    "ensure_service_capability_roles() first"
                )
            datastore.add_role_to_user(user, role)
            roles_added.append(role_name)
        if not roles_added:
            return []
        try:
            datastore.commit()
            return roles_added
        except (IntegrityError, StaleDataError):
            db.session.rollback()
            return None

    for spec in SERVICE_ACCOUNTS:
        # Peer app instances race to create the user and/or assign roles
        user = None
        created = False
        for _ in range(SERVICE_ROLE_CHECK_RETRIES):
            got = _try_user_check(spec)
            if got is not None:
                user, created = got
                break
        if user is None:
            raise RuntimeError(
                "invenio_group_collections_kcworks could not ensure service "
                f"account exists for {spec.username!r}"
            )

        roles_added: list[str] | None = None
        for _ in range(SERVICE_ROLE_CHECK_RETRIES):
            # Re-load so we don't keep a stale User after a failed assign commit.
            user = _find_service_user(spec.username, spec.email)
            if user is None:
                break
            roles_added = _try_role_assign(user, spec)
            if roles_added is not None:
                break
        if user is None or roles_added is None:
            raise RuntimeError(
                "invenio_group_collections_kcworks could not ensure role "
                f"assignments for service account {spec.username!r}"
            )

        results.append({
            "username": spec.username,
            "email": spec.email,
            "user_id": user.id,
            "created": created,
            "roles_added": roles_added,
            "role_names": list(spec.role_names),
        })

    return results


def ensure_service_capabilities() -> dict[str, Any]:
    """Ensure capability roles, service accounts, and role assignments.

    Idempotent. Safe to run on every deploy. No-ops when the accounts tables
    are not present yet (test bootstrap before `create_all`).

    Returns:
        Dict with `roles` (role name list) and `accounts` (per-account dicts).
    """
    if not _accounts_tables_ready():
        return {"roles": [], "accounts": []}
    roles = ensure_service_capability_roles()
    accounts = ensure_service_accounts()
    return {"roles": roles, "accounts": accounts}

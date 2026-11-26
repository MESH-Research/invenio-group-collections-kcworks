#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2026, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Permission generators for group-collections associate/transfer."""

from itertools import chain

from flask import current_app
from flask_principal import Identity, RoleNeed
from invenio_access.permissions import Permission
from invenio_records_permissions.generators import Generator

from .utils import format_group_role_name


def kc_group_admin_role_names(
    commons_instance: str, commons_group_id: str
) -> list[str]:
    """Account role names that count as KC group admin for this group.

    Returns:
        Role name strings derived from IdP `group_roles.owner` labels.
    """
    endpoints = current_app.config.get("REMOTE_USER_DATA_API_ENDPOINTS", {})
    idp_config = endpoints.get(commons_instance, {})
    group_roles = idp_config.get("groups", {}).get("group_roles", {})
    owner_labels = group_roles.get("owner") or ["administrator"]
    return [
        format_group_role_name(label, commons_instance, commons_group_id)[0]
        for label in owner_labels
    ]


def _resolve_commons_groups(
    commons_instance: str | None,
    commons_group_id: str | None,
    commons_groups: list[tuple[str, str]] | None,
) -> list[tuple[str, str]]:
    """Normalize associate/transfer group kwargs to `(instance, group_id)` pairs.

    Returns:
        Non-empty list when kwargs supply groups; otherwise `[]`.
    """
    groups = list(commons_groups or [])
    if not groups and commons_instance and commons_group_id:
        groups = [(commons_instance, commons_group_id)]
    return groups


class And(Generator):
    """Require that the identity satisfies every wrapped generator.

    Policy generator lists are OR. `And` contributes needs only when each
    child would already allow the identity (junction of satisfaction). Pass
    `identity` through into generator kwargs (see service `check_permission`).
    """

    def __init__(self, *generators: Generator):
        """Store the generators that must all allow.

        Args:
            *generators: Child permission generators.
        """
        self.generators = generators

    def needs(self, identity: Identity | None = None, **kwargs):
        """Enabling needs if every child allows `identity`; else none.

        Args:
            identity: Caller identity used to test each child.
            **kwargs: Forwarded to children (e.g. `record` for `CommunityOwners`).

        Returns:
            Union of child needs when all children allow; otherwise `[]`.
        """
        if identity is None:
            return []
        # Upstream `CommunityOwners` does `record.id` when `community_id` is
        # omitted; without either, this owner∧admin junction cannot succeed
        # and must not crash policy evaluation for other OR generators.
        if kwargs.get("record") is None and kwargs.get("community_id") is None:
            return []

        collected: list = []
        for generator in self.generators:
            child_needs = list(generator.needs(identity=identity, **kwargs))
            if not Permission(*child_needs).allows(identity):
                return []
            collected.extend(child_needs)
        return collected

    def excludes(self, identity: Identity | None = None, **kwargs):
        """Union of child excludes (any matching exclude still denies).

        Args:
            identity: Caller identity (forwarded).
            **kwargs: Forwarded to children.

        Returns:
            Combined exclude needs from all children.
        """
        if kwargs.get("record") is None and kwargs.get("community_id") is None:
            return []
        return list(
            chain.from_iterable(
                generator.excludes(identity=identity, **kwargs)
                for generator in self.generators
            )
        )


class KCGroupAdmin(Generator):
    """Allow identities that hold KC group admin `RoleNeed`(s).

    Reads `commons_groups` or the single `commons_instance` /
    `commons_group_id` pair from policy kwargs. When several groups are
    supplied (transfer), every group must be satisfied — a single
    `Permission` OR across all role needs would be too weak, so the
    multi-group conjunction is enforced here before any needs are returned.
    """

    def needs(
        self,
        identity: Identity | None = None,
        commons_instance: str | None = None,
        commons_group_id: str | None = None,
        commons_groups: list[tuple[str, str]] | None = None,
        **kwargs,
    ):
        """Return matching admin `RoleNeed`s when every group is covered.

        Args:
            identity: Caller identity whose `provides` are inspected.
            commons_instance: Single Commons instance key (associate).
            commons_group_id: Single Commons group id (associate).
            commons_groups: `(instance, group_id)` pairs (transfer).
            **kwargs: Ignored; accepted for generator `over` compatibility.

        Returns:
            Matched `RoleNeed`s when all groups pass; otherwise `[]`.
        """
        if identity is None:
            return []

        groups = _resolve_commons_groups(
            commons_instance, commons_group_id, commons_groups
        )
        if not groups:
            return []

        matched: list[RoleNeed] = []
        for instance, group_id in groups:
            if not instance or not group_id:
                return []
            role_needs = [
                RoleNeed(name) for name in kc_group_admin_role_names(instance, group_id)
            ]
            group_matches = [need for need in role_needs if need in identity.provides]
            if not group_matches:
                return []
            matched.extend(group_matches)
        return matched

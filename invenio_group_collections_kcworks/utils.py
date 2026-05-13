#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Utility functions for invenio-group-collections-kcworks."""

import re
from urllib.parse import quote

from flask import current_app
from invenio_access.permissions import system_identity
from invenio_communities.members.errors import AlreadyMemberError
from invenio_communities.members.records.api import Member
from invenio_communities.proxies import current_communities
from unidecode import unidecode


def get_configured_remote_group_role_labels(idp: str) -> frozenset[str]:
    """Return every remote group-role label listed under ``group_roles`` for IDP.

    Args:
        idp: Key in ``REMOTE_USER_DATA_API_ENDPOINTS`` (e.g. ``knowledgeCommons``).

    Returns:
        All strings appearing in any permission bucket's list; empty if none.
    """
    endpoints_config = current_app.config.get("REMOTE_USER_DATA_API_ENDPOINTS", {})
    idp_config = endpoints_config.get(idp, {})
    groups_config = idp_config.get("groups", {})
    group_roles_config = groups_config.get("group_roles", {})
    if not group_roles_config:
        return frozenset()
    return frozenset(
        label for labels in group_roles_config.values() for label in labels
    )


def map_remote_roles_to_permissions(
    slug: str,
    all_roles: list,
) -> dict[str, list[str]]:
    """Map remote group roles to Invenio accounts role names by community level.

    Every label listed under ``group_roles`` for this IDP is materialized as
    ``{idp}---{group_id}|{label}`` under the configured permission bucket.

    Remote role strings present in ``all_roles`` but not listed anywhere in
    ``group_roles`` are appended under the ``reader`` bucket and a warning is
    logged.

    Args:
        slug: ``{idp}---{group_id}`` for the Commons group.
        all_roles: Remote role strings from the group metadata API (e.g.
            ``upload_roles`` and ``moderate_roles``).

    Returns:
        Dict mapping Invenio community member ``role`` (e.g. ``owner``) to
        lists of local accounts role names for group-type members.

    Raises:
        ValueError: If ``slug`` is missing the ``---`` separator or this IDP
            has no ``group_roles`` configuration.
    """
    if "---" not in slug:
        raise ValueError(f"Invalid slug: {slug}")
    idp, group_id = slug.split("---", 1)

    endpoints_config = current_app.config.get("REMOTE_USER_DATA_API_ENDPOINTS", {})
    idp_config = endpoints_config.get(idp, {})
    groups_config = idp_config.get("groups", {})
    group_roles_config = groups_config.get("group_roles", {})

    if not group_roles_config:
        raise ValueError(f"No group_roles configuration found for IDP '{idp}'")

    invenio_roles: dict[str, list[str]] = {
        permission_level: [] for permission_level in group_roles_config
    }

    for permission_level, remote_labels in group_roles_config.items():
        seen_names: set[str] = set()
        for remote_label in remote_labels:
            full_name = format_group_role_name(remote_label, idp, group_id)[0]
            if full_name not in seen_names:
                invenio_roles[permission_level].append(full_name)
                seen_names.add(full_name)

    configured_labels = frozenset(
        label for labels in group_roles_config.values() for label in labels
    )
    extras = set(all_roles) - configured_labels
    if extras:
        invenio_roles.setdefault("reader", [])
        reader_seen = set(invenio_roles["reader"])
        for role in sorted(extras):
            current_app.logger.warning(
                "Remote group role %r is not listed in "
                "REMOTE_USER_DATA_API_ENDPOINTS[%r]['groups']['group_roles']; "
                "mapping slug %s to reader as %s.",
                role,
                idp,
                slug,
                format_group_role_name(role, idp, group_id)[0],
            )
            full_name = format_group_role_name(role, idp, group_id)[0]
            if full_name not in reader_seen:
                invenio_roles["reader"].append(full_name)
                reader_seen.add(full_name)

    return invenio_roles


def format_group_role_name(remote_role: str, idp: str, group_id: str) -> list[str]:
    """Format a remote group role into a community role name.

    This function provides centralized role name formatting that can be used
    by both GroupCollectionsService and RemoteUserDataService to ensure
    consistent role naming across the system. The remote suffix is used as
    given (no aliasing between ``admin`` and ``administrator``).

    Args:
        remote_role: The role from the remote API (e.g., "administrator", "member")
        idp: The identity provider name
        group_id: The remote group ID

    Returns:
        List of community role names that should be created for this user
    """
    slug = f"{idp}---{group_id}"
    return [f"{slug}|{remote_role}"]


def make_base_group_slug(group_name: str) -> str:
    """Create a slug from a group name.

    The slug is based on the group name converted to lowercase and with
    spaces replaced by dashes. Any non-alphanumeric characters are removed,
    and slugs longer than 100 characters are truncated.

    Args:
        group_name: The Commons group name.

    Returns:
        The slug based on the group name.
    """
    base_slug = unidecode(group_name.lower().replace(" ", "-"))[:100]
    base_slug = re.sub(r"[^\w-]+", "", base_slug, flags=re.UNICODE)
    url_encoded_base_slug = quote(base_slug)
    return url_encoded_base_slug


def make_group_slug(
    group_id: str | int, group_name: str, instance_name: str
) -> dict[str, str | list[str]]:
    """Create a slug from a group name.

    The slug is based on the group name converted to lowercase and with
    spaces replaced by dashes. Any non-alphanumeric characters are removed and
    slugs longer than 50 characters are truncated.

    If the slug already exists then
    - if the collection belongs to another group, it will append an
    incrementer number to the slug.
    - if the collection belongs to this group but is deleted, it will append
    an incrementer to the slug but return the deleted group's slug as well.
    - if the collection belongs to this group and is not deleted, it will
    raise a RuntimeError.

    Args:
        group_id: The Commons group ID.
        group_name: The Commons group name.
        instance_name: The Commons instance name.

    Returns:
        A dictionary with the following keys:
        - fresh_slug: The slug based on the group name that is available.
        - deleted_slugs: A list of the slugs (if any) based on the group
        name that are not available because they belong to a (soft)
        deleted collection owned by the same group.

    Raises:
        RuntimeError: If an active collection already exists for this group
            with the computed base slug.
    """
    base_slug = group_name.lower().replace(" ", "-")[:100]
    base_slug = re.sub(r"\W+", "", base_slug)
    incrementer = 0
    fresh_slug = base_slug
    deleted_slugs = []

    while True:
        if incrementer > 0:
            fresh_slug = f"{base_slug}-{incrementer}"
        community_list = current_communities.service.search(
            identity=system_identity, q=f"slug:{fresh_slug}"
        )
        if community_list.total == 0:
            break
        else:
            community = community_list.hits[0]
            if (
                community["custom_fields"]["kcr:commons_instance"] == instance_name
                and community["custom_fields"]["kcr:commons_group_id"] == group_id
            ):
                if community["is_deleted"]:
                    deleted_slugs.append(fresh_slug)
                else:
                    raise RuntimeError(
                        f"Group {group_name} from {instance_name} ({group_id})"
                        " already has an active collection with the slug "
                        f"{fresh_slug}"
                    )
            else:
                break
        incrementer += 1

    return {"fresh_slug": fresh_slug, "deleted_slugs": deleted_slugs}


def add_user_to_community(user_id: int, role: str, community_id: int) -> Member | None:
    """Add a user to a community with a given role.

    Returns:
        The created member record, or ``None`` on failure.
    """
    members = None
    try:
        payload = [{"type": "user", "id": str(user_id)}]
        members = current_communities.service.members.add(
            system_identity,
            community_id,
            data={"members": payload, "role": role},
        )
        assert members
    except AlreadyMemberError:
        current_app.logger.error(
            f"User {user_id} was already a {role} member of community {community_id}"
        )
    except AssertionError:
        current_app.logger.error(
            f"Error adding user {user_id} to community {community_id}"
        )
    return members

# -*- coding: utf-8 -*-
#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Utility functions for invenio-group-collections-kcworks."""

from flask import current_app
from invenio_access.permissions import system_identity
from invenio_communities.members.errors import AlreadyMemberError
from invenio_communities.members.records.api import Member
from invenio_communities.proxies import current_communities
import re
from typing import Union, Dict, List, Optional
from unidecode import unidecode
from urllib.parse import quote


def map_remote_roles_to_permissions(
    slug: str,
    all_roles: list,
) -> Dict[str, List[str]]:
    """Map remote group roles to Invenio group names organized by
    their community permissions role level.

    The mapping is based on the group_roles configuration in the
    REMOTE_USER_DATA_API_ENDPOINTS configuration. But we also ensure that
    the remote group roles provided by the API request for group information
    are all mapped to at least "reader" permission level, even if they don't
    appear in the group_roles configuration.

    params:
        slug: The slug of the group in Invenio. Should have the form
            {idp name}---{group name} with the group name in lower-case and
            with spaces replaced by hyphens.
        all_roles: A list of all remote group roles from the API.

    returns:
        Returns a dictionary with the community permission levels as keys
        and the corresponding Invenio group names as values.
    """
    invenio_roles = {}

    if "---" in slug:
        idp, group_id = slug.split("---", 1)
    else:
        raise ValueError(f"Invalid slug: {slug}")

    # Get role mapping from configuration
    endpoints_config = current_app.config.get("REMOTE_USER_DATA_API_ENDPOINTS", {})
    idp_config = endpoints_config.get(idp, {})
    groups_config = idp_config.get("groups", {})
    group_roles_config = groups_config.get("group_roles", {})

    if not group_roles_config:
        raise ValueError(f"No group_roles configuration found for IDP '{idp}'")

    # Track which roles have been assigned to permission levels
    assigned_roles = set()

    # Iterate over permission levels (config keys)
    for permission_level, remote_roles in group_roles_config.items():
        invenio_roles[permission_level] = []

        # For each remote role that maps to this permission level
        for role in all_roles:
            if role in remote_roles:
                community_role_names = format_group_role_name(role, idp, group_id)
                invenio_roles[permission_level].extend(community_role_names)
                assigned_roles.add(role)

    # Handle any roles that weren't in the config (default to reader)
    unassigned_roles = set(all_roles) - assigned_roles
    if unassigned_roles:
        invenio_roles.setdefault("reader", [])
        for role in unassigned_roles:
            community_role_names = format_group_role_name(role, idp, group_id)
            invenio_roles["reader"].extend(community_role_names)

    return invenio_roles


def format_group_role_name(remote_role: str, idp: str, group_id: str) -> list[str]:
    """Format a remote group role into a community role name.

    This function provides centralized role name formatting that can be used
    by both GroupCollectionsService and RemoteUserDataService to ensure
    consistent role naming across the system.

    Args:
        remote_role: The role from the remote API (e.g., "administrator", "member")
        idp: The identity provider name
        group_id: The remote group ID

    Returns:
        List of community role names that should be created for this user
    """
    slug = f"{idp}---{group_id}"

    # Standardize role names for admins, since there's inconsistency in the
    # remote API.
    if remote_role in ["admin", "administrator"]:
        standardized_role = "administrator"
    else:
        standardized_role = remote_role

    return [f"{slug}|{standardized_role}"]


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
    group_id: Union[str, int], group_name: str, instance_name: str
) -> Dict[str, Union[str, List[str]]]:
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


def add_user_to_community(
    user_id: int, role: str, community_id: int
) -> Optional[Member]:
    """Add a user to a community with a given role."""

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
            f"User {user_id} was already a {role} member of community "
            f"{community_id}"
        )
    except AssertionError:
        current_app.logger.error(
            f"Error adding user {user_id} to community {community_id}"
        )
    return members

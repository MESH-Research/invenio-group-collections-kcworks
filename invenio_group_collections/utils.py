# -*- coding: utf-8 -*-
#
# This file is part of the invenio-group-collections package.
# Copyright (C) 2024, MESH Research.
#
# invenio-group-collections is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Utility functions for invenio-group-collections."""

from flask import current_app
from invenio_access.permissions import system_identity
from invenio_communities.members.errors import AlreadyMemberError
from invenio_communities.members.records.api import Member
from invenio_communities.proxies import current_communities

import logging
import os
from pathlib import Path
import re
from typing import Union

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s:%(levelname)s : %(message)s")

instance_path = os.environ.get("INVENIO_INSTANCE_PATH")
if not instance_path:
    instance_path = Path(__file__).parent.parent

log_file_path = Path(instance_path) / "logs" / "invenio-group-collections.log"
print("log_file_path", log_file_path)

if not log_file_path.exists():
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    log_file_path.touch()

file_handler = logging.handlers.RotatingFileHandler(
    log_file_path,
    maxBytes=1000000,
    backupCount=5,
)
file_handler.setFormatter(formatter)
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(file_handler)


def convert_remote_roles(
    slug: str,
    moderate_roles: list,
    upload_roles: list,
    other_roles: list = ["member"],
) -> dict:
    """Convert remote group roles to Invenio group names organized by their community permissions role level.

    params:
        slug: The slug of the group in Invenio. Should have the form
            {idp name}---{group name} with the group name in lower-case and
            with spaces replaced by hyphens.
        moderate_roles: A list of the remote group roles that should be
            converted to the Invenio "manager" role.
        upload_roles: A list of the remote group roles that should be
            converted to the Invenio "curator" role.
        other_roles: A list of the remote group roles that should be
            converted to the Invenio "reader" role. Defaults to ["member"].

    returns:
        Returns a dictionary with the community permission levels as keys
        and the corresponding Invenio group names as values.
    """
    invenio_roles = {}
    seen_roles = []
    # FIXME: In api user response "admin" is used, but in api group
    # response "administrator" is used
    # FIXME: Should upload_roles be given only "reader" permissions?
    if "administrator" in moderate_roles:
        moderate_roles.append("admin")

    for r in list(set(moderate_roles)):
        invenio_roles.setdefault("manager", []).append(f"{slug}|{r}")
        seen_roles.append(r)
    for u in [r for r in list(set(upload_roles)) if r not in seen_roles]:
        invenio_roles.setdefault("curator", []).append(f"{slug}|{u}")
        seen_roles.append(u)
    for o in [r for r in list(set(other_roles)) if r not in seen_roles]:
        invenio_roles.setdefault("reader", []).append(f"{slug}|{o}")
    # ensure reader role is created even if members all have higher perms
    if "reader" not in invenio_roles.keys():
        invenio_roles["reader"] = []
    return invenio_roles


def make_base_group_slug(group_name: str) -> str:
    """Create a slug from a group name.

    The slug is based on the group name converted to lowercase and with
    spaces replaced by dashes. Any non-alphanumeric characters are removed and
    slugs longer than 50 characters are truncated.

    Args:
        group_name: The Commons group name.

    Returns:
        The slug based on the group name.
    """
    base_slug = group_name.lower().replace(" ", "-")[:50]
    base_slug = re.sub(r"[^\w-]+", "", base_slug)
    return base_slug


def make_group_slug(
    group_id: Union[str, int], group_name: str, instance_name: str
) -> dict[str, str]:
    """Create a slug from a group name.

    The slug is based on the group name converted to lowercase and with
    spaces replaced by dashes. Any non-alphanumeric characters are removed and
    slugs longer than 50 characters are truncated.

    If the slug already exists then
    - if the collection belongs to another group, it will append an
    incrementer number to the slug.
    - if the collection belongs to this group but is deleted, it will append an incrementer to the slug but return the deleted group's slug as well.
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
    base_slug = group_name.lower().replace(" ", "-")[:50]
    base_slug = re.sub(r"[^\w-]+", "", base_slug)
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
                community["custom_fields"]["kcr:commons_instance"]
                == instance_name
                and community["custom_fields"]["kcr:commons_group_id"]
                == group_id
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
) -> Member:
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

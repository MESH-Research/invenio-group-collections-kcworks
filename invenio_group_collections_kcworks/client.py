#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2026, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""HTTP client for Commons group metadata used by group collections."""

import os
from typing import Any

import requests
from flask import current_app as app
from werkzeug.exceptions import RequestTimeout, UnprocessableEntity

from .errors import CommonsGroupNotFoundError
from .utils import make_base_group_slug, safe_response_snippet


class CommonsGroupMetadataClient:
    """Fetch and normalize group metadata from configured Commons endpoints."""

    @staticmethod
    def fetch_group_metadata(
        commons_instance: str,
        commons_group_id: str,
        *,
        timeout: int = 15,
    ) -> dict[str, Any]:
        """GET group metadata from `GROUP_COLLECTIONS_METADATA_ENDPOINTS`.

        Args:
            commons_instance: Key in `GROUP_COLLECTIONS_METADATA_ENDPOINTS`.
            commons_group_id: Remote Commons group id.
            timeout: Request timeout in seconds.

        Returns:
            Normalized metadata dict with keys used by
            `GroupCollectionsService` (`instance_name`, `commons_group_name`,
            `commons_group_description`, `commons_group_visibility`,
            `commons_group_url`, `commons_avatar_url`, `commons_upload_roles`,
            `commons_moderate_roles`, `base_slug`, `placeholder_avatar`).

        Raises:
            CommonsGroupNotFoundError: If the remote group is missing.
            RequestTimeout: If the remote request times out.
            requests.exceptions.ConnectionError: If the remote host is
                unreachable.
            UnprocessableEntity: For other unexpected remote responses.
            KeyError: If `commons_instance` is not configured or the token
                env var name is missing from config.
        """
        api_details = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            commons_instance
        ]
        instance_name = api_details.get("title")
        headers = {"Authorization": f"Bearer {os.environ[api_details['token_name']]}"}
        try:
            meta_response = requests.get(
                f"{api_details['url']}{commons_group_id}",
                headers=headers,
                timeout=timeout,
            )
        except requests.exceptions.Timeout:
            raise RequestTimeout(
                "Request to Commons instance for group metadata timed out"
            )
        except requests.exceptions.ConnectionError:
            raise requests.exceptions.ConnectionError(
                "Could not connect to Commons instance to fetch group metadata"
            )

        if meta_response.status_code == 200:
            raw_content = meta_response.json()
            # API may return group at top level or under "results".
            content = raw_content.get("results", raw_content)
            if not content or commons_group_id not in [
                content.get("id"),
                str(content.get("id") or ""),
            ]:
                raise CommonsGroupNotFoundError(
                    f"No such group {commons_group_id} could be found "
                    f"on {instance_name}"
                )
            commons_avatar_url = content["avatar"]
            if commons_avatar_url == api_details.get("default_avatar"):
                commons_avatar_url = None
            commons_group_name = content["name"]
            return {
                "instance_name": instance_name,
                "commons_group_name": commons_group_name,
                "commons_group_description": content["description"],
                "commons_group_visibility": content["visibility"],
                "commons_group_url": content["url"],
                "commons_avatar_url": commons_avatar_url,
                "commons_upload_roles": content["upload_roles"],
                "commons_moderate_roles": content["moderate_roles"],
                "base_slug": content.get("slug")
                or make_base_group_slug(commons_group_name),
                "placeholder_avatar": api_details.get("placeholder_avatar"),
            }

        if meta_response.status_code == 404:
            app.logger.error(
                f"Failed to get metadata for group {commons_group_id} on "
                f"{instance_name} (status={meta_response.status_code}, "
                f"body={safe_response_snippet(meta_response.text)!r})"
            )
            raise CommonsGroupNotFoundError(
                f"No such group {commons_group_id} could be found on {instance_name}"
            )

        app.logger.error(
            f"Failed to get metadata for group {commons_group_id} on "
            f"{instance_name} (status={meta_response.status_code}, "
            f"body={safe_response_snippet(meta_response.text)!r})"
        )
        raise UnprocessableEntity(
            f"Something went wrong requesting group {commons_group_id} "
            f"on {instance_name}"
        )

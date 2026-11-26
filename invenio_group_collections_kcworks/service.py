#
# This file is part of the invenio-group-collections-kcworks package.
# Copyright (C) 2024, MESH Research.
#
# invenio-group-collections-kcworks is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

"""Service for managing group collections."""

from enum import Enum
from io import BytesIO
from pprint import pformat
from typing import Any

import marshmallow as ma
import requests
from flask import current_app as app
from flask_principal import Identity
from invenio_access.permissions import system_identity
from invenio_accounts.models import Role
from invenio_accounts.proxies import current_datastore as accounts_datastore
from invenio_communities.communities.records.systemfields.access import VisibilityEnum
from invenio_communities.communities.services.results import (
    CommunityItem,
    CommunityListResult,
)
from invenio_communities.errors import (
    CommunityDeletedError,
    DeletionStatusError,
    OpenRequestsForCommunityDeletionError,
)
from invenio_communities.members.errors import AlreadyMemberError
from invenio_communities.proxies import current_communities
from invenio_communities.utils import load_community_needs
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_records_resources.services.records.service import RecordService
from invenio_search.proxies import current_search_client
from werkzeug.exceptions import (  # Unauthorized,
    BadRequest,
    Forbidden,
    NotFound,
    UnprocessableEntity,
)

from .client import CommonsGroupMetadataClient
from .errors import (
    CollectionAlreadyExistsError,
    CollectionNotCreatedError,
    CollectionNotFoundError,
    RoleNotCreatedError,
)
from .utils import (
    add_user_to_community,
    map_remote_roles_to_permissions,
    safe_response_snippet,
)


class RemoteAPIVisibility(str, Enum):
    """Enum for the possible visibility values on the remote service."""

    PUBLIC = "public"
    PRIVATE = "private"
    HIDDEN = "hidden"


REMOTE_TO_INVENIO_VISIBILITY = {
    RemoteAPIVisibility.PUBLIC: VisibilityEnum.PUBLIC.value,
    RemoteAPIVisibility.PRIVATE: VisibilityEnum.RESTRICTED.value,
    RemoteAPIVisibility.HIDDEN: VisibilityEnum.RESTRICTED.value,
}


def remote_to_invenio_visibility(remote_value: str) -> str:
    """Map remote API visibility to invenio-communities value.

    Uses remote_value as key in REMOTE_TO_INVENIO_VISIBILITY (via
    RemoteAPIVisibility). Unknown values fall back to 'public'.

    Args:
        remote_value: Remote visibility string.

    Returns:
        'public' or 'restricted'.
    """
    try:
        remote = RemoteAPIVisibility(remote_value)
        return REMOTE_TO_INVENIO_VISIBILITY[remote]
    except (ValueError, KeyError):
        return VisibilityEnum.PUBLIC.value


class GroupCollectionsService(RecordService):
    """Service for managing group collections."""

    def __init__(self, config: dict = {}, **kwargs):
        """Constructor."""
        super().__init__(config=config, **kwargs)

    def check_permission(self, identity, action_name, **kwargs):
        """Check a permission, injecting `identity` into generator kwargs.

        `And` (and `KCGroupAdmin`) read `identity` from policy `over`
        (alongside `commons_instance` / `commons_groups`). Parent
        `check_permission(identity, action, **kwargs)` cannot receive
        `identity` in `kwargs` — that double-binds the positional parameter —
        so this override calls `permission_policy` directly after injecting.

        Loads community `CommunityRoleNeed`s so upstream `CommunityOwners`
        can participate in the associate/transfer junction.

        Args:
            identity: The identity to check.
            action_name: The permission policy action name.
            **kwargs: Extra context passed into generator `over`.

        Returns:
            True if the identity is allowed.
        """
        # `system_identity.id` is the string "system", not a users.id PK —
        # Membership lookups would raise InvalidTextRepresentation.
        if identity.id is not None and identity.id != system_identity.id:
            load_community_needs(identity)
        kwargs.setdefault("identity", identity)
        return self.permission_policy(action_name, **kwargs).allows(identity)

    @staticmethod
    def _is_linked(custom_fields: dict | None) -> bool:
        """Return True when custom fields carry a non-empty KC group link."""
        fields = custom_fields or {}
        instance = fields.get("kcr:commons_instance") or ""
        group_id = fields.get("kcr:commons_group_id") or ""
        return bool(instance) and bool(group_id)

    def _ensure_group_roles(
        self,
        commons_instance: str,
        commons_group_id: str,
        upload_roles: list,
        moderate_roles: list,
    ) -> dict[str, list[str]]:
        """Create Invenio account roles for a Commons group and return the map.

        Args:
            commons_instance: The Commons instance name.
            commons_group_id: The ID of the group on the Commons instance.
            upload_roles: Upload roles from the Commons group metadata.
            moderate_roles: Moderate roles from the Commons group metadata.

        Returns:
            Mapping of community permission names to Invenio role names.

        Raises:
            RoleNotCreatedError: If a role could not be created.
        """
        all_roles = list(moderate_roles) + list(upload_roles)
        if "member" not in all_roles:
            all_roles.append("member")

        invenio_roles = map_remote_roles_to_permissions(
            f"{commons_instance}---{commons_group_id}",
            all_roles,
        )
        app.logger.debug("GroupCollectionService creating roles")
        app.logger.debug(invenio_roles)
        for _key, value in invenio_roles.items():
            for remote_role in value:
                my_group_role = accounts_datastore.find_or_create_role(name=remote_role)
                accounts_datastore.commit()
                if my_group_role is None:
                    raise RoleNotCreatedError(f'Role "{remote_role}" not created.')
        return invenio_roles

    def _add_group_roles_as_members(
        self, community_id: str, invenio_roles: dict[str, list[str]]
    ) -> None:
        """Add mapped group roles as community members."""
        for coll_perm, remote_roles in invenio_roles.items():
            for role in remote_roles:
                try:
                    role_id = accounts_datastore.find_role(role).id
                except AttributeError:
                    app.logger.error(f"Role {role} not found in accounts_datastore")
                    continue
                try:
                    payload = [{"type": "group", "id": role_id}]
                    member = current_communities.service.members.add(
                        system_identity,
                        community_id,
                        data={"members": payload, "role": coll_perm},
                    )
                    assert member
                except AlreadyMemberError:
                    app.logger.error(f"{role} role was already a group member")
                except Exception as e:
                    app.logger.error(f"Error adding {role} role to collection: {e}")

    def _add_admin_as_owner(self, community_id: str) -> None:
        """Add admin role as a community owner."""
        admin_role = accounts_datastore.find_role("administration")
        try:
            manage_payload = [{"type": "group", "id": admin_role.id}]
            current_communities.service.members.add(
                system_identity,
                community_id,
                data={"members": manage_payload, "role": "owner"},
            )
        except AlreadyMemberError:
            app.logger.error("administration role is already an owner")

    def _find_active_collection_for_group(
        self,
        commons_instance: str,
        commons_group_id: str,
        *,
        exclude_id: str | None = None,
    ) -> dict | None:
        """Return the first active collection already linked to this KC group."""
        query_params = (
            f"+custom_fields.kcr\\:commons_instance:{commons_instance} "
            f"+custom_fields.kcr\\:commons_group_id:{commons_group_id}"
        )
        community_list = current_communities.service.search(
            identity=system_identity,
            params={"q": query_params, "size": 10, "page": 1},
        )
        for hit in community_list.to_dict()["hits"]["hits"]:
            if exclude_id and str(hit.get("id")) == str(exclude_id):
                continue
            return hit
        return None

    def _load_community_by_slug(self, collection_slug: str) -> CommunityItem:
        """Load a non-deleted community by slug.

        Uses communities `read` (not search) so soft-deleted slugs surface as
        `CommunityDeletedError` instead of being treated as missing.

        Args:
            collection_slug: The slug of the collection to load.

        Returns:
            A CommunityItem for the collection.

        Raises:
            CollectionNotFoundError: If no community matches the slug.
            CommunityDeletedError: If the community exists but was soft-deleted.
        """
        try:
            return current_communities.service.read(system_identity, collection_slug)
        except CommunityDeletedError:
            raise
        except PIDDoesNotExistError:
            raise CollectionNotFoundError(
                f"No collection found with the slug {collection_slug}"
            )

    def _apply_group_link(
        self,
        community: CommunityItem,
        commons_instance: str,
        commons_group_id: str,
        metadata: dict[str, Any],
        collection_visibility: str | None = None,
    ) -> CommunityItem:
        """Set `kcr:*` fields and group memberships without rewriting metadata.

        Args:
            community: The community to update.
            commons_instance: The Commons instance name.
            commons_group_id: The ID of the group on the Commons instance.
            metadata: Normalized Commons group metadata.
            collection_visibility: Optional visibility override.

        Returns:
            The updated CommunityItem.
        """
        invenio_roles = self._ensure_group_roles(
            commons_instance,
            commons_group_id,
            metadata["commons_upload_roles"],
            metadata["commons_moderate_roles"],
        )
        self._add_group_roles_as_members(community["id"], invenio_roles)

        data = community.to_dict()
        custom_fields = data.get("custom_fields") or {}
        custom_fields.update({
            "kcr:commons_instance": commons_instance,
            "kcr:commons_group_id": commons_group_id,
            "kcr:commons_group_name": metadata["commons_group_name"],
            "kcr:commons_group_description": metadata["commons_group_description"],
            "kcr:commons_group_visibility": metadata["commons_group_visibility"],
        })
        data["custom_fields"] = custom_fields

        if collection_visibility:
            access = data.get("access") or {}
            access["visibility"] = remote_to_invenio_visibility(collection_visibility)
            data["access"] = access

        updated = current_communities.service.update(
            system_identity, community["id"], data=data
        )

        avatar_url = metadata.get("commons_avatar_url")
        placeholder = metadata.get("placeholder_avatar") or "mystery-group.png"
        if avatar_url and placeholder not in avatar_url:
            self.update_avatar(avatar_url, updated["id"])

        current_search_client.indices.refresh(index="*communities*")
        return updated

    def _format_community_payload(
        self,
        metadata: dict[str, Any],
        slug: str,
        commons_instance: str,
        commons_group_id: str,
        collection_visibility: str | None,
    ) -> dict[str, Any]:
        """Format the metadata payload for one community record.

        Args:
            metadata: The metadata dictionary to format.
            slug: String slug for the community.
            commons_instance: Our string identifier for the commons instance.
            commons_group_id: KC group id.
            collection_visibility: Optional collection visibility code.

        Returns:
            The formatted metadata as a dictionary.
        """
        instance_name = metadata["instance_name"]
        commons_group_name = metadata["commons_group_name"]
        commons_group_description = metadata["commons_group_description"]
        commons_group_visibility = metadata["commons_group_visibility"]
        commons_group_url = metadata["commons_group_url"]

        access_visibility = remote_to_invenio_visibility(
            collection_visibility or commons_group_visibility
        )

        data = {
            "access": {
                "visibility": access_visibility,
                "member_policy": "closed",
                "record_submission_policy": "closed",
                "review_policy": "closed",
            },
            "slug": slug,
            "metadata": {
                "title": f"{commons_group_name}",
                "description": (
                    f"A collection managed by "
                    f"{commons_group_name}, a {instance_name} group"
                ),
                "curation_policy": "",
                "page": (
                    f"This"
                    " is a collection of works curated by "
                    f"{commons_group_name}, a {instance_name} group"
                ),
                "website": commons_group_url,
                "organizations": [
                    {
                        "name": commons_group_name,
                    },
                    {"name": instance_name},
                ],
            },
            "custom_fields": {
                "kcr:commons_instance": commons_instance,
                "kcr:commons_group_id": commons_group_id,
                "kcr:commons_group_name": commons_group_name,
                "kcr:commons_group_description": (commons_group_description),  # noqa: E501
                "kcr:commons_group_visibility": commons_group_visibility,  # noqa: E501
            },
        }

        return data

    def _increment_slug(
        self, incrementer: int, base_slug: str, data: dict[str, Any]
    ) -> tuple[int, str, dict[str, Any]]:
        """Increment a community slug for disambiguation.

        Args:
            incrementer: Current numeric suffix.
            base_slug: Base slug before the suffix.
            data: Community create payload (updated in place).

        Returns:
            The modified incrementer, slug, and data with the modified slug.
        """
        incrementer += 1
        slug = f"{base_slug}-{str(incrementer)}"
        data["slug"] = slug
        return (incrementer, slug, data)

    def update_avatar(self, commons_avatar_url: str, community_record_id: str) -> bool:
        """Update the avatar of a community in Invenio from the provided url.

        params:
            commons_avatar_url: The URL of the avatar to fetch.
            community_record_id: The ID of the community to update.

        Returns:
            True if the avatar was updated successfully, otherwise False.
        """
        success = False
        try:
            avatar_response = requests.get(commons_avatar_url, timeout=15)
        except requests.exceptions.Timeout:
            app.logger.error("Request to Commons instance for group avatar timed out")
        except requests.exceptions.ConnectionError:
            app.logger.error(
                "Could not connect to Commons instance to fetch group avatar"
            )
        if avatar_response.status_code == 200:
            try:
                logo_result = current_communities.service.update_logo(
                    system_identity,
                    community_record_id,
                    stream=BytesIO(avatar_response.content),
                )
                if logo_result is not None:
                    app.logger.info("Logo uploaded successfully.")
                    success = True
                else:
                    app.logger.error("Logo upload failed silently in Invenio.")
            except Exception as e:
                app.logger.error(f"Logo upload failed: {e}")
        elif avatar_response.status_code in [400, 405, 406, 412, 413]:
            app.logger.error(
                "Request was not accepted when trying to access "
                f"the provided avatar at {commons_avatar_url} "
                f"(status={avatar_response.status_code}, "
                f"body={safe_response_snippet(avatar_response.text)!r})"
            )
        elif avatar_response.status_code in [401, 403, 407]:
            app.logger.error(
                f"Access the provided avatar was not allowed at {commons_avatar_url} "
                f"(status={avatar_response.status_code}, "
                f"body={safe_response_snippet(avatar_response.text)!r})"
            )
        elif avatar_response.status_code in [404, 410]:
            app.logger.error(
                f"Provided avatar was not found at {commons_avatar_url} "
                f"(status={avatar_response.status_code}, "
                f"body={safe_response_snippet(avatar_response.text)!r})"
            )
        elif avatar_response.status_code == 403:
            app.logger.error(
                f"Access to the provided avatar was forbidden at {commons_avatar_url} "
                f"(status={avatar_response.status_code}, "
                f"body={safe_response_snippet(avatar_response.text)!r})"
            )
        elif avatar_response.status_code in [500, 502, 503, 504, 509, 511]:
            app.logger.error(
                f"Connection failed when trying to access the "
                f"provided avatar at {commons_avatar_url} "
                f"(status={avatar_response.status_code}, "
                f"body={safe_response_snippet(avatar_response.text)!r})"
            )

        return success

    def read(
        self,
        identity: Identity,
        slug: str,
    ) -> CommunityItem:
        """Read a collection (community) by its slug.

        Args:
            identity: The identity of the user making the request.
            slug: The slug of the collection to read.

        Returns:
            A CommunityItem object representing the collection.

        Raises:
            PermissionDeniedError: If `identity` lacks `read_group_collection`
                for this collection's visibility.
            CollectionNotFoundError: If no collection matches the slug.
            CommunityDeletedError: If the collection exists but was soft-deleted
                (API maps this to 410 Gone).
        """  # noqa: DOC502
        # Resolve without the caller's identity so we can return 403 for
        # restricted collections instead of collapsing them into 404.
        result = self._load_community_by_slug(slug)
        self.require_permission(
            identity, "read_group_collection", record=result._record
        )

        return result

    def search(
        self,
        identity: Identity,
        commons_instance: str | None = None,
        commons_group_id: str | None = None,
        sort: str | None = "updated-desc",
        size: int | None = 10,
        page: int | None = 1,
    ) -> CommunityListResult:
        """Search collections (communities) by Commons instance and group ID.

        Args:
            identity: The Identity of the user making the request. [required]
            commons_instance: The Commons instance name. The API search view
                defaults this to `knowledgeCommons` when omitted.
            commons_group_id: The ID of the group on the Commons instance.
            sort: The sort order for the results.
            size: The number of results to return.
            page: The page number of the results to return.

        When `commons_instance` is set, only collections for that instance are
        returned. When `commons_group_id` is also set, only collections for
        that group are returned. Unknown query parameter names are rejected
        by the resource parser (e.g. `group_id` is not accepted; use
        `commons_group_id`).

        Returns:
            A CommunityListResult object.

        Raises:
            PermissionDeniedError: If `identity` lacks
                `search_group_collections`.
            CollectionNotFoundError: If no collections are found matching
                the parameters.
        """  # noqa: DOC502
        self.require_permission(identity, "search_group_collections")
        commons_instance = commons_instance or "knowledgeCommons"
        query_params = f"+custom_fields.kcr\\:commons_instance:{commons_instance} "
        if commons_group_id:
            query_params += f"+custom_fields.kcr\\:commons_group_id:{commons_group_id}"
        community_list = current_communities.service.search(
            identity=identity,
            params={
                "q": query_params,
                "sort": sort,
                "size": int(size) if size else 10,
                "page": int(page) if page else 1,
            },
        )

        if community_list.to_dict()["hits"]["total"] == 0:
            raise CollectionNotFoundError(
                f"No Works collection found matching the parameters {query_params}"
            )

        return community_list

    def create(
        self,
        identity: Identity,
        commons_group_id: str,
        commons_instance: str,
        restore_deleted: bool = False,
        collection_visibility: str | None = None,
        **kwargs,
    ) -> CommunityItem:
        """Create an Invenio collection (community) belonging to a KC group.

        Unlike most Invenio services, this "create" method does not take a
        `data` parameter. Instead the method fetches the necessary data from
        the Commons instance and constructs the collection metadata from that
        data.

        Note that group collections are created with the "administration" role
        and the group's admins (per group_roles config) as owners.

        Args:
            identity: The identity of the user creating the collection.
            commons_group_id: The ID of the group on the Commons instance.
            commons_instance: The name of the Commons instance.
            restore_deleted: If True, the collection will be restored if it
                was previously deleted. If False, a new collection will be
                created with a new slug. [default: False]
            collection_visibility: Optional override for the visibility of
                the collection. Must be either "public" or "restricted" and
                will be converted to a value from invenio-communities
                VisibilityEnum. (Will default to VisibilityEnum.PUBLIC in
                this method.)
            **kwargs: Additional keyword arguments.

        Returns:
            The created collection record.

        Raises:
            PermissionDeniedError: If `identity` lacks `create_group_collection`.
            CommonsGroupNotFoundError: If the group is not found on the
                Commons instance.
            CollectionAlreadyExistsError: If a collection for the group
                already exists and has not been deleted.
            CollectionNotCreatedError: If the collection could not be created
                for some other reason.
            RequestTimeout: If the request to the Commons instance api
                endpoint times out.
            NotImplementedError: If `restore_deleted` is True (not yet
                implemented).
        """  # noqa: DOC502
        self.require_permission(
            identity,
            "create_group_collection",
            commons_instance=commons_instance,
            commons_group_id=commons_group_id,
        )
        metadata = CommonsGroupMetadataClient.fetch_group_metadata(
            commons_instance, commons_group_id
        )
        instance_name = metadata["instance_name"]
        commons_avatar_url = metadata["commons_avatar_url"]
        base_slug = metadata["base_slug"]
        incrementer = 0
        slug = base_slug

        invenio_roles = self._ensure_group_roles(
            commons_instance,
            commons_group_id,
            metadata["commons_upload_roles"],
            metadata["commons_moderate_roles"],
        )

        new_record = None
        data = self._format_community_payload(
            metadata, slug, commons_instance, commons_group_id, collection_visibility
        )
        while not new_record:
            try:
                new_record_result = current_communities.service.create(
                    identity=system_identity, data=data
                )
                new_record = new_record_result
                app.logger.info(f"New record created successfully: {new_record}")
                if not new_record_result:
                    raise CollectionNotCreatedError("Failed to create new collection")
            except ma.ValidationError as e:
                # group with slug already exists
                app.logger.error(f"Validation error: {e}")
                # KCWorks i18n rewrites "community" → "collection" here;
                # match the stable suffix rather than the noun.
                if "with this identifier already exists" in str(e):
                    community_list = current_communities.service.search(
                        identity=system_identity, q=f"slug:{slug}"
                    )
                    if community_list.total < 1:
                        msg = (
                            f"Collection for {instance_name} group {commons_group_id} "
                            "seems to have been deleted previously and has not been "
                            "restored. Continuing with a new url slug."
                        )
                        app.logger.warning(msg)

                        if restore_deleted:
                            raise NotImplementedError(
                                "Restore deleted collection not yet implemented"
                            )
                        else:
                            incrementer, slug, data = self._increment_slug(
                                incrementer, base_slug, data
                            )
                    elif (
                        community_list.total == 1
                        and community_list.to_dict()["hits"]["hits"][0][
                            "custom_fields"
                        ]["kcr:commons_group_id"]
                        == commons_group_id
                    ):
                        raise CollectionAlreadyExistsError(
                            f"Collection for {instance_name} "
                            f"group {commons_group_id} already exists"
                        )
                    else:
                        incrementer, slug, data = self._increment_slug(
                            incrementer, base_slug, data
                        )
                else:
                    raise CollectionNotCreatedError(str(e))

        self._add_admin_as_owner(new_record["id"])
        self._add_group_roles_as_members(new_record["id"], invenio_roles)

        # download the group avatar and upload it to the Invenio instance
        placeholder = metadata.get("placeholder_avatar") or "mystery-group.png"
        if commons_avatar_url and placeholder not in commons_avatar_url:
            self.update_avatar(commons_avatar_url, new_record["id"])

        return new_record

    def associate(
        self,
        identity: Identity,
        collection_slug: str,
        commons_group_id: str,
        commons_instance: str,
        collection_visibility: str | None = None,
    ) -> CommunityItem:
        """Associate an existing unlinked collection with a KC group.

        Args:
            identity: Caller identity.
            collection_slug: Slug of the Invenio collection to link.
            commons_group_id: Target Commons group id.
            commons_instance: Commons instance key.
            collection_visibility: Optional visibility override (`public` /
                `restricted` remote values).

        Returns:
            The updated community item.

        Raises:
            BadRequest: If `commons_instance` or `commons_group_id` is missing.
            PermissionDeniedError: If identity fails associate authorization.
            CollectionNotFoundError: If the collection slug does not exist.
            CollectionAlreadyExistsError: If the collection is already linked to
                another group, or the target group already owns another
                collection.
            CommonsGroupNotFoundError: If the Commons group cannot be fetched.
        """  # noqa: DOC502
        if not commons_instance or not commons_group_id:
            raise BadRequest("commons_instance and commons_group_id are required")

        community = self._load_community_by_slug(collection_slug)
        custom_fields = community.to_dict().get("custom_fields") or {}
        current_instance = str(custom_fields.get("kcr:commons_instance") or "").strip()
        current_group_id = str(custom_fields.get("kcr:commons_group_id") or "").strip()

        self.require_permission(
            identity,
            "associate_group_collection",
            record=community._record,
            commons_instance=commons_instance,
            commons_group_id=commons_group_id,
        )

        if self._is_linked(custom_fields):
            if (
                current_instance == commons_instance
                and current_group_id == commons_group_id
            ):
                return community
            raise CollectionAlreadyExistsError(
                f"Collection {collection_slug} is already linked to "
                f"{current_instance} group {current_group_id}. "
                "Use PATCH .../transfer to change group ownership."
            )

        existing = self._find_active_collection_for_group(
            commons_instance,
            commons_group_id,
            exclude_id=community["id"],
        )
        if existing:
            raise CollectionAlreadyExistsError(
                f"Collection for {commons_instance} group {commons_group_id} "
                f"already exists ({existing.get('slug')})"
            )

        metadata = CommonsGroupMetadataClient.fetch_group_metadata(
            commons_instance, commons_group_id
        )
        return self._apply_group_link(
            community,
            commons_instance,
            commons_group_id,
            metadata,
            collection_visibility=collection_visibility,
        )

    def transfer(
        self,
        identity: Identity,
        collection_slug: str,
        commons_group_id: str,
        commons_instance: str,
        old_commons_group_id: str,
        old_commons_instance: str,
        collection_visibility: str | None = None,
    ) -> CommunityItem:
        """Transfer an already-linked collection to a different KC group.

        Args:
            identity: Caller identity.
            collection_slug: Slug of the collection to transfer.
            commons_group_id: Target Commons group id.
            commons_instance: Target Commons instance key.
            old_commons_group_id: Expected current Commons group id.
            old_commons_instance: Expected current Commons instance key.
            collection_visibility: Optional visibility override.

        Returns:
            The updated community item.

        Raises:
            PermissionDeniedError: If identity fails transfer authorization.
            CollectionNotFoundError: If the collection slug does not exist.
            BadRequest: If required fields are missing, the collection is
                unlinked, or `old_*` does not match.
            CollectionAlreadyExistsError: If the target group already owns
                another collection.
            CommonsGroupNotFoundError: If the target Commons group is missing.
        """  # noqa: DOC502
        required = {
            "commons_instance": commons_instance,
            "commons_group_id": commons_group_id,
            "old_commons_instance": old_commons_instance,
            "old_commons_group_id": old_commons_group_id,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise BadRequest("Missing required fields: " + ", ".join(missing))

        community = self._load_community_by_slug(collection_slug)
        custom_fields = community.to_dict().get("custom_fields") or {}
        current_instance = str(custom_fields.get("kcr:commons_instance") or "").strip()
        current_group_id = str(custom_fields.get("kcr:commons_group_id") or "").strip()

        if not self._is_linked(custom_fields):
            raise BadRequest(
                f"Collection {collection_slug} is not linked to a KC group. "
                "Use PATCH .../associate instead."
            )
        if (
            current_instance != old_commons_instance
            or current_group_id != old_commons_group_id
        ):
            raise BadRequest(
                f"Collection {collection_slug} is linked to "
                f"{current_instance} group {current_group_id}, not "
                f"{old_commons_instance} group {old_commons_group_id}."
            )

        if (
            current_instance == commons_instance
            and current_group_id == commons_group_id
        ):
            return community

        self.require_permission(
            identity,
            "transfer_group_collection",
            record=community._record,
            commons_groups=[
                (old_commons_instance, old_commons_group_id),
                (commons_instance, commons_group_id),
            ],
        )

        existing = self._find_active_collection_for_group(
            commons_instance,
            commons_group_id,
            exclude_id=community["id"],
        )
        if existing:
            raise CollectionAlreadyExistsError(
                f"Collection for {commons_instance} group {commons_group_id} "
                f"already exists ({existing.get('slug')})"
            )

        metadata = CommonsGroupMetadataClient.fetch_group_metadata(
            commons_instance, commons_group_id
        )
        community = self.disown(
            identity,
            community["id"],
            collection_slug,
            old_commons_group_id,
            old_commons_instance,
        )
        return self._apply_group_link(
            community,
            commons_instance,
            commons_group_id,
            metadata,
            collection_visibility=collection_visibility,
        )

    def delete(
        self,
        identity: Identity,
        collection_slug: str,
        commons_instance: str,
        commons_group_id: str,
    ) -> CommunityItem:
        """Delete the collection belonging to the given Commons group.

        This is a soft delete. The collection will be marked as deleted but
        a tombstone record will be retained and can still be retrieved from
        the database.

        If the collection is successfully deleted, the method will also delete
        the roles associated with the collection.

        Args:
            identity: The identity of the user making the request.
            collection_slug: The slug of the collection to delete.
            commons_instance: The name of the Commons instance.
            commons_group_id: The ID of the group on the Commons instance.

        Returns:
            A CommunityItem object representing the deleted collection.

        Raises:
            NotFound: If no collection is found with the slug.
            Forbidden: If the collection does not belong to the given instance
                or group.
            RuntimeError: If the delete call fails.
            UnprocessableEntity: If the collection is already deleted or has
                open requests that block deletion.
        """
        try:
            collection_record = current_communities.service.read(
                system_identity, collection_slug
            )
            if not collection_record:
                msg = f"No collection found with the slug {collection_slug}. Could not delete."  # noqa: E501
                app.logger.error(msg)
                raise NotFound(msg)
            elif (
                collection_record["custom_fields"].get("kcr:commons_instance")
                != commons_instance
            ):
                msg = f"Collection {collection_slug} does not belong to {commons_instance}. Could not delete."  # noqa: E501
                app.logger.error(msg)
                raise Forbidden(msg)
            elif (
                collection_record["custom_fields"].get("kcr:commons_group_id")
                != commons_group_id
            ):
                msg = f"Collection {collection_slug} does not belong to group {commons_group_id}. Could not delete."  # noqa: E501
                app.logger.error(msg)
                raise Forbidden(msg)

            self.require_permission(
                identity,
                "delete_group_collection",
                record=collection_record._record,
                commons_instance=commons_instance,
                commons_group_id=commons_group_id,
            )

            deleted = current_communities.service.delete(
                system_identity, collection_slug
            )
            if deleted:
                app.logger.info(
                    f"Collection {collection_slug} belonging to "
                    f"{commons_instance} group {commons_group_id}"
                    "deleted successfully."
                )
            else:
                msg = f"Failed to delete collection {collection_slug} belonging to {commons_instance} group {commons_group_id}"  # noqa: E501
                app.logger.error(msg)
                raise RuntimeError(msg)
        except (DeletionStatusError, CommunityDeletedError) as e:
            msg = f"Collection has already been deleted: {str(e)}"
            app.logger.error(msg)
            raise UnprocessableEntity(msg)
        except OpenRequestsForCommunityDeletionError as oe:
            msg = f"Cannot delete a collection with openrequests: {str(oe)}"
            app.logger.error(msg)
            raise UnprocessableEntity(msg)

        # TODO: Is this manual refresh necessary?
        # This manual refresh resulted in a 404 error for the index
        # Community.index.refresh()

        return deleted

    def disown(
        self,
        identity: Identity,
        collection_id: str,
        collection_slug: str,
        remote_group_id: str,
        remote_instance_name: str,
    ) -> CommunityItem:
        """Remove all connections between the remote group and the collection.

        This method will remove all role-based members of the collection that
        are associated with the remote group. It will also remove the remote
        group's metadata from the collection.

        All users who were formerly members of the remote group by virtue of
        their roles will be re-added as individual members of the collection
        with permission levels based on their former roles.

        The group roles themselves (that were used to assign group memberships
        in the collection) will not be deleted. This is because the group
        itself may still exist and may create a new collection in the future.
        They will only be deleted when the group itself is deleted.

        Args:
            identity: The identity of the user making the request.
            collection_id: The ID of the collection to disown.
            collection_slug: The slug of the collection to disown.
            remote_group_id: The ID of the group on the remote Commons
                instance.
            remote_instance_name: The name of the remote Commons instance.

        Returns:
            A CommunityItem object representing the disowned collection. This
            should have no group-based members linked to the remote group, and
            the remote group's metadata should be removed from its
            custom_fields.

        Raises:
            RuntimeError: If not all former group members could be reassigned
                to the collection as individuals.
        """
        app.logger.info(
            f"GroupCollectionsService: Disowning collection "
            f"{collection_slug} from {remote_instance_name} "
            f"group {remote_group_id}"
        )
        model_class = current_communities.service.members.record_cls.model_cls
        # `group_id` stores `Role.id` (UUID), not the role name. Match roles
        # for this Commons group by name prefix, then scope rows to this community.
        role_name_prefix = f"{remote_instance_name}---{remote_group_id}"
        group_role_ids = [
            r.id
            for r in accounts_datastore.role_model.query.filter(
                Role.name.contains(role_name_prefix)
            ).all()
        ]
        app.logger.info(
            "GroupCollectionsService: group_role_ids for prefix %s: %s",
            role_name_prefix,
            group_role_ids,
        )
        if group_role_ids:
            query = model_class.query.filter(
                model_class.community_id == collection_id,
                model_class.group_id.in_(group_role_ids),
            )
            group_members = [(g.group_id, g.role) for g in query.all()]
        else:
            group_members = []
        app.logger.info(f"Group members to remove: {group_members}")

        individual_memberships = []
        failures = []
        for member_role in group_members:
            app.logger.info(f"Group member to remove: {member_role}")
            group_role = accounts_datastore.role_model.query.get(member_role[0])
            if group_role is None:
                app.logger.warning(
                    "GroupCollectionsService: no Role for group_id=%s; skipping",
                    member_role[0],
                )
                continue
            individuals = [u for u in group_role.users]
            app.logger.info(f"Individuals: {pformat(individuals)}")

            for member in individuals:
                # assign member to the group collection community
                # directly with a community role based on their former
                # group role
                add_result = add_user_to_community(
                    member.id, member_role[1], collection_id
                )
                if add_result:
                    individual_memberships.append((member.id, member_role[1]))
                    app.logger.info(f"Member {member.id} reassigned successfully.")
                else:
                    failures.append(member)

            members = current_communities.service.members.record_cls.get_members(
                collection_id,
                members=[{"type": "group", "id": member_role[0]}],
            )
            app.logger.info(f"Members to remove: {pformat(members)}")
            if members:
                current_communities.service.members.delete(
                    system_identity,
                    collection_id,
                    data={"members": [{"id": member_role[0], "type": "group"}]},
                )

        if failures:
            raise RuntimeError("Failed to reassign all members to the collection.")

        # remove the remote group's metadata from the collection
        collection_record = current_communities.service.read(
            system_identity, collection_id
        )
        new_data = collection_record.to_dict()
        removals = {
            "kcr:commons_instance": "",
            "kcr:commons_group_id": "",
            "kcr:commons_group_name": "",
            "kcr:commons_group_description": "",
            "kcr:commons_group_visibility": "",
        }
        new_data["custom_fields"].update(removals)
        new_record = current_communities.service.update(
            system_identity, collection_id, data=new_data
        )

        current_search_client.indices.refresh(index="*communities*")

        return new_record

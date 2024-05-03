# -*- coding: utf-8 -*-
#
# This file is part of the invenio-groups package.
# Copyright (C) 2023, MESH Research.
#
# invenio-groups is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see
# LICENSE file for more details.

from flask import current_app as app
from flask_principal import Identity
from invenio_accounts.proxies import current_datastore as accounts_datastore
from invenio_access.permissions import system_identity
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
from invenio_records_resources.services.records.service import RecordService
from invenio_remote_user_data.components.groups import GroupRolesComponent
from io import BytesIO
import marshmallow as ma
import os
from pprint import pformat
import requests
from typing import Optional, Union
from werkzeug.exceptions import (
    Forbidden,
    NotFound,
    RequestTimeout,
    UnprocessableEntity,
    # Unauthorized,
)

from .errors import CollectionAlreadyExistsError, CommonsGroupNotFoundError
from .utils import logger


class GroupsMetadataService(RecordService):
    """Service for managing group metadata records."""

    def __init__(self, config: dict = {}, **kwargs):
        """Constructor."""
        super().__init__(config=config, **kwargs)


class GroupCollectionsService(RecordService):
    """Service for managing group collections."""

    def __init__(self, config: dict = {}, **kwargs):
        """Constructor."""
        super().__init__(config=config, **kwargs)

    def update_avatar(
        self, commons_avatar_url: str, community_record_id: str
    ) -> bool:
        """Update the avatar of a community in Invenio from the provided url.

        params:
            commons_avatar_url: The URL of the avatar to fetch.
            community_record_id: The ID of the community to update.

        returns True if the avatar was updated successfully, otherwise False.
        """

        success = False
        try:
            avatar_response = requests.get(commons_avatar_url, timeout=15)
        except requests.exceptions.Timeout:
            logger.error(
                "Request to Commons instance for group avatar timed out"
            )
        except requests.exceptions.ConnectionError:
            logger.error(
                "Could not connect to "
                "Commons instance to fetch group avatar"
            )
        if avatar_response.status_code == 200:
            try:
                logo_result = current_communities.service.update_logo(
                    system_identity,
                    community_record_id,
                    stream=BytesIO(avatar_response.content),
                )
                if logo_result is not None:
                    logger.info("Logo uploaded successfully.")
                    success = True
                else:
                    logger.error("Logo upload failed silently in Invenio.")
            except Exception as e:
                logger.error(f"Logo upload failed: {e}")
        elif avatar_response.status_code in [400, 405, 406, 412, 413]:
            logger.error(
                "Request was not accepted when trying to access "
                f"the provided avatar at {commons_avatar_url}"
            )
            logger.error(f"Response: {avatar_response.text}")
        elif avatar_response.status_code in [401, 403, 407]:
            logger.error(
                "Access the provided avatar was not allowed "
                f"at {commons_avatar_url}"
            )
            logger.error(f"Response: {avatar_response.text}")
        elif avatar_response.status_code in [404, 410]:
            logger.error(
                f"Provided avatar was not found at {commons_avatar_url}"
            )
            logger.error(f"Response: {avatar_response.text}")
        elif avatar_response.status_code == 403:
            logger.error(
                "Access to the provided avatar was forbidden"
                f" at {commons_avatar_url}"
            )
            logger.error(f"Response: {avatar_response.text}")
        elif avatar_response.status_code in [500, 502, 503, 504, 509, 511]:
            logger.error(
                f"Connection failed when trying to access the "
                f"provided avatar at {commons_avatar_url}"
            )
            logger.error(f"Response: {avatar_response.text}")

        return success

    def read(
        self,
        identity,
        slug,
    ) -> Union[CommunityItem, dict]:
        """Read a collection (community) by its slug."""

        community_list = current_communities.service.search(
            identity=system_identity, q=f"slug:{slug}"
        )

        if community_list.to_dict()["hits"]["total"] == 0:
            raise NotFound(f"No collection found with the slug {slug}")

        return community_list.to_dict()["hits"]["hits"][0]

    def search(
        self,
        identity: Identity,
        commons_instance: str,
        commons_group_id: Optional[str] = None,
        sort: Optional[str] = None,
        size: Optional[int] = None,
        page: Optional[int] = 1,
    ) -> CommunityListResult:
        """Search collections (communities) by Commons instance and group ID.

        params:
            identity: The Identity of the user making the request. [required]
            commons_instance: The name of the Commons instance. [required]
            commons_group_id: The ID of the group on the Commons instance.
            sort: The sort order for the results.
            size: The number of results to return.
            page: The page number of the results to return.

        Although commons_instance and commons_group_id are optional, at least
        one of them must be provided.

        If only the commons instance is provided, all collections belonging to
        that instance will be returned. If the group ID is also provided, all
        collections belonging to that group will be returned.

        returns:
            Returns a CommunityListResult object.
        """
        query_params = "+_exists_:custom_fields.kcr\:commons_instance "
        if commons_instance:
            query_params += (
                f"+custom_fields.kcr\:commons_instance:{commons_instance} "
            )
        if commons_group_id:
            query_params += (
                f"+custom_fields.kcr\:commons_group_id:{commons_group_id}"
            )
        community_list = current_communities.service.search(
            identity=identity,
            q=query_params,
            sort=sort,
            size=size,
            page=page,
        )

        if community_list.to_dict()["hits"]["total"] == 0:
            raise NotFound(
                "No Works collection found matching the parameters "
                f"{query_params}"
            )

        return community_list

    def create(
        self,
        identity: Identity,
        commons_group_id: str,
        commons_instance: str,
        restore_deleted: bool = False,
        **kwargs,
    ) -> CommunityItem:
        """Create a in Invenio collection (community) belonging to a KC group.

        Unlike most Invenio services, this "create" method does not take a
        `data` parameter. Instead the method fetches the necessary data from
        the Commons instance and constructs the collection metadata from that
        data.

        params:
            identity: The identity of the user creating the collection.
            commons_group_id: The ID of the group on the Commons instance.
            commons_instance: The name of the Commons instance.
            restore_deleted: If True, the collection will be restored if it
                was previously deleted. If False, a new collection will be
                created with a new slug. [default: False]
            **kwargs: Additional keyword arguments.

        returns:
            The created collection record.
        """
        errors = []

        instance_name = app.config["SSO_SAML_IDPS"][commons_instance]["title"]

        # make API request to commons instance to get group metadata
        commons_group_name = ""
        commons_group_description = ""
        commons_group_url = ""
        commons_avatar_url = ""
        commons_upload_roles = []
        commons_moderate_roles = []
        api_details = app.config["GROUP_COLLECTIONS_METADATA_ENDPOINTS"][
            commons_instance
        ]
        headers = {
            "Authorization": f"Bearer {os.environ[api_details['token_name']]}"
        }
        try:
            meta_response = requests.get(
                api_details["url"].format(id=commons_group_id),
                headers=headers,
                timeout=15,
            )
        except requests.exceptions.Timeout:
            raise RequestTimeout(
                "Request to Commons instance for group metadata timed out"
            )
        except requests.exceptions.ConnectionError:
            raise requests.exceptions.ConnectionError(
                "Could not connect to "
                "Commons instance to fetch group metadata"
            )
        if meta_response.status_code == 200:
            content = meta_response.json()
            commons_group_name = content["name"]
            commons_group_description = content["description"]
            commons_group_visibility = content["visibility"]
            commons_group_url = content["url"]
            commons_avatar_url = content["avatar"]
            if commons_avatar_url == api_details.get("default_avatar"):
                commons_avatar_url = None
            commons_upload_roles = content["upload_roles"]
            commons_moderate_roles = content["moderate_roles"]

            base_slug = commons_group_name.lower().replace(" ", "-")
            slug_incrementer = 0
            slug = base_slug

        elif meta_response.status_code == 404:
            logger.error(
                f"Failed to get metadata for group {commons_group_id} on "
                f"{instance_name}"
            )
            logger.error(f"Response: {meta_response.text}")
            logger.error(headers)
            raise CommonsGroupNotFoundError(
                f"No such group {commons_group_id} could be found "
                f"on {instance_name}"
            )
        else:
            logger.error(
                f"Failed to get metadata for group {commons_group_id} on "
                f"{instance_name}"
            )
            logger.error(f"Response: {meta_response.text}")
            logger.error(headers)
            raise UnprocessableEntity(
                f"Something went wrong requesting group {commons_group_id} "
                f"on {instance_name}"
            )

        # create roles for the new collection's group members
        invenio_roles = GroupRolesComponent.convert_remote_roles(
            f"{commons_instance}|{slug}",
            commons_moderate_roles,
            commons_upload_roles,
        )
        for role in invenio_roles.values():
            my_group_role = accounts_datastore.find_or_create_role(name=role)
            accounts_datastore.commit()

            if my_group_role is not None:
                assert my_group_role.name == role
                logger.info(
                    f'Role "{role}" created or retrieved successfully.'
                )
            else:
                raise RuntimeError(f'Role "{role}" not created.')

        # create the new collection
        new_record = None
        data = {
            "access": {
                "visibility": "restricted",
                "member_policy": "closed",
                "record_policy": "closed",
            },
            "slug": slug,
            "metadata": {
                "title": f"{commons_group_name}",
                "description": f"A collection managed by the "
                f"{commons_group_name} group of {instance_name}",
                "curation_policy": "",
                "page": f"This"
                " is a collection of works curated by the "
                f"{commons_group_name} group of {instance_name}",
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
                "kcr:commons_group_description": commons_group_description,  # noqa: E501
                "kcr:commons_group_visibility": commons_group_visibility,  # noqa: E501
            },
        }

        while not new_record:
            try:
                new_record_result = current_communities.service.create(
                    identity=system_identity, data=data
                )
                logger.info(f"New record created successfully: {new_record}")
                new_record = new_record_result
                if not new_record_result:
                    raise RuntimeError("Failed to create new collection")
            except ma.ValidationError as e:
                # group with slug already exists
                logger.error(f"Validation error: {e}")
                if "A community with this identifier already exists" in str(e):
                    community_list = current_communities.service.search(
                        identity=system_identity, q=f"slug:{slug}"
                    )
                    if community_list.to_dict()["hits"]["total"] < 1:
                        msg = f"Collection for {instance_name} group {commons_group_id} seems to have been deleted previously and has not been restored. Continuing with a new url slug."  # noqa: E501
                        logger.error(msg)
                        # raise DeletionStatusError(False, msg)
                        # TODO: provide the option of restoring a deleted
                        # collection here? `restore_deleted` query param is
                        # in place

                        if restore_deleted:
                            raise NotImplementedError(
                                "Restore deleted collection not yet "
                                "implemented"
                            )
                        else:
                            slug_incrementer += 1
                            slug = f"{base_slug}-{str(slug_incrementer)}"
                            data["slug"] = slug
                    elif (
                        community_list.to_dict()["hits"][0]["custom_fields"][
                            "kcr:commons_group_id"
                        ]
                        == commons_group_id
                    ):
                        raise CollectionAlreadyExistsError(
                            f"Collection for {instance_name} "
                            f"group {commons_group_id} already exists"
                        )
                    else:
                        slug_incrementer += 1
                        slug = f"{base_slug}-{str(slug_incrementer)}"
                        data["slug"] = slug
                else:
                    raise UnprocessableEntity(str(e))

        # assign admins as members of the new collection
        try:
            manage_payload = [{"type": "group", "id": "administrator"}]
            manage_members = current_communities.service.members.add(
                system_identity,
                new_record["id"],
                data={"members": manage_payload, "role": "manager"},
            )
            logger.error(f"Manage members: {pformat(manage_members)}")
        except AlreadyMemberError:
            logger.error("adminstrator role is already a manager")

        # assign the group roles as members of the new collection
        for irole in invenio_roles.values():
            payload = [
                {
                    "type": "group",
                    "id": irole,
                }
            ]
            try:
                member = current_communities.service.members.add(
                    system_identity,
                    new_record["id"],
                    data={
                        "members": payload,
                        "role": irole.split("|")[-1],
                    },
                )
                assert member
            except AlreadyMemberError:
                logger.error(f"{irole} role was was already a group member")
        logger.error(pformat(new_record))

        # download the group avatar and upload it to the Invenio instance
        if commons_avatar_url:
            assert self.update_avatar(commons_avatar_url, new_record["id"])

        return new_record

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

        params:
            identity: The identity of the user making the request.
            collection_slug: The slug of the collection to delete.
            commons_instance: The name of the Commons instance.
            commons_group_id: The ID of the group on the Commons instance.

        returns:
            A CommunityItem object representing the deleted collection.
        """

        try:
            collection_record = current_communities.service.read(
                system_identity, collection_slug
            )
            if not collection_record:
                msg = f"No collection found with the slug {collection_slug}. Could not delete."  # noqa: E501
                logger.error(msg)
                raise NotFound(msg)
            elif (
                collection_record["custom_fields"].get("kcr:commons_instance")
                != commons_instance
            ):
                msg = f"Collection {collection_slug} does not belong to {commons_instance}. Could not delete."  # noqa: E501
                logger.error(msg)
                raise Forbidden(msg)
            elif (
                collection_record["custom_fields"].get("kcr:commons_group_id")
                != commons_group_id
            ):
                msg = f"Collection {collection_slug} does not belong to group {commons_group_id}. Could not delete."  # noqa: E501
                logger.error(msg)
                raise Forbidden(msg)

            deleted = current_communities.service.delete(
                system_identity, collection_slug
            )
            if deleted:
                logger.info(
                    f"Collection {collection_slug} belonging to "
                    f"{commons_instance} group {commons_group_id}"
                    "deleted successfully."
                )
            else:
                msg = f"Failed to delete collection {collection_slug} belonging to {commons_instance} group {commons_group_id}"  # noqa: E501
                logger.error(msg)
                raise RuntimeError(msg)
        except (DeletionStatusError, CommunityDeletedError) as e:
            msg = f"Collection has already been deleted: {str(e)}"
            logger.error(msg)
            raise UnprocessableEntity(msg)
        except OpenRequestsForCommunityDeletionError as oe:
            msg = "Cannot delete a collection with open" f"requests: {str(oe)}"
            logger.error(msg)
            raise UnprocessableEntity(msg)

        return deleted
